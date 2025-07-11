FROM debian:bookworm

RUN apt-get update

RUN apt-get install -y tzdata
ENV TZ=Asia/Tokyo
RUN ln -sf /usr/share/zoneinfo/Japan /etc/localtime && \
    echo $TZ > /etc/timezone

RUN apt-get install -y python3

RUN apt-get install -y \
    python3-pip sqlite3 python3-venv procps locales
RUN echo "ja_JP.UTF-8 UTF-8" >> /etc/locale.gen && locale-gen

ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:en
ENV LC_ALL ja_JP.UTF-8

WORKDIR /app

COPY .vimrc /root/
COPY requirements.txt ./

RUN python3 -m venv /app/venv && . /app/venv/bin/activate && pip install -Ur requirements.txt

ENV PATH /app/venv/bin:$PATH

COPY . .

WORKDIR /app/ex_scraping
