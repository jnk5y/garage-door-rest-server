""" Pi Garage Manager

Authors: John Kyrus adapted from Richard L. Lynch <rich@richlynch.com>

Description: Create a REST service that allows you to query and control the state of your garage door 
    and receive notifications based on the user supplied config.
    There is accompying cordova app to communicate with this garage door app. 
    See state of garage door and open and close it from the app. Receive
    notifications on your phone through the app.

"""
##############################################################################
import re
import sys
import signal
import os
import json
import logging
import traceback
import time
from time import strftime
from datetime import datetime
from datetime import timedelta

from queue import Queue
import subprocess
import threading
import requests

import pigpio

from http.server import HTTPServer, BaseHTTPRequestHandler
import base64
import ssl
import httplib2

from configparser import ConfigParser

LOCALPATH = '/usr/src/app/'

def send_notification(logger, name, state, time_in_state, alert_type, firebase_id):

    """
        Send a Firebase event using the FCM.
        Get the server key by following the URL at https://console.firebase.google.com/
    """
    AUTHKEY, FIREBASE_KEY = read_secrets()    

    if FIREBASE_KEY == '' or firebase_id == '':
        logger.error("No Firebase Key or ID")
    else:
        time = format_duration(int(time_in_state))
        body = "Your garage door has been " + state + " for " + time
        headers = { "Content-type": "application/json", "Authorization": FIREBASE_KEY}
        payload = ''

        if alert_type == 'alert':
            payload = { "notification": { "title": "Garage door alert", "body": body, "sound": "default" }, "data": { "event": state }, "to": firebase_id }
        else:
            payload = { "data": { "event": state }, "to": firebase_id }
    
        try:
            requests.post("https://fcm.googleapis.com/fcm/send", headers=headers, json=payload)
            logger.info("Sent firebase %s event: %s, %s, %s", alert_type, name, state, time)
        except:
            logger.error("Exception sending Firebase event: %s", sys.exc_info()[0])
    
    return

def format_duration(duration_sec):
    """Format a duration into a human friendly string"""
    days, remainder = divmod(duration_sec, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    ret = ''
    if days > 1:
        ret += "%d days " % (days)
    elif days == 1:
        ret += "%d day " % (days)

    if hours > 1:
        ret += "%d hours " % (hours)
    elif hours == 1:
        ret += "%d hour " % (hours)

    if minutes > 1:
        ret += "%d minutes" % (minutes)
    if minutes == 1:
        ret += "%d minute" % (minutes)

    if ret == '':
        ret += "%d seconds" % (seconds)

    return ret

def write_config(home_away,alert_open_notify,alert_open_minutes,alert_open_start,alert_open_end,forgot_open_notify,forgot_open_minutes):
    
    try:
        config = ConfigParser()
        config.read(LOCALPATH + 'config/config.ini')
        config.set('main', 'home_away', home_away)
        config.set('main', 'alert_open_notify', str(alert_open_notify))
        config.set('main', 'alert_open_minutes', str(alert_open_minutes))
        config.set('main', 'alert_open_start_time', str(alert_open_start))
        config.set('main', 'alert_open_end_time', str(alert_open_end))
        config.set('main', 'forgot_open_notify', str(forgot_open_notify))
        config.set('main', 'forgot_open_minutes', str(forgot_open_minutes))

        with open(LOCALPATH + 'config/config.ini', 'w') as f:
            config.write(f)
    except:
        logger.error("Exception writing config: %s", sys.exc_info()[0])
        sys.exit(0)
            
    return


def read_config():
    try:
        # Read config file
        logger.info("Reading configuration file")

        config = ConfigParser()
        config.read(LOCALPATH + 'config/config.ini')

        name = config.get('main', 'name')
        home_away = config.get('main', 'home_away')
        network_ip = config.get('main', 'network_ip')
        alert_open_notify = config.getboolean('main', 'alert_open_notify')
        alert_open_minutes = config.getint('main', 'alert_open_minutes')
        alert_open_start = config.getint('main', 'alert_open_start_time')
        alert_open_end = config.getint('main', 'alert_open_end_time')
        forgot_open_notify = config.getboolean('main', 'forgot_open_notify')
        forgot_open_minutes = config.getint('main', 'forgot_open_minutes')
    except:
        logger.error("Exception reading configuration file: %s", sys.exc_info()[0])
        #set to defaults
        name = 'garage door'
        home_away = 'home'
        network_ip = '192.168.86.9'
        alert_open_notify = False
        alert_open_minutes = 1
        alert_open_start = 23
        alert_open_end = 7
        forgot_open_notify = False
        forgot_open_minutes = 15

    return name,home_away,network_ip,alert_open_notify,alert_open_minutes,alert_open_start,alert_open_end,forgot_open_notify,forgot_open_minutes

def read_secrets():
    try:
        f = open('/run/secrets/AUTHKEY', "r")
        AUTHKEY = f.readline().strip()
        f.close()

        f = open('/run/secrets/FIREBASE_KEY', "r")
        FIREBASE_KEY = "key=" + f.readline().strip()
        f.close()
    except:
       logger.error("Exception reading secrets files: %s", sys.exc_info()[0])
       sys.exit(0)

    return AUTHKEY, FIREBASE_KEY

def read_firebaseID():
    try:
        f = open(LOCALPATH + 'config/FIREBASE_ID.txt', "r")
        FIREBASE_ID = f.readline().strip()
        f.close()
    except:
        logger.error("Exception reading firebase id from file: %s", sys.exc_info()[0])
        FIREBASE_ID = ''

    return FIREBASE_ID

def write_firebaseID(FIREBASE_ID):
    try:
        f = open(LOCALPATH + 'config/FIREBASE_ID.txt',"w")
        f.write(FIREBASE_ID)
        f.close()
    except:
        logger.error("Exception writing firebase id to file: %s", sys.exc_info()[0])

    return

def write_tz():
    try:
        f = open('/etc/timezone',"w")
        f.write(os.getenv('TZ', 'US/Eastern'))
        f.close()
    except:
        logger.error("Exception writing timezone to file: %s", sys.exc_info()[0])

    return

##############################################################################
# Listener thread for getting/setting state and openning/closing the garage
##############################################################################
def garage_listener():

    name,home_away,network_ip,alert_open_notify,alert_open_minutes,alert_open_start,alert_open_end,forgot_open_notify,forgot_open_minutes = read_config()

    try:
        # Initialize pigpio
        logger.info("Initializing garage door")
        logger.info("Configuring pin GPIO 4, GPIO 7, GPIO 23 for %s at IP %s", name, network_ip)
        pi = pigpio.pi(network_ip)
        # Configure the sensor pin as input
        pi.set_mode(4, pigpio.INPUT)
        pi.set_pull_up_down(23, pigpio.PUD_UP)
        # Configure the control pin for the relay to open and close the garage door
        pi.set_mode(7, pigpio.OUTPUT)
    except:
        logger.error("Exception connecting to garage pi: %s", sys.exc_info()[0])
        sys.exit(0)

    # Read initial states
    initial_state =  ''
    try:
        if pi.read(4):
            initial_state = 'open'
        else:
            initial_state = 'closed'
    except:
        logger.error("Exception reading garage state: %s", sys.exc_info()[0])

    current_state = initial_state
    time_of_last_state_change = time.time()
    alert_state = False
    firebase_id = read_firebaseID()

    logger.info("Initial state of \"%s\" is %s and set to %s", name, initial_state, home_away)

    while True:
        try:
            if pi.read(4):
                current_state = 'open'
            else:
                current_state = 'closed'
        except:
            logger.error("Exception reading garage state: %s", sys.exc_info()[0])

        time_in_state = time.time() - time_of_last_state_change
        send_alert = False

        # Check if the door has changed state and reset variables
        if initial_state != current_state:
            # Send app data notification - not an alert
            send_notification(logger, name, current_state, time_in_state, 'data', firebase_id)
            
            initial_state = current_state
            time_of_last_state_change = time.time()
            time_in_state = 0
            alert_state = False

        # See if there are any alerts
        if (alert_open_notify or forgot_open_notify) and current_state == 'open' and not alert_state:
            # Get start and end times and only alert if current time is in between
            time_of_day = int(datetime.now().strftime("%H"))

            if alert_open_notify:
                # Is start and end hours in the same day?
                if alert_open_start < alert_open_end:
                    # Is the current time within the start and end times and has the time elapsed?
                    if time_of_day >= alert_open_start and time_of_day <= alert_open_end and time_in_state > (alert_open_minutes*60):
                        send_alert = True
                else:
                    if (time_of_day >= alert_open_start or time_of_day <= alert_open_end) and time_in_state > (alert_open_minutes*60):
                        send_alert = True

            if forgot_open_notify and time_in_state > (forgot_open_minutes*60):
                send_alert = True

            if send_alert:
                send_notification(logger, name, current_state, time_in_state, 'alert', firebase_id)
                alert_state = True

        # If system is set to away and the door is a open send an alert
        if home_away == 'away' and current_state == 'open' and not alert_state:
            send_notification(logger, name, current_state, '0', 'alert', firebase_id)
            alert_state = True

        # Deal with received messages
        if not listeningQueue.empty():
            received_og = listeningQueue.get()
            received = received_og.lower()
            response = 'unknown command'
            trigger = False

            if received == 'trigger':
                trigger = True
                if current_state == 'open':
                    response = 'closing'
                else:
                    response = 'opening'
            elif received == 'open' or received == 'up':
                if current_state == 'open':
                    response = 'already open'
                else:
                    response = 'opening'
                    trigger = True
            elif received == 'close' or received == 'down' or received == 'clothes':
                if current_state == 'open':
                    response = 'closing'
                    trigger = True
                else:
                    response = 'already closed'
            elif received == 'get_state' or received == 'get_status' or received == 'get_settings':
                response = "%s,%s,%s,%s,%s,%s,%s,%s" % (current_state,home_away,alert_open_notify,alert_open_minutes,alert_open_start,alert_open_end,forgot_open_notify,forgot_open_minutes)
            elif 'set_settings' in received:
                settings = received.replace('set_settings','')
                settings = settings.replace('%20','')
                settings = settings.split(',')
                home_away = settings[0]
                alert_open_notify = settings[1]
                alert_open_minutes = int(settings[2])
                alert_open_start = int(settings[3])
                alert_open_end = int(settings[4])
                forgot_open_notify = settings[5]
                forgot_open_minutes = int(settings[6])
                write_config(home_away,alert_open_notify,alert_open_minutes,alert_open_start,alert_open_end,forgot_open_notify,forgot_open_minutes)
                response = "Settings saved"
            elif received.startswith('firebase:'):
                firebase_id = received_og.replace('firebase:','')
                write_firebaseID(firebase_id)
                response = 'Firebase ID saved'

            if trigger:
                try:
                    pi.write(7,0)
                    time.sleep(2)
                    pi.write(7,1)
                except:
                    logger.error("Exception triggering garage: %s", sys.exc_info()[0])
            
            logger.info('Received: %s. Responded: %s', received_og, response )
            listeningQueue.task_done()
            responseQueue.put(response)
            responseQueue.join()

        time.sleep(1)


##############################################################################
# Main functionality
##############################################################################
# Set up logging
logger = logging.getLogger('garage-rest-server')
log_fmt = '%(asctime)-15s %(levelname)-8s %(message)s'
log_level = logging.INFO
LOG_FILENAME = "/var/log/garage-rest-server.log"
logging.basicConfig(format=log_fmt, level=log_level)
#logging.basicConfig(format=log_fmt, level=log_level, filename=LOG_FILENAME)

# Queues for comminicating between threads
listeningQueue = Queue()
responseQueue = Queue()

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    ''' Main class for authentication. '''
    def do_GET(self):
        path = self.path.split('?_=',1)[0]
        path = path.split('/')
        trigger = path[1].lower()
        action = path[2]
        response = ''
        
        if trigger == 'garage' and action == 'health':
#            self.send_response(200)
#            self.send_header('Content-Type', 'text/plain');
#            self.end_headers()
#            response = 'healthy'
#            self.wfile.write(response.encode())
            pass
        else:
            AUTHKEY, FIREBASE_KEY = read_secrets()

            if AUTHKEY == '':
                logger.error('Empty Authentication')
                sys.exit(0)
            else:
                if self.headers.get('Authorization') == ('Basic '+ AUTHKEY):
                    if trigger == 'garage':
                        listeningQueue.put(action)
                        listeningQueue.join()
                        response = responseQueue.get()
                        responseQueue.task_done()

                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain');
                    self.end_headers()
                    self.wfile.write(response.encode())
                else:
                    logger.error("Not Authorized")

try:
    CERTFILE_PATH = LOCALPATH + "certs/live/server.kyrus.xyz/fullchain.pem"
    KEYFILE_PATH = LOCALPATH + "certs/live/server.kyrus.xyz/privkey.pem"

    httpd = HTTPServer(('', 8888), SimpleHTTPRequestHandler)
    httpd.socket = ssl.wrap_socket (httpd.socket, keyfile=KEYFILE_PATH, certfile=CERTFILE_PATH, server_side=True)
    sa = httpd.socket.getsockname()

    write_tz()
    logger.info("Python REST Server")
    logger.info("Serving HTTPS on port %d", sa[1])

    ##############################################################################
    # Start garage door thread
    ##############################################################################
    logger.info("Listening for garage commands")
    messageListenerThread = threading.Thread(target=garage_listener)
    messageListenerThread.setDaemon(True)
    messageListenerThread.start()

    httpd.serve_forever()

except:
    logging.critical("Terminating process")

finally:
    logger.error("Exiting Python REST Server")
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
    sys.exit(0)
