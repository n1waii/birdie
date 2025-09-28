# Golf Club Sensor Setup Guide

## Hardware Requirements

### ESP32-S3 N16R8
- ESP32-S3 development board
- USB-C cable for programming and power

### MPU Sensor
- MPU6050 or MPU9250 (recommended)
- I2C interface
- 3.3V compatible

### Wiring Diagram

```
ESP32-S3    MPU6050/MPU9250
--------    ----------------
3.3V   -->  VCC
GND    -->  GND
GPIO21 -->  SDA
GPIO22 -->  SCL
```

## Software Setup

### 1. Arduino IDE Setup

1. Install Arduino IDE (latest version)
2. Install ESP32 board package:
   - Go to File > Preferences
   - Add this URL to "Additional Board Manager URLs":
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
3. Go to Tools > Board > Boards Manager
4. Search for "ESP32" and install "ESP32 by Espressif Systems"
5. Install required libraries:
   - ArduinoJson (by Benoit Blanchon)
   - WiFi (included with ESP32)

### 2. ESP32 Code Configuration

1. Open `esp32_golf_club.ino` in Arduino IDE
2. Update WiFi credentials:
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```
3. Update server URL (replace with your laptop's IP):
   ```cpp
   const char* serverURL = "http://192.168.1.100:8080/api/sensor-data";
   ```
4. Select board: Tools > Board > ESP32 Arduino > ESP32S3 Dev Module
5. Configure upload settings:
   - Upload Speed: 921600
   - CPU Frequency: 240MHz
   - Flash Mode: QIO
   - Flash Size: 16MB
   - Partition Scheme: Default 4MB with spiffs
6. Upload the code

### 3. Python Server Setup

1. Install Python 3.8 or later
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python server.py
   ```
4. Open your browser and go to: `http://localhost:8080`

## Usage

### Calibration
1. Place the golf club on a flat surface
2. Power on the ESP32
3. Wait for "Gyroscope calibrated" message in Serial Monitor
4. The system is ready to use

### Data Collection
1. Start the Python server on your laptop
2. Ensure ESP32 is connected to the same WiFi network
3. Open the dashboard in your browser
4. Swing the golf club to see real-time data

### Dashboard Features
- Real-time accelerometer and gyroscope data
- Swing detection with visual indicators
- Data visualization charts
- Raw data table
- Temperature monitoring

## Troubleshooting

### ESP32 Issues
- **WiFi Connection Failed**: Check SSID and password
- **No Data Received**: Verify server URL and network connectivity
- **Sensor Errors**: Check wiring connections

### Server Issues
- **Port Already in Use**: Change port in server.py
- **Module Not Found**: Install requirements.txt dependencies
- **Connection Refused**: Check firewall settings

### Data Quality
- **Noisy Data**: Ensure stable power supply
- **Calibration Issues**: Restart ESP32 and recalibrate
- **Missing Data**: Check I2C connections

## Advanced Configuration

### Sampling Rate
Modify the delay in the main loop:
```cpp
delay(50); // 20Hz sampling rate
```

### Swing Detection Threshold
Adjust in server.py:
```python
'swing_detected': accel_magnitude > 2.0  # Threshold for swing detection
```

### Data Range
For different MPU configurations, adjust the conversion factors in the Arduino code:
```cpp
// For ±4g range: / 8192.0
// For ±8g range: / 4096.0
```

## Network Configuration

### Finding Your Laptop's IP
- Windows: `ipconfig`
- macOS/Linux: `ifconfig` or `ip addr`

### Firewall Settings
Ensure port 8080 is open for incoming connections.

## Safety Notes

- Secure the ESP32 and sensor to the golf club properly
- Use appropriate mounting materials
- Test in a safe environment first
- Be aware of battery life limitations
