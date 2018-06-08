# Dockerfile for Flux-CI.

FROM library/alpine:3.4

EXPOSE 4042

RUN apk update && apk upgrade && \
    apk add --no-cache 'git>2.6.6-r0' && \
    apk add --no-cache bash gcc linux-headers musl-dev && \
    apk add --no-cache openssl-dev libffi-dev python3-dev && \
    apk add --no-cache python3 && \
    apk add --no-cache sqlite

# Install Python dependencies.
COPY requirements.txt /opt/requirements.txt
RUN pip3 install -r /opt/requirements.txt
RUN rm /opt/requirements.txt

# Install Flux-CI.
COPY . /opt/flux
RUN pip3 install /opt/flux
RUN rm -r /opt/flux

# Copy Flux-CI configuration.
RUN mkdir -p /opt/flux
COPY flux_config.py /opt/flux

ENV PYTHONPATH=/opt/flux
CMD flux-ci --web
