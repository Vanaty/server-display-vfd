from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import threading
import time
from typing import List, Dict, Optional
from vfd220 import VFD220

WELCOME_MESSAGE = " CAISSE ILO MARKET  Pret a vous servir !"
VFD_TIMEOUT = 5  # seconds
DISPLAY_TIMEOUT = 10  # seconds

def setup_logger() -> logging.Logger:
    """Configure logger with file and console handlers"""
    if not os.path.exists('logs'):
        os.makedirs('logs')

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler (DEBUG level)
    file_handler = logging.FileHandler('logs/vfd_server.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()


class VFDManager:
    """Manages a single persistent VFD display connection with thread safety"""

    def __init__(self):
        self._lock = threading.Lock()
        self._vfd = VFD220()
        self._connected = False
        self._connect()

    def _connect(self):
        """Establish connection if not already connected"""
        if not self._connected:
            try:
                self._connected = self._vfd.connect()
                if not self._connected:
                    logger.error("Failed to connect to VFD display")
            except PermissionError as e:
                logger.error(f"PermissionError: Cannot open serial port (maybe already in use or insufficient permissions): {e}")
                self._connected = False
            except Exception as e:
                logger.error(f"Exception during VFD connect: {e}")
                self._connected = False

    def _ensure_connection(self):
        """Ensure the VFD is connected before any operation"""
        if not (self._vfd and self._vfd.is_connected()):
            self._connected = False
            self._connect()

    def test_connection(self) -> bool:
        """Test VFD display connection"""
        with self._lock:
            self._ensure_connection()
            if not self._connected:
                return False
            try:
                self._vfd.clear_display()
                self._vfd.send_text(WELCOME_MESSAGE)
                return True
            except Exception as e:
                logger.error(f"VFD connection test failed: {e}")
                self._connected = False
                return False

    def display_welcome(self) -> bool:
        """Display welcome message on VFD"""
        with self._lock:
            self._ensure_connection()
            if not self._connected:
                return False
            try:
                self._vfd.clear_display()
                self._vfd.send_text(WELCOME_MESSAGE)
                return True
            except Exception as e:
                logger.error(f"Error displaying welcome message: {e}")
                self._connected = False
                return False

    def display_order(self, order_items: List[Dict[str, str]]) -> bool:
        """Display order on VFD"""
        if not order_items:
            logger.warning("No order items to display")
            return False

        with self._lock:
            self._ensure_connection()
            if not self._connected:
                return False
            try:
                self._vfd.clear_display()

                lines = []
                total = 0

                for item in order_items:
                    name = str(item.get("name", "Unknown"))
                    price = float(item.get('price', 0))
                    quantity = int(item.get('quantity', 1))
                    item_total = price * quantity
                    total += item_total

                    formatted_name = self._format_name(name)
                    formatted_price = self._format_money(item_total)
                    lines.append(f"{formatted_name}: {formatted_price} Ar")

                # Add total line
                total_formatted = self._format_money(total)
                lines.append(f"TOTAL = {total_formatted} Ar")

                self._vfd.send_multiline_text(lines)
                return True

            except Exception as e:
                logger.error(f"Error displaying order: {e}")
                self._connected = False
                return False
            
    def deconnect(self):
        self._vfd.disconnect()
        self._connected = False


    @staticmethod
    def _format_money(value: float) -> str:
        """Format a float value as money with thousands separator"""
        return f"{value:,.0f}".replace(',', ' ')

    @staticmethod
    def _format_name(name: str) -> str:
        """Format name to fit VFD display constraints"""
        if len(name) >= 7:
            return name[:7]
        return name.ljust(5)

# Global instances
current_display_thread: Optional[threading.Thread] = None
stop_display_event = threading.Event()
orders: List[Dict[str, str]] = []
vfd_manager = VFDManager()

app = Flask(__name__)
CORS(app)

def validate_order_data(data: List[Dict]) -> bool:
    """Validate order data structure"""
    if not isinstance(data, list):
        return False
    
    for item in data:
        if not isinstance(item, dict):
            return False
        
        # Check required fields
        if 'name' not in item or 'price' not in item:
            return False
        
        # Validate data types
        try:
            float(item.get('price', 0))
            int(item.get('quantity', 1))
        except (ValueError, TypeError):
            return False
    
    return True

def display_order_thread(order: List[Dict[str, str]], stop_event: threading.Event) -> None:
    """Display order on VFD in a separate thread"""
    global orders
    
    try:
        # Update global orders
        orders.clear()
        orders.extend(order)
        
        # Display the order
        success = vfd_manager.display_order(order)
        if not success:
            logger.error("Failed to display order on VFD")
        
        # Wait for timeout or stop event
        stop_event.wait(DISPLAY_TIMEOUT)
        
    except Exception as e:
        logger.error(f"Error in display thread: {e}")

def display_order_on_vfd(order: List[Dict[str, str]]) -> bool:
    """Start displaying order on VFD in a thread"""
    global current_display_thread, stop_display_event

    if not validate_order_data(order):
        logger.error("Invalid order data provided")
        return False

    try:
        if current_display_thread and current_display_thread.is_alive():
            logger.debug("Stopping previous display thread")
            stop_display_event.set()
            current_display_thread.join(timeout=2)
            stop_display_event.clear()

        stop_display_event = threading.Event()
        current_display_thread = threading.Thread(
            target=display_order_thread,
            args=(order, stop_display_event),
            daemon=True,
            name="VFD-Display-Thread"
        )
        current_display_thread.start()

        logger.debug(f"Started new display thread for {len(order)} items")
        return True

    except Exception as e:
        logger.error(f"Error starting display thread: {e}")
        return False

@app.route('/api/welcome', methods=['GET'])
def welcome():
    """API endpoint to display welcome message"""
    try:
        success = vfd_manager.display_welcome()
        if success:
            return jsonify({"status": "success", "message": "Welcome message displayed"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to display welcome message"}), 500
    except Exception as e:
        logger.error(f"Error in welcome endpoint: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/receive_order', methods=['POST'])
def receive_order():
    """API endpoint to receive and display orders"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        if not validate_order_data(data):
            return jsonify({"error": "Invalid order data format"}), 400
        
        logger.debug(f"Received order: {len(data)} items")
        
        # Display order on VFD
        success = display_order_on_vfd(data)
        
        if success:
            return jsonify({"status": "success", "message": "Order displayed"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to display order"}), 500
            
    except Exception as e:
        logger.error(f"Error processing order: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """API endpoint to check VFD status"""
    try:
        is_connected = vfd_manager.test_connection()
        response = {
            "status": "success" if is_connected else "error",
            "vfd_connected": is_connected,
            "current_orders": len(orders)
        }
        if not is_connected:
            response["message"] = (
                "VFD not connected. "
                "Possible reasons: COM port in use, access denied, or hardware not present. "
                "Check that COM4 is available and not used by another program."
            )
        return jsonify(response), 200 if is_connected else 500
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info("Testing VFD connection on startup...")
    if vfd_manager.test_connection():
        logger.info("VFD test successful - starting Flask server")
        vfd_manager.deconnect()
    else:
        logger.warning("VFD test failed - server will start but display may not work")
    
    try:
        app.run(port=8086, debug=True)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        if current_display_thread and current_display_thread.is_alive():
            stop_display_event.set()
            current_display_thread.join(timeout=2)
        logger.info("Server stopped")