FROM python:3.6

CMD pip install -r requirements.txt && \
    python bin/develop.py migrate --noinput && \
    python bin/develop.py sync_translation_fields --noinput &&\
    python bin/develop.py createcachetable && \
    python bin/develop.py runserver 0.0.0.0:8000

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

RUN echo "APT::Install-Recommends \"0\";" >> /etc/apt/apt.conf.d/02recommends && \
    echo "APT::Install-Suggests \"0\";" >> /etc/apt/apt.conf.d/02recommends && \
    apt-get -qq update && \
    apt-get -qq install \
        build-essential \
        postgresql-client \
        sqlite3 \
        libxml2-dev \
        libxslt-dev \
        ffmpeg \
        git-core && \
    rm -rf /var/lib/apt/lists/* && \
    true

# The application requires a volume to write files to
RUN mkdir /writable
VOLUME /writaable

RUN ln -s /usr/bin/ffmpeg /usr/sbin/avconv

# Install requirements
WORKDIR /app
ADD requirements.txt /app
RUN pip --no-cache-dir install --src=/opt pyinotify -r requirements.txt

# This seems to be a requirement for AV encoding that is packaged
# as a git repo of Python scripts
RUN git clone https://github.com/vanlummelhuizen/CNGT-scripts CNGT_scripts

# Install application
ADD . /app
