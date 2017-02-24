FROM library/alpine:3.4

EXPOSE 4042

RUN apk add --no-cache 'git>2.6.6-r0'
RUN apk add --no-cache bash gcc linux-headers
RUN apk add --no-cache python3
RUN apk add --no-cache openssl-dev libffi-dev python3-dev
RUN apk add --no-cache sqlite

ADD . /app
WORKDIR /app
RUN apk add --no-cache  musl-dev
RUN pip3 install -r requirements.txt
