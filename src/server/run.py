from sensor import SensorServer
import sys

print(f"Using Python executable: {sys.executable}")
server = SensorServer()
server.start()