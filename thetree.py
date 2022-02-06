#!/usr/bin/env python3

# version 2.3
#
# Note no security on the web server on port 8080
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

# run mode (See modelist)
treestate = 2
currenttreemode = 1

# default start brightness (Minimum) and maxiumum
requiredbrightness=1
maxbrightness = 20

# seconds interval to call service wathcdog
WATCHDOGTIME = 5 #10

# run state
stopping = False

# Next display mode
nextdisplay = currenttreemode
lasttreemode = currenttreemode # tracks last tremode via api that wasnt "off"
lasttreestate = treestate

statelist = ["Off","On","Random"]
modelist = ["Sparkles","Hue","Layers","Spiral","Rotate","Fixed Colour"]
modecount = len(modelist)
allowedmodes = [0,1,2,3,4,5,6,7]

# sequence for error replies
global replyno
replyno  = 0

urls = (
    '/','error',
    '/api', 'api',
    '/api/(.+)', 'api',
    '/tree', 'webtree',
    '/settings', 'settings'
)

PixelList = (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23)
SPIRAL = [12,6,15,16,0,7,19,24,11,5,14,17,1,8,20,23,10,4,13,18,2,9,21,22,3]

# Spiral (partialy done)
# 7,15,16,12,6,19,24,0), (8,14,17,11,5,20,23,1),(

def random_color():
    # Turn off 1 time in 6
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
        global currenttreemode, nextdisplay, fixed_colour

        log.info("Starting tree display")

        lastrandomdisplay = -1
        while(not self.stopped ):
            if (treestate == 0):
                tree.display = True
                tree.off()
                time.sleep(1)

            elif treestate == 2:
                #nextdisplay = random.randrange(modecount)
                allowedmodescopy = allowedmodes.copy()
                if (allowedmodescopy.count(lastrandomdisplay)):
                    allowedmodescopy.remove(lastrandomdisplay)
                    log.debug("choose from " + ",".join(str(e) for e in allowedmodescopy) + " removed " + str(lastrandomdisplay))
                randompick = random.randrange(0,len(allowedmodescopy))
                #log.debug("randompick=" + str(randompick) +" max " + str(len(allowedmodescopy)))
                nextdisplay = allowedmodescopy[randompick]
                
                # Get New random mode if its the same as the last one
                # while (lastrandomdisplay == nextdisplay) & (len(allowedmodescopy) > 1):
                #     #nextdisplay = random.randrange(modecount)
                #     randompick = random.randrange(0,len(allowedmodescopy))
                #     log.debug("randompick=" + str(randompick) +" max " + str(len(allowedmodescopy)))
                #     nextdisplay = allowedmodescopy[randompick]
                lastrandomdisplay = nextdisplay

            else: # Fixed display mode
                nextdisplay = currenttreemode
                log.debug("display fixed at %d", nextdisplay)

            if (treestate != 0):
                log.debug("display picked %d", nextdisplay)
                if nextdisplay == 0:
                    self.randomsparkles()

                elif nextdisplay == 1:
                    self.hue()

                elif nextdisplay == 2:
                    self.layers()

                elif nextdisplay == 3:
                    self.spiral()

                elif nextdisplay == 4:
                    self.rotate()

                elif nextdisplay == 5:
                    self.flicker()

                else:
                    treemodeset = True
                    tree.off()

        treemodeset = True
        tree.off()
        log.info("Stopping tree display")

    def randomsparkles(self):
        self.updatedisplay = True
        tree.display = True
        pixel = 0
        lastpixel = pixel
        while(self.updatedisplay ):
            while (pixel == lastpixel):
                pixel = random.choice(tree)
            lastpixel = pixel
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
            #tree[layers[layer][0]].color = newcolor

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
        pixel = 0
        lastpixel = pixel
        while(self.updatedisplay ):
            while (lastpixel == pixel):
                pixel = random.choice(tree)
            lastpixel = pixel
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
        ROTATE = [[12,11,10],[6,5,4],[15,14,13],[16,17,18],[0,1,2],[7,8,9],[19,20,21],[24,23,22]]

        self.updatedisplay = True
        tree.display = True
        while(self.updatedisplay ):
            newcolor = random_color()
            for index, list in enumerate(ROTATE):
                #~ print(index,list)
                listnum = 0
                tree.display = False
                if (self.updatedisplay ):
                    for number, val in enumerate(list):
                        listnum += 1
                        if (listnum == 3):
                            tree.display = True
                        tree[val].color = newcolor
                        # was
                        # tree[val].color = colors[index]
                else:
                    break

def signal_handler(signal, frame):
    log.info("Ctrl-C pressed")
    StopAll("")

def StopAll(action):
    global stopping
    try:
        #displaythread.stopped = True
        #displaythread.stop()
        treeweb.stop()
        treemodeset = True
        stopping = True
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
        global currenttreemode, treemodeset, allowedmodes, treestate

        #user_data = web.input(mode="")

        #if (user_data.mode != ""):
        #    try: 
        #        if (user_data.mode.upper == "ON"):
        #            currenttreemode = 1
        #        else:
        #            currenttreemode = modelist.index(user_data.mode)
        #        log.info("new treemode %s", currenttreemode)
        #        treemodeset = True
        #    except:
        #        log.debug("Invalid treemode %s", user_data.mode)
        currentstate = makeselector(statelist,statelist[treestate]) 
        currentmode = makeselector(modelist,modelist[currenttreemode])
        modeno = 0
        checks = ""
        for modevalue in modelist:
            #log.info("mode=" + modevalue)
            #Statusjson['mode' + str(modeno)] = modevalue
            onchange="ToggleMode('togglemode', '" + str(modeno) + "')"
            checked = allowedmodes.count(modeno)
            checks = checks + makeinput("mode" + str(modeno), modevalue, onchange,checked) + modevalue + "<BR>\n"
            modeno = modeno + 1
        brightnessoptions = makeselector(range(1,maxbrightness+1), requiredbrightness)

        return render.tree("RGB Christmas Tree",currentstate,currentmode,checks, brightnessoptions)

class settings:
    def GET(self):
        currentmode = makeselector(modelist,modelist[currenttreemode])
        modeno = 0
        checks = ""
        for modevalue in modelist:
            #log.info("mode=" + modevalue)
            #Statusjson['mode' + str(modeno)] = modevalue
            onchange="ToggleMode('togglemode', '" + str(modeno) + "')"
            checks = checks + "<input type=\"checkbox\" id=\"mode" + str(modeno) + "\" name=\"" + modevalue + "\" onclick=\"" + onchange + "\">" + modevalue + "<BR>"
            modeno = modeno + 1

        return render.settings("RGB Christmas Tree",currentmode,checks)

class api:
    def GET(self):
        global currenttreemode, treemodeset, nextdisplay, requiredbrightness, fixed_colour, timeleft, allowedmodes, displaytime, lasttreemode, treestate, maxbrightness, lasttreestate

        user_data = web.input(action="",value="")

        try:
            action = user_data.action.upper()
            if (action != "STATUS"):
                if (user_data.value != ""):
                    log.info("action=%s, value=%s",action,user_data.value)
                else:
                    log.info("action=%s",action)
            #else:
            #    log.info("action=%s, value=%s",user_data.action,user_data.value)


            if (action == "STATE"):
                try:
                    #if (user_data.value.upper() == "ON"):
                        #currenttreemode = defaulttreemode
                    #    treestate = statelist.index(user_data.value)
                        #requiredbrightness = defaultrequiredbrightness
                        #tree.brightness_bits = requiredbrightness
                    #else
                    if (user_data.value.upper() == "LAST"):
                        currenttreemode = lasttreemode
                        treestate = lasttreestate
                        if (currenttreemode == 0):
                            currenttreemode = defaulttreemode
                        if (treestate == 0):
                            treestate = defaulttreestate
                    else:
                        treestate = statelist.index(user_data.value)

                    log.info("new treestate %s", treestate)
                    treemodeset = True
                    if (currenttreemode >= 0):
                        lasttreemode = currenttreemode
                    if (treestate != lasttreestate):
                        lasttreestate = treestate
                except Exception as e:
                    log.info("unknown treemode %s", user_data.value)
                    log.error("Exception is '%s'" , e)

            if (action == "MODE"):
                try:
                    currenttreemode = modelist.index(user_data.value)
                    log.info("new treemode %s", currenttreemode)
                    treemodeset = True
                    if (treemode >= 0):
                        lasttreemode = currenttreemode
                except Exception as e:
                    log.info("unknown treemode %s", user_data.value)
                    log.error("Exception is '%s'" , e)

            elif (action == "MODENO"):
                currenttreemode = int(user_data.value)
                log.info("new treemode %d", currenttreemode)
                treemodeset = True
                if (treemode >= 0):
                    lasttreemode = currenttreemode
                    
            # Brightness value 1 to 31
            elif (action == "BRIGHTNESS"):
                requiredbrightness = int(user_data.value)
                if (requiredbrightness > maxbrightness):
                    requiredbrightness = maxbrightness
                elif (requiredbrightness < 1):
                    requiredbrightness = 1
                log.info("new brightness %d", requiredbrightness)
                tree.brightness_bits = requiredbrightness
                #tree.brightness = (requiredbrightness/31.0)/2.0

            # Brightness value as a percentage. Converted to 1 to 20 range
            elif (action == "PERCENTAGE"):
                requiredbrightness = int((maxbrightness/100)*int(user_data.value))
                log.info("new brightness %s", user_data.value)
                if requiredbrightness < 1:
                    requiredbrightness = 1
                elif (requiredbrightness > 31):
                    requiredbrightness = 31
                log.info("new brightness (1-31) %d", requiredbrightness)
                tree.brightness_bits = int(requiredbrightness)

            elif (action == "SHUTDOWN"):
                StopAll("shutdown")
                log.debug("Shutting Down Now")
                with subprocess.Popen("sudo /sbin/shutdown now", stdout=subprocess.PIPE, shell=True) as proc:
                    log.Info(proc.stdout.read())

            elif (action == "SETDEFAULTS"):
                SaveDefaults()

            elif (action == "RESTART"):
                log.debug("Restarting Tree Display")
                StopAll("")
                time.sleep(2)

            elif (action == "DISPLAYTIME"):
                displaytime = int(user_data.value)

            elif ((action == "COLOR") | (action == "COLOUR")):
                log.debug("Colour Value %s", user_data.value)
                fixed_colour_list = user_data.value.split(",")
                fixed_colour = (int(fixed_colour_list[0])/255, int(fixed_colour_list[1])/255, int(fixed_colour_list[2])/255)
                currenttreemode = modecount-1
                log.info("new colour %s", fixed_colour)
                treemodeset = True
                treestate = 1 # fixed mode
                if (currenttreemode >= 0):
                    lasttreemode = currenttreemode                
            elif (action == "TOGGLEMODE"):
                modeno = int(user_data.value)
                if (allowedmodes.count(modeno) > 0):
                    allowedmodes.remove(modeno)
                else:
                    allowedmodes.append(modeno)

        except Exception as e: # stream not valid I guess
            log.error("Exception in Web Server: %s" , e)

        #		currentmode = makeselector(modelist,modelist[currenttreemode])
        #		currentmode += '<P><input type="submit" onclick="ChangeMode(\'\')" value="Change" >'

        Statusjson = { 'TreeState': statelist[treestate], 'TreeStateNo': treestate, 'ModeText': modelist[currenttreemode], 'ModeNo': currenttreemode, 'Current': modelist[nextdisplay], 'Brightness': requiredbrightness, 'displaytime': int(displaytime), 'timeleft': int(timeleft) }
        #if (user_data.action == "status") & (user_data.value == "modes"):
        #modeno = 0
        #for modevalue in modelist:
        #    #log.info("mode=" + modevalue)
        #    if (modeno > 1):
        #       Statusjson['mode' + str(modeno)] = modevalue
        #    modeno = modeno + 1
        Statusjson['allowedmodes'] = allowedmodes
        #Statusjson['modecount'] = str(modeno-1)

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

def makeinput(id,name,onclick, checked):
    madeinput = "<input type=\"checkbox\" id=\"" + id + "\" name=\"" + name + "\" onclick=\"" + onclick + "\""
    if (checked > 0):
        madeinput = madeinput + " checked >"
    else:
        madeinput = madeinput + ">"
    return madeinput

def makeselector(Selections,CurrentSelection):
    makeselector = ""
    #'<select id="' + "selector" + '" name="' + "sel" + '" onchange="ChangeMode(\'\')" >'
    for selno in Selections:
        #log.info("selection %s", selno)
        if (selno == CurrentSelection):
            makeselector += '<option selected '
        else:
            makeselector += '<option '
        makeselector += 'value="' + str(selno) +'">' + str(selno) + '</option>\n'
    #makeselector += '<option value="XX">XX</option>\n'
    #makeselector += '</select>'
    return makeselector

def SaveDefaults():
    global currenttreemode, requiredbrightness, maxbrightness
    Settingsjson = { 'state':treestate, 'mode': currenttreemode, 'brightness': requiredbrightness, "displaytime": displaytime, "allowedmodes" : allowedmodes, 'maxbrightness':maxbrightness }
    with open("settings.json", "w") as fi:
        json.dump(Settingsjson, fi)
    defaulttreemode = currenttreemode
    defaultrequiredbrightness = requiredbrightness
    defaulttreestate = treestate

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
defaulttreestate = 0
defaultrequiredbrightness = requiredbrightness
defaultdisplaytime = displaytime

# Need to start with some random colour
fixed_colour = random_color()

if (os.path.isfile("settings.json")):
    try:
        with open("settings.json", "r") as f:
            my_dict = json.load(f)
        currenttreemode = my_dict["mode"]
        requiredbrightness = my_dict["brightness"]
        displaytime = float(my_dict["displaytime"])
        defaulttreemode = currenttreemode
        defaultrequiredbrightness = requiredbrightness
        defaultdisplaytime = displaytime
        defaulttreestate = my_dict["state"]
        allowedmodes = my_dict["allowedmodes"]
        maxbrightness = my_dict["maxbrightness"]
        log.debug("Read defaults")
    except:
    	log.debug("settings.json file invalid or incomplete")

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
            #log.debug("Change %d", currenttreemode)
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
    notifier.notify("WATCHDOG=1")
    notifier.notify("STOPPING=1")

log.debug("Exiting")

# For 2.2 shutdown is done directly in the webpage so this doesnt get restarted.
