FROM ubuntu:18.04

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /code/

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y python2.7 python-pip wget lsb-release

RUN wget http://download.ag-projects.com/agp-debian-gpg.key && \
    apt-key add agp-debian-gpg.key && \
    echo "deb       http://ag-projects.com/ubuntu `lsb_release -c -s` main" >> /etc/apt/sources.list && \
    echo "deb-src   http://ag-projects.com/ubuntu `lsb_release -c -s` main" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y python-sipsimple && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove wget python-pip

RUN useradd user && \
    chown -R user /code
USER user

COPY . .

VOLUME [ "/code/audio" ]

CMD [ "python", "-m", "media_server" ]
