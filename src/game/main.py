# main.py
import sys
import os

# Get the absolute path of the directory containing the module you want to import
# This goes up one level from the current script's directory, then into 'utils'
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server'))

# Add the directory to Python's path if it's not already there
if module_path not in sys.path:
    sys.path.append(module_path)

from game import Game
from sensor import SensorServer
import sys

print(f"Using Python executable: {sys.executable}")
# server = SensorServer()
# server.start()

def main():
    """
    Initializes and runs the game.
    """
    server = SensorServer()
    server.start()

    game_instance = Game(server)
    game_instance.run()

if __name__ == "__main__":
    main()