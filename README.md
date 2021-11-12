# grage-door-rest-server

A REST server that connects to a raspberry pi and allows you to query and update pins. This is used to detect if a garage door is opened or closed and to open and close it. Theoretically could be used to detect if anything is opened or closed.

## BASIC RASPBERRY PI ZERO W SETUP
Equipment required
* Any Raspberry Pi will work but I used a zero w model
* 2GB or larger SD card
* Magnetic sensor (https://www.amazon.com/uxcell-Stainless-Security-Magnetic-Contact/dp/B005DJLILI/ref=sr_1_10)
* 2 channel relay (https://www.amazon.com/SunFounder-Channel-Optocoupler-Expansion-Raspberry/dp/B00E0NTPP4/ref=sr_1_1)
* Female to female jumper cables (https://www.amazon.com/40pcs-Female-2-54mm-Jumper-2x40pcs/dp/B00GSE2S98/ref=sr_1_4)

## RASPBERRY PI SETUP
* Setup your Pi and give it a static IP.
* Enable Remote GPIO on the Pi in the Raspberry Pi Configuration Tool.
* Install and run pigpoi which allows remote controlling of GPIO on the pi.
 `sudo apt-get update; sudo apt-get install pigpio python-pigpio python3-pigpio; sudo pigpiod`

## PI WIRING DIAGRAMS  
Check out the wiki for the wiring diagrams - https://github.com/jnk5y/garage-door-rest-server/wiki

## REST SERVER SETUP  
You must create 2 docker secrets, AUTHKEY and FIREBASE_KEY, before running. AUTHKEY is your username:password base64 encrypted. FIREBASE_KEY is your app's firebase key at firebase.google.com.
 * `printf "place-your-AUTHKEY-here" | docker secret create AUTHKEY -`
 * `printf "place-your-FIREBASE_KEY-here" | docker secret create FIREBASE_KEY -`

## Build  
`podman build -t garage-door-rest-server -f ./Dockerfile`

## Config  
Update the config.ini file with your raspberry pi IP address
 
## Deploy
`podman run -d -e CERTPATH='live/<SERVER NAME>' -e TZ='US/Eastern' --secret AUTHKEY --secret FIREBASE_KEY -p 8888:8888 -v <CONFIG FOLDER>:/usr/src/app/config/:z -v <LETSENCRYPT FOLDER>:/usr/src/app/certs/:z --healthcheck-command 'curl --fail -k -s https://localhost:8888/garage/health || exit 1' --label "io.containers.autoupdate=image" --name garage-door garage-door-rest-server`
 
## Systemd Connection
This will allow your server to restart the running pods on a server restart or if they are stopped.  
`podman generate systemd --new --name garage-door | sudo tee ~/.config/systemd/user/container-garage-door.service >/dev/null`  
Now you can use systemctl --user calls to enable, start, stop or view the status of your pod  
`systemctl --user enable container-garage-door.service`  
`systemctl --user start container-garage-door.service`

## REST Call
When running you can make calls to the rest server  
`https://<SERVER NAME>:8888/garage/<COMMAND>`
 
### Commands  
 * trigger - triggers the garage to open or close depending on current state
 * open - opens the garage door if it is closed
 * close or clothes (a fun google assistant issue) - closes the garage door if it is open
 * get_state, get_status, or get_settings - returns a comma seperated list of state and settings
 * set_settings home_away,alert_open_notify,alert_open_minutes,alert_open_start,alert_open_end,forgot_open_notify,forgot_open_minutes - sets those alert settings
 * firebase:your-firebase-id - sets the firebase id of your device (phone, tablet) so you will receive notifications if an alert is triggered.
 
### Examples
 * You can use postman to test but you must have a header with KEY: "Authorization" and VALUE: "Basic Base64-encoded-username:password". Your request would be GET https://<SERVER NAME>:8888/garage/command 
 * IFTTT webhook url would be https://username:password@<SERVER NAME>:8888/garage/{{TextField}}. I have it connected to Google Assistant - Say a phrase with a text ingredient and for What do you want to say? I have `Garage $`
 
Thanks to:
* Shane Rowley - https://github.com/smrowley
