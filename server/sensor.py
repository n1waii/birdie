# sensor_server.py
import socket
import json
import threading

class SensorServer:
    """
    A server class that listens for streaming JSON data from a sensor client (like an ESP32),
    parses it, and makes the latest data available in a thread-safe manner.
    """
    def __init__(self, host='35.3.180.140', port=50000):
        """
        Initializes the server.
        Args:
            host (str): The host address to bind to. '0.0.0.0' means all available interfaces.
            port (int): The port to listen on.
        """
        self.host = host
        self.port = port
        self.server_socket = None
        self._is_running = False
        self._server_thread = None
        
        # Thread-safe storage for the latest sensor data
        self._latest_data = None
        self._data_lock = threading.Lock()

    def _client_handler(self, client_socket, addr):
        """
        Handles an individual client connection in its own thread.
        """
        print(f"[SERVER] Accepted connection from {addr}")
        buffer = ""
        try:
            while self._is_running:
                data = client_socket.recv(1024)
                if not data:
                    break # Client disconnected

                buffer += data.decode('utf-8')

                # Process all complete messages delimited by a newline
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    try:
                        sensor_data = json.loads(message)
                        
                        # Use a lock to safely update the shared data
                        with self._data_lock:
                            self._latest_data = sensor_data
                        
                        # Optional: Log the received data
                        # print(f"[DATA] Received from {addr}: {self._latest_data}")

                    except json.JSONDecodeError:
                        print(f"[WARNING] Invalid JSON received from {addr}: {message}")
        
        except ConnectionResetError:
            print(f"[INFO] Client {addr} forcefully disconnected.")
            
        finally:
            print(f"[SERVER] Client {addr} disconnected.")
            client_socket.close()

    def _server_loop(self):
        """
        The main server loop that accepts new connections.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[SERVER] Listening on {self.host}:{self.port}")

            while self._is_running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    # Start a new thread for each client
                    client_thread = threading.Thread(
                        target=self._client_handler,
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True # Allows main program to exit even if threads are running
                    client_thread.start()
                except OSError:
                    # This can happen when the socket is closed while accept() is blocking
                    break

        finally:
            print("[SERVER] Server loop shutting down.")
            if self.server_socket:
                self.server_socket.close()

    def start(self):
        """
        Starts the server in a background thread.
        """
        if self._is_running:
            print("[SERVER] Server is already running.")
            return

        self._is_running = True
        self._server_thread = threading.Thread(target=self._server_loop)
        self._server_thread.start()
        print("[SERVER] Server started.")

    def stop(self):
        """
        Stops the server gracefully.
        """
        if not self._is_running:
            print("[SERVER] Server is not running.")
            return

        self._is_running = False
        # To unblock the server_socket.accept(), we can connect to it ourselves
        try:
            # This is a trick to wake up the accept() call
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((self.host, self.port))
        except ConnectionRefusedError:
            pass # Expected if the server is already shutting down
        
        self._server_thread.join()
        print("[SERVER] Server stopped.")

    def get_latest_data(self):
        """
        Returns the most recently received sensor data.
        Returns:
            dict or None: The latest data dictionary, or None if no data has been received.
        """
        with self._data_lock:
            return self._latest_data