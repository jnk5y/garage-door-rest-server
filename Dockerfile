FROM python:3-slim

COPY ./garage_door_rest_server.py /usr/src/app/

RUN chmod +x /usr/src/app/garage_door_rest_server.py && mkdir -p /usr/src/app/config && mkdir -p /usr/src/app/certs

RUN apt-get update && apt-get install -y \
      python3-pip curl && \
    pip3 install --upgrade pip && \
    pip3 install requests httplib2 pigpio parse lxml

EXPOSE 8888

CMD [ "python3", "/usr/src/app/garage_door_rest_server.py"]
