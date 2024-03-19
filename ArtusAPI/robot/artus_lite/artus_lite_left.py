
import sys
from pathlib import Path
# Current file's directory
current_file_path = Path(__file__).resolve()
# Add the desired path to the system path
desired_path = current_file_path.parent.parent.parent.parent.parent
sys.path.append(str(desired_path))
# print(desired_path)

from ArtusAPI.robot.artus_lite.artus_lite import ArtusLite

class ArtusLite_LeftHand(ArtusLite): # change any properties for the left hand
    def __init__(self):
        super().__init__()