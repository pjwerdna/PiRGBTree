#!/usr/bin/env python3

# version 2.1
#
# Note no security on the wweb server on port 8080
# Requires RGB Tree from
#  https://thepihut.com/products/3d-rgb-xmas-tree-for-raspberry-pi

# Original code from
#  https://github.com/ThePiHut/rgbxmastree#rgbxmastree

# Spiral and Rotate code taken from
#  https://github.com/rendzina/XmasTree
#  Specifically XmasTree_Swirl.py

# Modified version required
from tree import RGBXmasTree
from colorzero import Color
from colorzero import Hue
# web server
import web
import subprocess

import random
import time
import logging
import logging.handlers
import argparse
import sys
import os
import json

# serial usb via https://hacks.mozilla.org/2017/02/headless-raspberry-pi-configuration-over-bluetooth/
# and
# https://www.instructables.com/id/Raspberry-Pi-Bluetooth-to-PuTTY-on-Windows-10/
#
import serial

# when called as a service
import sdnotify


import threading
import signal
from pathlib import Path

# Speed, delay between LED chnages
treespeed = 0.1

#global modelist, treemode, apphttp, tree
# run mode (See modelist)
treemode = 1

# default start brightness (Minimum)
requiredbrightness=1

# what to do when existing script
exitaction  = "none"

# seconds interval to call service wathcdog
WATCHDOGTIME = 5 #10

# run state
stopping = False

# Next display mode
nextdisplay = treemode

modelist = ["Off","Auto","Sparkles","Hue","Layers","Spiral","Rotate","Fixed Colour"]
modecount = len(modelist)-2

# sequence for error replies
global replyno
replyno  = 0

urls = (
    '/','error',
    '/api', 'api',
    '/api/(.+)', 'api',
    '/tree', 'webtree'
)

PixelList = (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23)
SPIRAL = [12,6,15,16,0,7,19,24,11,5,14,17,1,8,20,23,10,4,13,18,2,9,21,22,3]
ROTATE = [[12,11,10],[6,5,4],[15,14,13],[16,17,18],[0,1,2],[7,8,9],[19,20,21],[24,23,22]]

# Spiral (partialy done)
# 7,15,16,12,6,19,24,0), (8,14,17,11,5,20,23,1),(

def random_color():
    # Turn off 1 time in 4
    if (random.randrange(6) == 1):
        r = 0.0
        g = 0.0
        b = 0.0
    else:
        r = random.random()
        g = random.random()
        b = random.random()
    return (r, g, b)


# run the tree
class treethread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.updatedisplay = True
        self.stopped = False
        log.info("TreeThread Started")

    def next(self):
        self.updatedisplay = False

    def stop(self):
        self.stopped = True
        self.updatedisplay = False

    def run(self):
        global treemode, nextdisplay, fixed_colour

        log.info("Starting tree display")

        lastrandom = -1
        while(not self.stopped ):
            #time.sleep(10)
            if (treemode == 0):
                tree.off
                time.sleep(2)
                if (nextdisplay != 0):
                    log.debug("display off")
                nextdisplay = 0

            elif treemode == 1:
                nextdisplay = random.randrange(modecount)
                # Get New random mode
                while (lastrandom == nextdisplay):
                    nextdisplay = random.randrange(modecount)
                lastrandom = nextdisplay
                log.debug("display picked %d", nextdisplay)

            else: # Fixed display mode
                nextdisplay = treemode - 1
                log.debug("display fixed at %d", nextdisplay)

            if nextdisplay == 1:
                self.randomsparkles()

            elif nextdisplay == 2:
                self.hue()

            elif nextdisplay == 3:
                self.layers()

            elif nextdisplay == 4:
                self.spiral()

            elif nextdisplay == 5:
                self.rotate()

            elif nextdisplay == modecount:
                self.flicker()

            else:
                tree.off()
        tree.off()
        log.info("Stopping tree display")

    def randomsparkles(self):
        self.updatedisplay = True
        tree.display = True
        while(self.updatedisplay ):
            pixel = random.choice(tree)
            pixel.color = random_color()
        #tree.off()

    def hue(self):
        #tree.color = Color('red')

        self.updatedisplay = True
        tree.display = True
        LastPixel = PixelList[-1]
        while(self.updatedisplay ):
            #pixel = random.choice(tree)
            tree.display = False
            for pixelno in PixelList:
                #~ if pixel.color == (0,0,0):
                    #~ pixel.color = random_color()
                #~ pixel.color += Hue(deg=30)
                if (pixelno == LastPixel):
                    tree.display = True

                if tree[pixelno].color == (0,0,0):
                    tree[pixelno].color = random_color()
                #~ StartColour = tree[pixelno].color
                tree[pixelno].color += Hue(deg=20)
                #~ log.debug("do %d, %s to %s", pixelno, StartColour , tree[pixelno].color)
            if not self.updatedisplay:
                break

            #~ tree.color += Hue(deg=1)
        #tree.off()

    def layers(self):
        # LED IDs in each layer
        layers = ((0,6,7,12,15,16,19,24),(1,5,8,11,14,17,20,23), (2,4,9,10,13,18,21,22), (3,3))

        self.updatedisplay = True
        layer = 0
        direction = 1
        newcolor = random_color()
        while(self.updatedisplay ):
            #log.debug("layer %d", layer)
            # turn update of tree off
            tree.display = False
            lastpixel = layers[layer][-1]
            for pixelno in layers[layer]:
                #log.debug("do %d", pixelno)
                # turn tree updates back on for last pixel ini the layer
                if (pixelno == lastpixel):
                    # turn update on tree on
                    tree.display = True
                tree[pixelno].color = newcolor
                if not self.updatedisplay:
                    break
            #log.debug("redo %d", layers[layer][0])
#			tree[layers[layer][0]].color = newcolor

            # Change direction
            layer += direction
            if layer < 0:
                layer = 0
                direction = 1
                newcolor = random_color()
            elif layer > 3:
                layer = 3
                direction = -1
                newcolor = random_color()

    def flicker(self):
        global fixed_colour
        tree.color = fixed_colour

        self.updatedisplay = True
        tree.display = True
        while(self.updatedisplay ):
            pixel = random.choice(tree)
            if pixel.color == (0,0,0):
                pixel.color = fixed_colour
            else:
                pixel.color = (0,0,0)

    def spiral(self):
        self.updatedisplay = True
        tree.display = True
        length = len(SPIRAL)
        while(self.updatedisplay ):
            for number, val in enumerate(SPIRAL): # up from bottom
              #~ print("S",number,number/length,val)
              tree[val].color = Color.from_hsv(0.8,number/length,1).rgb
            if self.updatedisplay:
                for number, val in reversed(list(enumerate(SPIRAL))): # down from top
                    #~ print("S",number,number/length,val)
                    tree[val].color = Color.from_hsv(0.8,number/length,1).rgb

    def rotate(self):
        self.updatedisplay = True
        tree.display = True
        while(self.updatedisplay ):
            newcolor = random_color()
            for index, list in enumerate(ROTATE):
                #~ print(index,list)
                listnum = 0
                tree.display = False
                for number, val in enumerate(list):
                    listnum += 1
                    if (listnum == 3):
                        tree.display = True
                    tree[val].color = newcolor
                    # was
                    # tree[val].color = colors[index]
            if not self.updatedisplay:
                break

def signal_handler(signal, frame):
    log.info("Ctrl-C pressed")
    StopAll("")

def StopAll(action):
    global stopping, exitaction
    try:
        #displaythread.stopped = True
        #displaythread.stop()
        treeweb.stop()
        treemodeset = True
        stopping = True
        exitaction  = action
    except Exception as e: # stream not valid I guess
        log.error("Exception in StopAll: %s" , e)

# ------------------------------- Web Server --------------------------------------

class error:
    def GET(self):
        global replyno
        replies = {
            0: "+++Mr. Jelly! Mr. Jelly!+++",
            1: "+++Error At Address: 14, Treacle Mine Road, Ankh-Morpork+++",
            2: "+++MELON MELON MELON+++",
            3: "+++Divide By Cucumber Error. Please Reinstall Universe And Reboot +++",
            4: "+++Whoops! Here Comes The Cheese! +++",
            5: "+++Oneoneoneoneoneoneone+++",
        }
        replyno += 1
        if replyno == 6:
            replyno  = 0
        raise web.Unauthorized(replies.get(replyno, "+++Out of Cheese Error++"))

    def POST(self):
        return "+++Divide By Cucumber Error. Please Reinstall Universe And Reboot +++"


class webtree:
    def GET(self):
        global treemode, treemodeset

        user_data = web.input(mode="")

        if (user_data.mode != ""):
            try: 
                if (user_data.mode.upper == "ON"):
                    treemode = 1
                else:
                    treemode = modelist.index(user_data.mode)
                log.info("new treemode %s", treemode)
                treemodeset = True
            except:
                log.debug("Invalid treemode %s", user_data.mode)
        currentmode = makeselector(modelist,modelist[treemode])
        # Dont need this as javascript uses the API to do updates
        # currentmode += '<P><input type="submit" onclick="ChangeMode(\'\')" value="Change" >'
        return render.tree("RGB Christmas Tree",currentmode)

class api:
    def GET(self):
        global treemode, treemodeset, nextdisplay, requiredbrightness, fixed_colour, timeleft

        user_data = web.input(action="",value="")

        try:
            if (user_data.action != "status"):
                log.info("action=%s",user_data.action)
    #		if (user_data.value != None):
    #			log.info("value=%s",user_data.value)

            if (user_data.action == "mode"):
                try:
                    if (user_data.value.upper == "ON"):
                        treemode = defaulttreemode
                        requiredbrightness = defaultrequiredbrightness
                        tree.brightness_bits = requiredbrightness
                    else:
                        treemode = modelist.index(user_data.value)
                    log.info("new treemode %s", treemode)
                    treemodeset = True
                except:
                    log.info("unknown treemode %s", ser_data.value)

            elif (user_data.action == "modeno"):
                treemode = int(user_data.value)
                log.info("new treemode %d", treemode)
                treemodeset = True

            # Brightness value 1 to 31
            elif (user_data.action == "brightness"):
                requiredbrightness = int(user_data.value)
                if (requiredbrightness > 31):
                    requiredbrightness = 31
                elif (requiredbrightness < 1):
                    requiredbrightness = 1
                log.info("new brightness %d", requiredbrightness)
                tree.brightness_bits = requiredbrightness
                #tree.brightness = (requiredbrightness/31.0)/2.0

            # Brightness value as a percentage. Converted to 1 to 20 range
            elif (user_data.action == "percentage"):
                requiredbrightness = int(20/100*int(user_data.value))
                log.info("new brightness %d", requiredbrightness)
                if requiredbrightness < 1:
                    requiredbrightness = 1
                elif (requiredbrightness > 31):
                    requiredbrightness = 31
                log.info("new brightness (1-31) %d", requiredbrightness)
                tree.brightness_bits = int(requiredbrightness)

            elif (user_data.action == "shutdown"):
                StopAll("shutdown")
                log.debug("Shutting Down Now")

            elif (user_data.action == "setdefaults"):
                SaveDefaults()

            elif (user_data.action == "restart"):
                StopAll("")
                log.debug("Restarting Tree Display")
                time.sleep(2)

            elif ((user_data.action == "color") | (user_data.action == "colour")):
                log.debug("Colour Value %s", user_data.value)
                fixed_colour_list = user_data.value.split(",")
                fixed_colour = (int(fixed_colour_list[0]), int(fixed_colour_list[1]), int(fixed_colour_list[2]))
                treemode = modecount+1
                log.info("new colour %s", fixed_colour)
                treemodeset = True
        except Exception as e: # stream not valid I guess
            log.error("Exception in Web Server: %s" , e)

#		currentmode = makeselector(modelist,modelist[treemode])
#		currentmode += '<P><input type="submit" onclick="ChangeMode(\'\')" value="Change" >'

        Statusjson = { 'ModeText': modelist[treemode], 'ModeNo': treemode, 'Current': modelist[nextdisplay + 1], 'Brightness': requiredbrightness, 'displaytime': int(displaytime), 'timeleft': int(timeleft) }

        web.header('Content-Type','application/json')
        return json.dumps(Statusjson)



class WebApplicationHTTP(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global apphttp
        log.debug("Starting up http web server")

        # web pages in a subfolder
        home_dir = os.getcwd() + "/html"

        web.config.debug = False
        # consider
        #  https://stackoverflow.com/questions/7192788/how-do-i-redirrect-the-output-in-web-py
        #~ web.config.log_file = "WebServer.log"
        #~ web.config.log_toprint = False
        #~ web.config.log_tofile = True

        # this must be within the thread or it causes everything to happen twice!
        apphttp = web.application(urls, globals())

        web.httpserver.runsimple(apphttp.wsgifunc(), ("0.0.0.0", 8080))
        log.debug("Web server has stopped")

    def stop(self):
        #~ global users
        log.debug("Shutting down http web server")
        apphttp.stop()

def makeselector(Selections,CurrentSelection):
    makeselector = ""
    #'<select id="' + "selector" + '" name="' + "sel" + '" onchange="ChangeMode(\'\')" >'
    for selno in Selections:
        #log.info("selection %s", selno)
        if (selno == CurrentSelection):
            makeselector += '<option selected '
        else:
            makeselector += '<option '
        makeselector += 'value="' + selno +'">' + selno + '</option>\n'
    #makeselector += '<option value="XX">XX</option>\n'
    #makeselector += '</select>'
    return makeselector

def SaveDefaults():
    global treemode, requiredbrightness
    Settingsjson = { 'mode': treemode, 'brightness': requiredbrightness, "displaytime": displaytime }
    with open("settings.json", "w") as fi:
        json.dump(Settingsjson, fi)
    defaulttreemode = treemode
    defaultrequiredbrightness = requiredbrightness

# ------------------------------------------------ Main --------------------------------

# Decode arguments
parser = argparse.ArgumentParser()
# Log level
parser.add_argument('--log', help='log help')
# Start in service mode
parser.add_argument('--service',action='store_true', help='service help')
args = parser.parse_args()
loglevel = args.log
systemservice = args.service
authflags = args

LOGFILENAME="tree.log"

log = logging.getLogger('root')
log.setLevel(logging.DEBUG)

log_format = '[%(asctime)s] %(levelname)8s %(threadName)15s: %(message)s'

if (loglevel != None):
    # specify --log=DEBUG or --log=debug
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)

    loghandler = logging.handlers.RotatingFileHandler(LOGFILENAME,maxBytes=100000,backupCount=5)
    loghandler.setFormatter(logging.Formatter(log_format))

    log.addHandler(loghandler)
    log.setLevel(numeric_level)

else: # Default output to caller
    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(logging.DEBUG)
    loglevel = logging.DEBUG

    stream.setFormatter(logging.Formatter(log_format))

    log.addHandler(stream)

log.info("Logging started")

# webserver base folder
render = web.template.render('html/', cache=False)

# how long to display each animation
displaytime=60.0
timeleft = 0.0 # how long until the next displaychanged for AUto mode

# setup defaults
defaulttreemode = 1
defaultrequiredbrightness = requiredbrightness
defaultdisplaytime = displaytime

if (os.path.isfile("settings.json")):
    try:
        with open("settings.json", "r") as f:
            my_dict = json.load(f)
        treemode = my_dict["mode"]
        requiredbrightness = my_dict["brightness"]
        displaytime = float(my_dict["displaytime"])
        defaulttreemode = treemode
        defaultrequiredbrightness = requiredbrightness
        defaultdisplaytime = displaytime
        log.debug("Read defaults")
    except:
    	log.debug("settings.json file invalid")

tree = RGBXmasTree(brightness=requiredbrightness/31)
treemodeset = False

# start threads

# Start Web server
treeweb = WebApplicationHTTP()
treeweb.setDaemon(True)
treeweb.start()

# Start Tree display
displaythread = treethread()
displaythread.setDaemon(True)
displaythread.start()

# ------------------------------------- Timing loop ---------------------------------

"""
# Currently very unreliable so disabled
##ExecStart=/usr/lib/bluetooth/bluetoothd -C

##ExecStartPost=/usr/bin/sdptool add SP
##ExecStartPost=/bin/hciconfig hci0 piscan

# Need to start with something
fixed_colour = random_color()

# open Bluetooth serial interface for control
 
try:
    if (False):
        if (Path("/dev/rfcomm0").is_char_device == False):
            log.debug("rfcomm0 not found")
            with subprocess.Popen("sudo /usr/bin/sdptool add SP", stdout=subprocess.PIPE, shell=True) as proc:
                log.Info(proc.stdout.read())
            with subprocess.Popen("sudo /bin/hciconfig hci0 piscan", stdout=subprocess.PIPE, shell=True) as proc:
                log.Info(proc.stdout.read())
            if (Path("/dev/rfcomm0").is_char_device):
                log.debug("rfcomm0 created")
        else:
            log.debug("stopping rfcomm service")
            with subprocess.Popen("sudo systemctl stop rfcomm.service", stdout=subprocess.PIPE, shell=True) as proc:
                log.info(proc.stdout.read())
        log.debug("openning serial port")
        ser = serial.Serial('/dev/rfcomm0')  # open serial port
        log.debug(ser.name)         # check which port was really used
except Exception as e:
    log.debug("failed opening rfcomm %s", e) 
"""

# ------------------------------------- Timing loop ---------------------------------

stopping = False

try:

    # Trap this as an exception
    #signal.signal(signal.SIGINT, signal_handler)

    # notify /watchdog info from
    #   https://www.freedesktop.org/software/systemd/man/sd_notify.html#
    #
    # Inform systemd that we've finished our startup sequence...
    if systemservice:
        notifier = sdnotify.SystemdNotifier()
        notifier.notify("READY=1")
        log.info("Starting watchdog")

    timeleft = displaytime
    nextwatchdogtime = time.time() + WATCHDOGTIME # Next watch dog timer

    while not stopping:
        time.sleep(treespeed)
        timeleft = 	timeleft - treespeed
        #
        if (timeleft < 0) or (treemodeset == True):
            #log.debug("Change %d", treemode)
            displaythread.next()
            treemodeset = False
            timeleft = displaytime

        if systemservice:
            if (time.time() >= nextwatchdogtime):
                nextwatchdogtime = time.time() + WATCHDOGTIME # Next watch dog timer
                #log.info("watchdog")   
                notifier.notify("WATCHDOG=1")

except (KeyboardInterrupt, SystemExit):
    log.warning("Interrupted, shutting down")
    stopping = True
    treeweb.stop()
    StopAll("")

finally:
    log.debug("Main Stopped")

if systemservice:
    notifier.notify("STOPPING=1")

log.debug("Exiting")
#displaythread.join()
#treeweb.join()
#tree.off()

log.debug("Checking for shutdown")
# What to do when exiting
if (exitaction == "shutdown"):
    with subprocess.Popen("sudo /sbin/shutdown now", stdout=subprocess.PIPE, shell=True) as proc:
        log.Info(proc.stdout.read())
