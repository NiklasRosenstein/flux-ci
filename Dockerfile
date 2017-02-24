# Dockerfile for Flux

FROM library/alpine:3.4

EXPOSE 4042

RUN apk update && apk upgrade && \
    apk add --no-cache 'git>2.6.6-r0' && \
    apk add --no-cache bash gcc linux-headers musl-dev && \
    apk add --no-cache openssl-dev libffi-dev python3-dev && \
    apk add --no-cache python3 && \
    apk add --no-cache sqlite

COPY requirements.txt /opt/requirements.txt
RUN pip3 install -r /opt/requirements.txt

COPY . /app
WORKDIR /app

CMD ["python3", "flux_run.py"]