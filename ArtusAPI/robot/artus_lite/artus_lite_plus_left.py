from .artus_lite_plus import ArtusLite_Plus

class ArtusLite_Plus_LeftHand(ArtusLite_Plus): # change any properties for the right hand
    def __init__(self):
        super().__init__(   joint_rotation_directions=[-1, 1, 1, 1, # thumb
                                        -1, 1, 1, # index
                                        -1, 1, 1, # middle
                                        -1, 1, 1, # ring
                                        -1, 1, 1], # pinky
                        )