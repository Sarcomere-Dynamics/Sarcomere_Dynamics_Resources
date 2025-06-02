<img src='../../../data/images/SarcomereLogoHorizontal.svg'>

# Artus Lite+

## Introduction
The Artus Lite+ has the same basic control and characteristics of the Artus Lite. However, these are equipped with fingertip force sensors. Here are the sensors that have been integrated to date. 

* Touchlabs - Data is separate from ArtusAPI communication
* Contactile - Data integrated

## Difference between Artus Lite and Artus Lite+
Mechanically, there is no difference between the two hands, the sole difference is the feedback data and finger tip sensors. 

The main difference between the two hands is listed below:
* Artus Lite+ output does not output the joint currents anymore, output is the x,y,z vector forces from the 5 fingertips. Output still includes the ack value and 16 joint angles. 
* If writing your own communication, Artus Lite+ data output is a fixed length of 77 bytes long whereas the Artus Lite is 65 bytes long. 
