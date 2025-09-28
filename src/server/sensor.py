# sensor_server_udp.py
import socket
import json
import threading

class SensorServer:
    def __init__(self, host='0.0.0.0', port=50000):
        self.host = host
        self.port = port
        self.server_socket = None
        self._is_running = False
        self._server_thread = None
        self._latest_data = None
        self._data_lock = threading.Lock()

    def _server_loop(self):
        # Use SOCK_DGRAM for UDP
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.host, self.port))
        print(f"[SERVER] UDP Server listening on {self.host}:{self.port}")

        while self._is_running:
            try:
                # Receive data and the address it came from
                data, addr = self.server_socket.recvfrom(1024) 
                message = data.decode('utf-8')
                
                try:
                    sensor_data = json.loads(message)
                    with self._data_lock:
                        self._latest_data = sensor_data
                    #print(f"Received from {addr}: {sensor_data}")
                except json.JSONDecodeError:
                    print(f"[WARNING] Invalid JSON received from {addr}: {message}")

            except Exception as e:
                if self._is_running:
                    print(f"[ERROR] An error occurred: {e}")
                break
        
        print("[SERVER] Server loop shutting down.")
        self.server_socket.close()

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self._server_thread = threading.Thread(target=self._server_loop)
        self._server_thread.start()
        print("[SERVER] Server started.")

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        # Closing the socket will cause recvfrom to raise an exception, stopping the loop.
        self.server_socket.close() 
        self._server_thread.join()
        print("[SERVER] Server stopped.")

    def get_latest_data(self):
        with self._data_lock:
            return self._latest_data