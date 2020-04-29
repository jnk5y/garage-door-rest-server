FROM alpine:3

RUN apk add --no-cache py3-pip tzdata && \
	pip3 install --no-cache-dir requests httplib2 pigpio parse

COPY ./garage-door-rest-server.py /usr/src/app/

RUN chmod +x /usr/src/app/garage-door-rest-server.py && mkdir -p /usr/src/app/config && mkdir -p /usr/src/app/certs

EXPOSE 8888

CMD [ "python3", "/usr/src/app/garage-door-rest-server.py"]
