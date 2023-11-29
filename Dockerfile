FROM ubuntu:22.04
MAINTAINER Rita "Rita.Chen@advantech.com.tw"

ENV  LANG="C.UTF-8"

SHELL ["/bin/bash", "-c"]

RUN apt-get update \
    && apt-get install --no-install-recommends --no-install-suggests -y \
       python3 \
       python3-pip \
       git \
    && apt-get clean \
    && mkdir -p /home/auto-update-script-forum


COPY . /home/auto-update-script-forum
WORKDIR /home/auto-update-script-forum
RUN pip3 install --upgrade pip \
    && pip3 install -r requirements.txt \
    && sh /home/auto-update-script-forum/script/start.sh

CMD ["sh", "/home/auto-update-script-forum/script/auto_update.sh"]
