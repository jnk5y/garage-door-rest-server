[![Build Status](https://travis-ci.com/jnk5y/garage-door-rest-server.svg?branch=master)](https://travis-ci.com/jnk5y/garage-door-rest-server)
[![Docker Stars](https://img.shields.io/docker/stars/jnk5y/garage-door-rest-server.svg)](https://hub.docker.com/r/jnk5y/shepherd/) 
[![Docker Pulls](https://img.shields.io/docker/pulls/jnk5y/garage-door-rest-server.svg)](https://hub.docker.com/r/jnk5y/garage-door-rest-server/)

grage-door-rest-server
===============

A REST server that connects to a raspberry pi and allows you to query and update pins. This is used to detect if a garage door is opened or closed and to open and close it. Theoretically could be used to detect if anything is opened or closed.

BASIC RASPBERRY PI SETUP
Equipment required
* Raspberry Pi - I have used an A and zerow model
* 2GB or larger SD card
* Magnetic sensor (e.g. https://www.amazon.com/uxcell-Stainless-Security-Magnetic-Contact/dp/B005DJLILI/ref=sr_1_10)*
* USB wifi adapter if not built in
* 2 channel relay (https://www.amazon.com/SunFounder-Channel-Optocoupler-Expansion-Raspberry/dp/B00E0NTPP4/ref=sr_1_1)
* Female to female jumper cables (https://www.amazon.com/40pcs-Female-2-54mm-Jumper-2x40pcs/dp/B00GSE2S98/ref=sr_1_4)

RASPBERRY PI SETUP
* Setup your Pi and give it a static IP.
* Enable Remote GPIO on the Pi in the Raspberry Pi Configuration Tool.

PI WIRING DIAGRAMS
* Check out the wiki for the wiring diagrams - https://github.com/jnk5y/garage-door-rest-server/wiki

REST SERVER SETUP
You must create 2 docker secrets (username, password, firebase_key), before running.
 * `printf "place-your-username-here" | docker secret create username -`
 * `printf "place-your-password-here" | docker secret create password -`
 * `printf "place-your-firebase-key-here" | docker secret create firebase_key -`
 
To build the container image from the main folder
 * `docker build . -t garage-door-rest-server`
 
Update the config.ini file with your raspberry pi IP address
 
To deploy to docker swarm from the main folder
 * `docker stack deploy --compose-file docker-compose.yaml garage-door-rest-service`
 
When running you can make calls to the rest server
 * `https://your-server-name:8888/garage/command`
 
Command List
 * trigger - triggers the garage to open or close depending on current state
 * open - opens the garage door if it is closed
 * close or clothes (a fun google assistant issue) - closes the garage door if it is open
 * get_state, get_status, or get_settings - returns a comma seperated list of state and settings
 * set_settings home_away,alert_open_notify,alert_open_minutes,alert_open_start,alert_open_end,forgot_open_notify,forgot_open_minutes - sets those alert settings
 * firebase:your-firebase-id - sets the firebase id of your device (phone, tablet) so you will receive notifications if an alert is triggered.
 
Examples
 * You can use postman to test but you must have a header with KEY: "Authorization" and VALUE: "Basic Base64-encoded-username:password". Your request would be GET https://your-server-ip-or-name:8888/garage/command 
 * IFTTT webhook url would be https://username:password@your-server-ip-or-name:8888/garage/{{TextField}}. I have it connected to Google Assistant - Say a phrase with a text ingredient and for What do you want to say? I have "Garage $"
 
Thanks to:
* Shane Rowley - https://github.com/smrowley
