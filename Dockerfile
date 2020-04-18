FROM python:3-slim

COPY ./garage-door-rest-server.py /usr/src/app/

RUN chmod +x /usr/src/app/garage-door-rest-server.py && mkdir -p /usr/src/app/config && mkdir -p /usr/src/app/certs

RUN apt-get update && apt-get install -y \
    python3-pip curl && \
    pip install --no-cache-dir requests httplib2 pigpio parse lxml

EXPOSE 8888

CMD [ "python3", "/usr/src/app/garage-door-rest-server.py"]
