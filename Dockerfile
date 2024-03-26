FROM ubuntu:22.04
LABEL MAINTAINER="Rita.Chen@advantech.com.tw"

ENV  LANG="C.UTF-8"

SHELL ["/bin/bash", "-c"]

RUN apt-get update \
    && apt-get install --no-install-recommends --no-install-suggests -y \
       python3 \
       python3-pip \
       git \
    && apt-get clean \
    && mkdir -p /home/auto-update-script-forum-docker


COPY . /home/auto-update-script-forum-docker
WORKDIR /home/auto-update-script-forum-docker
RUN pip3 install --upgrade pip \
    && pip3 install -r requirements.txt \
    && mkdir -p /home/auto-update-script-forum-docker/log \
    && mkdir -p /home/auto-update-script-forum-docker/log/forum \
    && mkdir -p /home/auto-update-script-forum-docker/log/index \
    && mkdir -p /home/auto-update-script-forum-docker/log/wiki \
    && sh /home/auto-update-script-forum-docker/script/start.sh

CMD ["sh", "/home/auto-update-script-forum-docker/script/auto_update.sh"]
