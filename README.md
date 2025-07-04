# VFD220 Display Controller

A Python library for controlling VFD220 (Vacuum Fluorescent Display) devices via serial communication.

## Features

- **Multi-baud rate auto-detection** - Automatically detects the correct baud rate (9600, 2400, 4800, 19200)
- **Text display** - Display static text across multiple lines
- **Scrolling text** - Horizontal scrolling with customizable speed
- **Cursor positioning** - Move cursor to specific positions
- **Audio feedback** - Built-in beep functionality and melody playback
- **Flexible display sizing** - Configurable display dimensions (default: 20x2)
- **Comprehensive logging** - Detailed logging for debugging and monitoring
- **Environment configuration** - Configure settings via .env file

## Hardware Requirements

- VFD220 display module
- USB-to-Serial adapter or direct serial connection
- Proper voltage level conversion (RS-232 vs TTL)

## Installation

1. Clone or download the project files
2. Install required dependencies:
```bash
pip install pyserial python-dotenv
```

3. Copy `.env.example` to `.env` and configure your settings
4. Connect your VFD220 display to the serial port

## Configuration

### Environment Variables (.env file)

Create a `.env` file in the project root with the following variables:

```bash
# Serial port configuration
VFD_PORT=COM4
VFD_BAUD_RATES=9600,2400,4800,19200

# Display configuration
VFD_WIDTH=20
VFD_HEIGHT=2

# Logging configuration
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_DATE_FORMAT=%Y-%m-%d %H:%M:%S
LOG_TO_FILE=False
LOG_FILE_PATH=vfd220.log
```

### Configuration Options

#### Serial Configuration
- `VFD_PORT`: Serial port name (e.g., 'COM4', '/dev/ttyUSB0')
- `VFD_BAUD_RATES`: Comma-separated list of baud rates to try

#### Display Configuration
- `VFD_WIDTH`: Display width in characters
- `VFD_HEIGHT`: Display height in lines

#### Logging Configuration
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT`: Log message format string
- `LOG_DATE_FORMAT`: Date format for log messages
- `LOG_TO_FILE`: Enable/disable file logging (True/False)
- `LOG_FILE_PATH`: Path to log file when file logging is enabled

## Quick Start

```python
from vfd220 import VFD220

# Initialize VFD display (uses .env configuration)
vfd = VFD220()

# Or override specific settings
vfd = VFD220(port='COM3', display_width=16, display_height=4)

# Connect to display
if vfd.connect():
    # Display static text
    vfd.display_static_text("Hello World!\nVFD220 Display")
    
    # Clean up
    vfd.disconnect()
else:
    print("Failed to connect to VFD display")
```

## API Reference

### Class: VFD220

#### Constructor
```python
VFD220(port='COM4', baud_rates=[9600, 2400, 4800, 19200], display_width=20, display_height=2)
```

**Parameters:**
- `port` (str): Serial port name (e.g., 'COM4', '/dev/ttyUSB0')
- `baud_rates` (list): List of baud rates to try during connection
- `display_width` (int): Display width in characters (default: 20)
- `display_height` (int): Display height in lines (default: 2)

#### Connection Methods

##### `connect()`
Attempts to connect to the VFD display using auto-detection of baud rates.

**Returns:** `bool` - True if connection successful, False otherwise

##### `disconnect()`
Closes the serial connection.

#### Display Methods

##### `send_text(message)`
Sends a single line of text to the display.

**Parameters:**
- `message` (str): Text to display (will be padded to display width)

##### `send_multiline_text(lines)`
Sends multiple lines of text to fill the entire display.

**Parameters:**
- `lines` (list): List of strings, one per display line

##### `display_static_text(message)`
Displays static text across all available lines.

**Parameters:**
- `message` (str): Multi-line text (use \n for line breaks)

##### `center_text(message)`
Centers text on the display.

**Parameters:**
- `message` (str): Text to center (supports multi-line with \n)

##### `clear_display()`
Clears the display screen.

#### Scrolling Methods

##### `scroll_text(message, scroll_speed=0.01)`
Scrolls text horizontally once through all display lines.

**Parameters:**
- `message` (str): Multi-line text to scroll
- `scroll_speed` (float): Delay between scroll steps in seconds

##### `scroll_text_boucle(message, scroll_speed=0.01, scroll_all_lines=True, stop_event=None)`
Scrolls text in a continuous loop.

**Parameters:**
- `message` (str): Multi-line text to scroll
- `scroll_speed` (float): Delay between scroll steps in seconds
- `scroll_all_lines` (bool): Whether to scroll all lines or only long ones
- `stop_event` (threading.Event): Event to stop scrolling

#### Cursor Methods

##### `move_cursor(row, col)`
Moves cursor to specific position.

**Parameters:**
- `row` (int): Row number (0-based)
- `col` (int): Column number (0-based)

#### Audio Methods

##### `send_beep(duration=0.1)`
Sends a beep command to the display.

**Parameters:**
- `duration` (float): Beep duration in seconds

##### `play_melody(melody_pattern, note_duration=0.2)`
Plays a melody using beep sequences.

**Parameters:**
- `melody_pattern` (list): List of tuples (beep_count, pause_duration)
- `note_duration` (float): Duration of each beep

##### `play_startup_song()`
Plays a predefined startup melody.

##### `play_notification_song()`
Plays a predefined notification melody.

## Usage Examples

### Basic Text Display
```python
vfd = VFD220(port='COM4')
if vfd.connect():
    vfd.display_static_text("Temperature: 25°C\nHumidity: 60%")
    vfd.disconnect()
```

### Scrolling Text
```python
vfd = VFD220(port='COM4')
if vfd.connect():
    vfd.scroll_text("This is a very long message that will scroll across the display\nSecond line also scrolling", scroll_speed=0.3)
    vfd.disconnect()
```

### Continuous Scrolling with Stop Control
```python
import threading

vfd = VFD220(port='COM4')
stop_event = threading.Event()

if vfd.connect():
    # Start scrolling in a separate thread
    scroll_thread = threading.Thread(
        target=vfd.scroll_text_boucle,
        args=("Welcome to our store!\nToday's special: 50% off", 0.5, False, stop_event)
    )
    scroll_thread.start()
    
    # Stop after 10 seconds
    time.sleep(10)
    stop_event.set()
    scroll_thread.join()
    
    vfd.disconnect()
```

### Audio Feedback
```python
vfd = VFD220(port='COM4')
if vfd.connect():
    vfd.play_startup_song()
    vfd.display_static_text("System Ready\nPress any key")
    vfd.disconnect()
```

## Troubleshooting

### Connection Issues
- Verify the correct COM port is specified
- Check if the port is accessible (may require admin privileges)
- Ensure proper wiring and voltage levels (RS-232 vs TTL)
- Try different baud rates manually if auto-detection fails

### Display Issues
- Check display power supply
- Verify serial communication settings
- Try different VFD clear commands if display doesn't clear properly

### Common Error Messages
- **"Serial port not open"**: Call `connect()` before sending commands
- **"Failed to open port"**: Check port permissions and availability
- **"Could not connect to VFD display"**: Verify hardware connections and port settings

## Logging

The library includes comprehensive logging that can be configured via environment variables:

### Basic Logging Setup
```python
# Logging is automatically configured from .env file
from vfd220 import VFD220
vfd = VFD220()  # Logger is set up with .env configuration
```

### Enable Debug Logging
Set in your `.env` file:
```bash
LOG_LEVEL=DEBUG
```

### Enable File Logging
Set in your `.env` file:
```bash
LOG_TO_FILE=True
LOG_FILE_PATH=logs/vfd220.log
```

### Custom Logging Configuration
```python
import logging
import os

# Override environment settings programmatically
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['LOG_TO_FILE'] = 'True'

from vfd220 import VFD220
vfd = VFD220()
```

## License

This project is provided as-is for educational and commercial use.

## Contributing

Feel free to submit issues and enhancement requests!