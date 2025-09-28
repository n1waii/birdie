# Golf Club Sensor System

A real-time golf club motion tracking system using ESP32-S3 and MPU sensor for MHacks 25.

## Features

- Real-time accelerometer and gyroscope data collection
- WiFi data transmission to local server
- Web-based dashboard with live visualization
- Swing detection and analysis
- Temperature monitoring

## Hardware

- ESP32-S3 N16R8 development board
- MPU6050/MPU9250 motion sensor
- WiFi connectivity

## Quick Start

1. **Setup ESP32**: Upload `esp32_golf_club.ino` to your ESP32-S3
2. **Configure WiFi**: Update WiFi credentials in the Arduino code
3. **Start Server**: Run `python server.py` on your laptop
4. **View Dashboard**: Open `http://localhost:8080` in your browser

## Files

- `esp32_golf_club.ino` - ESP32 Arduino code for sensor data collection
- `server.py` - Python Flask server for data reception and display
- `templates/dashboard.html` - Web dashboard for real-time visualization
- `requirements.txt` - Python dependencies
- `SETUP_GUIDE.md` - Detailed setup instructions

## Requirements

- Arduino IDE with ESP32 support
- Python 3.8+ with Flask and SocketIO
- MPU6050 or MPU9250 sensor
- WiFi network

See `SETUP_GUIDE.md` for detailed installation and configuration instructions.
