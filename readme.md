# RGB Christmas Tree

Requires RGB Tree from
https://thepihut.com/products/3d-rgb-xmas-tree-for-raspberry-pi

Original code from
https://github.com/ThePiHut/rgbxmastree#rgbxmastree

*`tree.py`* modified to allow colour updates etc without actually sending update to the tree. This allows multiple changes all to be done at the same time.

Spiral and Rotate code taken from https://github.com/rendzina/XmasTree

# Description

Provides a simple web interface to the tree.

This allows selection from a number of LED Modes. Including "Sparkles","Hue","Layers","Spiral","Rotate" and "Fixed Colour". As well as an "Auto" option to reselect a random mode after a defined interval.

For convenience the web page also allows shutting down the Raspberry Pi and restarting of the code to simplify development.

# Installation

 ## Hardware
 The following hardware is used:
 - [Raspberry Pi Zero](https://www.raspberrypi.org/products/raspberry-pi-zero-w/)
 - [3D RGB Xmas Tree for Raspberry Pi](https://thepihut.com/products/3d-rgb-xmas-tree-for-raspberry-pi)

 ## Software
If you're using Raspbian Desktop, you don't need to install anything else. If you're
using Raspbian Lite, you'll need to install gpiozero with:

```bash
sudo apt install python3-gpiozero
```

Also requires the following
```bash
sudo pip install web.py
sudo pip install paho-mqtt
```

Might require the following if [sdnotify](https://github.com/bb4242/sdnotify) is not present
```bash
pip install sdnotify
```

Copy all files to /home/pi/tree

Install service so tree starts when the pi does
```bash
sudo systemctl enable /home/pi/tree/tree.service
sudo systemctl start tree
```

## Web Interface
Assuming pitree is the name of the pi

http://pitree:8080/tree

**Note** There is no security on the web server on port 8080
- Image copyright [ThePiHut](https://thepihut.com/)

## API interface

This is used by the web interface for changes and status updates

```
http://pitree:8080/api?action=<comand>&value=<value>
```

### Commands
- status      - Returns tree status in json format
- modeno      - Sets tree to a specific display type. Value is one of "Off", "Auto", "Sparkles", "Hue", "Layers", "Spiral", "Rotate", "Fixed Colour" or "On" which uses the default mode
- brightness  - Sets tree brightness. Value is 1 to 31 (Note Web interface only show 1-16 as Ive found even 1 is quite bright)
- percentage  - Sets brightness as a percentage, Value is 0 to 100
- shutdown    - Shutdown the Pi
- setdefaults - Sets the current setup as that for startup
- restart     - restarts the tree code
- colour      - Sets the tree colour. Value is R,B,G each in the range 0 to 255

### Examples 
1. Set Tree to Auto
    ```
    http://pitree.home:8080/api?action=mode&value=Auto
    ```
2. Get tree status
    ```
    http://pitree.home:8080/api?action=status&value=x
    ```
    Returns something like the following
    ```
    {"ModeText": "Auto", "ModeNo": 1, "Current": "Layers", "Brightness": 1, "displaytime": 120, "timeleft": 18}
    ```
3. Set tree colour to red
    ```
    http://pitree.home:8080/api?action=color&value=255,0,0
    ```

## Manual Startup

```bash
/usr/local/bin/python3 /home/pi/tree/thetree.py
```

# Changes
- 2.2 Fixed bugs
- 2.3 Added settings for Auto mode to cotrol which layout can be chosen
- 2.4 Added partial support for Homeassistant integration via MQTT