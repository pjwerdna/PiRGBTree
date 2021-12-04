# RGB Christmas Tree

Requires RGB Tree from
https://thepihut.com/products/3d-rgb-xmas-tree-for-raspberry-pi

Original code from
https://github.com/ThePiHut/rgbxmastree#rgbxmastree

*`tree.py`* modified to allow colour updates etc without actually sending update to the tree. This allows multiple changes all to be done at the same time.

Spiral and Rotate code taken from https://github.com/rendzina/XmasTree

## Installation

 ## Hardware
 The following hardware is used:
 - [Raspberry Pi Zero](https://www.raspberrypi.org/products/raspberry-pi-zero-w/)
 - [3D RGB Xmas Tree for Raspberry Pi](https://thepihut.com/products/3d-rgb-xmas-tree-for-raspberry-pi)

 ## Software
If you're using Raspbian Desktop, you don't need to install anything. If you're
using Raspbian Lite, you'll need to install gpiozero with:

```bash
sudo apt install python3-gpiozero
```
Copy all files to /home/pi/tree

Install service so tree startss when the pi does
```bash
sudo systemctl enable /home/pi/tree/tree.service
```

## Web Interface
Assuming pitree.home is the name of the pi

http://pitree.home:8080/tree

**Note** There is no security on the web server on port 8080
- Image copyright [https://thepihut.com/](ThePiHut)

## API interface

This is used by the web interface for changes and suatus updates

/api?action=&lt;comand&gt;&amp;value=&lt;value&gt;

### Commands
- status      - Returns tree status in json format
- modeno      - Sets tree to a specific display type. Value is one of "Off", "Auto", "Sparkles", "Hue", "Layers", "Spiral", "Rotate", "Fixed Colour" or "On" which uses the default mode
- brightness  - Sets tree brightness. Value is 1 to 31
- percentage  - Sets brightness as a percentage, Value is 0 to 100
- shutdown    - Shutdown the Pi
- setdefaults - Sets the current setup as that for startup
- restart     - restarts the tree code
- colour      - Sets the tree colour. Value is R,B,G

### Examples 
Set Tree to Auto
```
http://pitree.home:8080/api?action=mode&value=Auto
```
Get tree status
```
http://pitree.home:8080/api?action=status&value=x
```
Set tree colour to red
```
http://pitree.home:8080/api?action=color&value=255,0,0
```

## Manual Startup

```bash
/usr/local/bin/python3.7 /home/pi/tree/thetree.py
```
