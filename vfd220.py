import serial
import time
import logging
import threading
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_vfd_logger():
    """Configure logger for VFD module using environment variables"""
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        # Get logging configuration from environment variables
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        date_format = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')
        log_to_file = os.getenv('LOG_TO_FILE', 'False').lower() == 'true'
        log_file_path = os.getenv('LOG_FILE_PATH', 'vfd220.log')
        
        # Create formatter
        formatter = logging.Formatter(log_format, datefmt=date_format)
        
        # Configure console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Configure file handler if enabled
        if log_to_file:
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Set log level
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        
    return logger

class VFD220:
    """Class to control VFD220 display"""
    
    def __init__(self, port=None, baud_rates=None, display_width=None, display_height=None):
        # Load configuration from environment variables with fallback to defaults
        self.port = port or os.getenv('VFD_PORT', 'COM4')
        
        if baud_rates is None:
            baud_rates_str = os.getenv('VFD_BAUD_RATES', '9600,2400,4800,19200')
            self.baud_rates = [int(rate.strip()) for rate in baud_rates_str.split(',')]
        else:
            self.baud_rates = baud_rates
            
        self.display_width = display_width or int(os.getenv('VFD_WIDTH', '20'))
        self.display_height = display_height or int(os.getenv('VFD_HEIGHT', '2'))
        
        self.display_size = (self.display_width, self.display_height)
        self.ser = None
        self.logger = setup_vfd_logger()
        
        # Log the configuration
        self.logger.info(f"VFD220 initialized: Port={self.port}, Size={self.display_width}x{self.display_height}")

    def open_serial_port(self, port, baud_rate):
        try:
            ser = serial.Serial(
                port=port,
                baudrate=baud_rate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
            )
            self.logger.info(f"Serial port {port} opened successfully at {baud_rate} baud")
            return ser
        except serial.SerialException as e:
            self.logger.error(f"Failed to open {port} at {baud_rate} baud: {e}")
            return None

    def connect(self):
        """Try to connect to VFD display"""
        for baud in self.baud_rates:
            self.logger.info(f"Trying baud rate: {baud}")
            self.ser = self.open_serial_port(self.port, baud)
            if self.ser:
                time.sleep(1)  # Wait for display to initialize
                return True
            time.sleep(1)
        
        self.logger.error(f"Error: Could not open {self.port} at any baud rate")
        return False
    
    def is_connected(self):
        """Check if the serial port is open and handle disconnection gracefully"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.in_waiting  # Check if the port is still responsive
                return True
            else:
                return False
        except (serial.SerialException, OSError) as e:
            self.logger.warning(f"Serial port disconnected or unresponsive: {e}")
            return False

    def disconnect(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.logger.info("Serial port closed")

    def send_text(self, message):
        if not self.ser:
            self.logger.error("Serial port not open")
            return
        try:
            message = message + ' ' * (self.display_width - len(message))
            self.ser.write(message.encode('ascii'))
            self.logger.debug(f"Sent: {message}")
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")

    def move_cursor(self, row, col):
        """Move cursor to specific position (row 0-1, col 0-19)"""
        if not self.ser:
            self.logger.error("Serial port not open")
            return
        try:
            # Common VFD cursor positioning commands
            position = row * self.display_width + col
            cmd = bytes([0x1B, 0x4C, position])  # ESC L position
            self.ser.write(cmd)
            self.logger.debug(f"Moved cursor to row {row}, col {col}")
        except Exception as e:
            self.logger.error(f"Error moving cursor: {e}")

    def send_multiline_text(self, lines):
        """Send multiple lines of text to fill the display"""
        if not self.ser:
            self.logger.error("Serial port not open")
            return
        try:
            # Ensure we have exactly display_height lines
            lines = lines[-self.display_height:]
            display_lines = []
            for i in range(self.display_height):
                if i < len(lines):
                    line = lines[i][:self.display_width]  # Truncate if too long
                    line = line.ljust(self.display_width)  # Pad if too short
                    display_lines.append(line)
                else:
                    display_lines.append(' ' * self.display_width)  # Empty line
            self.clear_display()
            time.sleep(0.1)
            for m in display_lines:
                time.sleep(0.1)
                self.send_text(m)
            self.logger.debug(f"Sent multiline text: {display_lines}")
        except Exception as e:
            self.logger.error(f"Error sending multiline text: {e}")

    def clear_display(self):
        if not self.ser:
            self.logger.error("Serial port not open")
            return
        try:
            # Try common VFD clear commands
            for cmd in [b'\x0C']:
                self.ser.write(cmd)
                self.logger.debug(f"Sent clear command: {cmd.hex()}")
        except Exception as e:
            self.logger.error(f"Error clearing display: {e}")

    def center_text(self, message):
        try:
            lines = message.split('\n')
            centered_lines = []
            
            for line in lines:
                padding = (self.display_width - len(line)) // 2
                centered_line = ' ' * padding + line + ' ' * padding
                centered_lines.append(centered_line[:self.display_width])
            
            self.send_multiline_text(centered_lines)
            self.logger.debug(f"Centered text: {centered_lines}")
        except Exception as e:
            self.logger.error(f"Error centering text: {e}")


    def display_static_text(self, message):
        """Display static text across all available lines"""
        try:
            lines = message.split('\n')
            # Pad lines to fill display height
            while len(lines) < self.display_height:
                lines.append('')
            
            # Take only as many lines as display can show
            lines = lines[:self.display_height]
            
            self.clear_display()
            self.send_multiline_text(lines)
            self.logger.debug(f"Displayed static text on {len(lines)} lines")
        except Exception as e:
            self.logger.error(f"Error displaying static text: {e}")

    def scroll_text(self, message, scroll_speed=0.01):
        """Scroll text using all available lines of the display"""
        try:
            lines = message.split('\n')
            
            # Ensure we use all display lines
            while len(lines) < self.display_height:
                lines.append('')
            lines = lines[:self.display_height]
            
            # Add padding for smooth scrolling
            padded_lines = []
            max_length = 0
            
            for line in lines:
                padded_line = ' ' * self.display_width + line + ' ' * self.display_width
                padded_lines.append(padded_line)
                max_length = max(max_length, len(padded_line))
            
            # Ensure all lines have same length
            for i in range(len(padded_lines)):
                if len(padded_lines[i]) < max_length:
                    padded_lines[i] += ' ' * (max_length - len(padded_lines[i]))
            
            # Scroll through all lines simultaneously
            for i in range(max_length - self.display_width + 1):
                windows = []
                for padded_line in padded_lines:
                    window = padded_line[i:i + self.display_width]
                    windows.append(window)
                
                self.clear_display()
                self.send_multiline_text(windows)
                
                self.logger.debug(f"Scrolling: {windows}")
                time.sleep(scroll_speed)
                
        except Exception as e:
            self.logger.error(f"Error scrolling text on all lines: {e}")

    def scroll_text_boucle(self, message, scroll_speed=0.01, scroll_all_lines=True, stop_event: threading.Event=None):
        """Scroll text in a loop, optionally using all available lines"""
        try:
            lines = message.split('\n')
            
            # Add padding for smooth scrolling
            padded_lines = []
            max_length = 0
            
            for line in lines:
                # padded_line = line
                if scroll_all_lines or len(line) >= self.display_width:
                    padded_line = ' ' * self.display_width + line + ' ' * self.display_width
                else:
                    padded_line = line
                padded_lines.append(padded_line)
                max_length = max(max_length, len(padded_line))

            # Scroll through all lines simultaneously in a loop
            while True:
                for i in range(max_length - self.display_width + 1):
                    windows = []
                    for padded_line in padded_lines:
                        window = padded_line
                        if scroll_all_lines or len(padded_line) >= self.display_width:
                            window = padded_line[i:i + self.display_width]
                        windows.append(window)
                    
                    self.clear_display()
                    self.send_multiline_text(windows)
                    if stop_event and stop_event.is_set():
                        self.logger.info("Scrolling stopped by event")
                        return
                    self.logger.debug(f"Scrolling: {windows}")
                    time.sleep(scroll_speed)
                    
        except Exception as e:
            self.logger.error(f"Error scrolling text in loop: {e}")

    def send_beep(self, duration=0.1):
        """Send a beep command to the VFD display"""
        if not self.ser:
            self.logger.error("Serial port not open")
            return
        try:
            # Common VFD beep commands
            for cmd in [b'\x07', b'\x1B\x42']:  # BEL character or ESC B
                self.ser.write(cmd)
                self.logger.debug(f"Sent beep command: {cmd.hex()}")
            time.sleep(duration)
        except Exception as e:
            self.logger.error(f"Error sending beep: {e}")

    def play_melody(self, melody_pattern, note_duration=0.2):
        """Play a simple melody using beep sequences"""
        try:
            self.logger.info("Playing melody...")
            for beep_count, pause_duration in melody_pattern:
                for _ in range(beep_count):
                    self.send_beep(note_duration)
                    time.sleep(0.1)
                time.sleep(pause_duration)
        except Exception as e:
            self.logger.error(f"Error playing melody: {e}")

    def play_startup_song(self):
        """Play a simple startup melody"""
        startup_melody = [
            (1, 0.2),  # Single beep
            (2, 0.3),  # Double beep
            (3, 0.5),  # Triple beep
            (1, 0.2),  # Final beep
        ]
        self.play_melody(startup_melody, note_duration=0.15)

    def play_notification_song(self):
        """Play a notification melody"""
        notification_melody = [
            (2, 0.1),  # Quick double beep
            (1, 0.2),  # Single beep
            (2, 0.3),  # Double beep with longer pause
        ]
        self.play_melody(notification_melody, note_duration=0.1)

if __name__ == "__main__":
    vfd = VFD220(port='COM4')
    
    if not vfd.connect():
        print("Error: Could not connect to VFD display")
        print("Ensure /dev/ttyS3 is accessible (e.g., sudo or dialout group)")
        print("Verify USB device: usbipd wsl attach --busid 1-8")
        print("Check wiring and VFD220 voltage (RS-232 vs TTL)")
        exit()

    try:
        vfd.clear_display()
        time.sleep(0.1)
        # vfd.center_text("VFD220 Starting...\nGG")
        # vfd.display_static_text("VFD220 Display Test\nInitializing...")
        vfd.scroll_text_boucle("ASQSQs\nWelcome to VFD220 Display!\nTOTAL=45 000 Ar", scroll_speed=0.5, scroll_all_lines=False)
        time.sleep(2)
        
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        vfd.disconnect()