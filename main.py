from flask import Flask, request, jsonify
from flask_cors import CORS
import serial
import time
import logging
import os
import threading
from contextlib import contextmanager
from typing import List, Dict, Optional
from vfd220 import VFD220

# Global variable to track current display thread
current_display_thread = None
stop_display_event = threading.Event()

def test_vfd_display() -> bool:
    """Test VFD display connection"""
    vfd = VFD220()
    try:
        if not vfd.connect():
            logging.error("Failed to connect to VFD display")
            return False
        
        vfd.clear_display()
        vfd.send_text("Bonjour a vous !")
        return True
    except Exception as e:
        logging.error(f"Error during VFD display test: {e}")
        return False

def setup_logger():
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

app = Flask(__name__)
CORS(app)

def display_order_thread(order: List[Dict[str, str]], stop_event: threading.Event) -> None:
    """Display order on VFD in a separate thread"""
    vfd = VFD220()
    if not vfd.connect():
        logger.error("Failed to connect to VFD display")
        return
    
    try:
        vfd.clear_display()
        line = ""
        total = 0
        for item in order:
            line += "\n" + f"{item.get('name', '')} {item.get('quantity', '')} {item.get('price', '')}"
            total += float(item.get('price', 0)) * int(item.get('quantity', 1))
        # total avec separation de milliers
        total = f"{total:,.0f}".replace(',', ' ')
        line += f"\nTOTAL={total} Ar"
        
        # Display with stop event check
        vfd.scroll_text_boucle(line, scroll_speed=0.5, scroll_all_lines=False,stop_event = stop_event)
        
    except Exception as e:
        logger.error(f"Error displaying order: {e}")
    finally:
        vfd.disconnect()

def display_order_on_vfd(order: List[Dict[str, str]]) -> bool:
    """Start displaying order on VFD in a thread"""
    global current_display_thread, stop_display_event
    
    try:
        # Stop previous display if running
        if current_display_thread and current_display_thread.is_alive():
            logger.info("Stopping previous display")
            stop_display_event.set()
            current_display_thread.join(timeout=2)
        
        # Create new stop event and thread
        stop_display_event = threading.Event()
        current_display_thread = threading.Thread(
            target=display_order_thread,
            args=(order, stop_display_event),
            daemon=True
        )
        current_display_thread.start()
        
        logger.info("Started new display thread")
        return True
        
    except Exception as e:
        logger.error(f"Error starting display thread: {e}")
        return False

@app.route('/api/receive_order', methods=['POST'])
def receive_order():
    """API endpoint to receive and display orders"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        logger.info(f"Received order: {len(data)} items")
        
        # Display order on VFD
        success = display_order_on_vfd(data)
        
        if success:
            return jsonify({"status": "success", "message": "Order displayed"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to display order"}), 500
            
    except Exception as e:
        logger.error(f"Error processing order: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Test VFD on startup
    logger.info("Testing VFD connection on startup...")
    if test_vfd_display():
        logger.info("VFD test successful - starting Flask server")
    else:
        logger.warning("VFD test failed - server will start but display may not work")
    
    app.run(port=8086, debug=True)