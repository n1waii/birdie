#!/usr/bin/env python3
"""
Golf Club Sensor Data Server
Receives sensor data from ESP32-S3 and displays it in real-time
"""

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import json
import time
from datetime import datetime
import threading
import queue

app = Flask(__name__)
app.config['SECRET_KEY'] = 'golf_club_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Data storage
sensor_data_queue = queue.Queue()
latest_data = {}

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """Receive sensor data from ESP32"""
    try:
        data = request.get_json()
        
        # Add timestamp
        data['server_timestamp'] = datetime.now().isoformat()
        
        # Store latest data
        latest_data.update(data)
        
        # Add to queue for real-time updates
        sensor_data_queue.put(data)
        
        # Emit to connected clients
        socketio.emit('sensor_data', data)
        
        return jsonify({'status': 'success', 'message': 'Data received'})
    
    except Exception as e:
        print(f"Error receiving data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/latest-data')
def get_latest_data():
    """Get the latest sensor data"""
    return jsonify(latest_data)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('status', {'message': 'Connected to golf club sensor server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

def process_sensor_data():
    """Process sensor data in background thread"""
    while True:
        try:
            if not sensor_data_queue.empty():
                data = sensor_data_queue.get_nowait()
                
                # Calculate swing metrics
                accel_magnitude = (data['accelerometer']['x']**2 + 
                                 data['accelerometer']['y']**2 + 
                                 data['accelerometer']['z']**2)**0.5
                
                gyro_magnitude = (data['gyroscope']['x']**2 + 
                                data['gyroscope']['y']**2 + 
                                data['gyroscope']['z']**2)**0.5
                
                # Emit processed data
                processed_data = {
                    'raw_data': data,
                    'metrics': {
                        'accel_magnitude': accel_magnitude,
                        'gyro_magnitude': gyro_magnitude,
                        'swing_detected': accel_magnitude > 2.0  # Threshold for swing detection
                    }
                }
                
                socketio.emit('processed_data', processed_data)
                
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error processing data: {e}")
        
        time.sleep(0.01)  # 100Hz processing

if __name__ == '__main__':
    # Start background thread for data processing
    data_thread = threading.Thread(target=process_sensor_data, daemon=True)
    data_thread.start()
    
    print("Golf Club Sensor Server starting...")
    print("Dashboard: http://localhost:8080")
    print("API endpoint: http://localhost:8080/api/sensor-data")
    
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)
