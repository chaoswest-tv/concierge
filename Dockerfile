FROM python:3.8-alpine
WORKDIR /app

# set env
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install required packages
RUN  pip install -U supervisor \
  && mkdir -p /var/log/supervisor \
  && apk add --no-cache ffmpeg

# install dependencies
ADD ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# add user
RUN addgroup -S concierge && adduser -S concierge -G concierge

# add supervisord tasks directories
RUN mkdir -p /app/tasks.d /app/tasks.logs && chown concierge:concierge /app/tasks.d /app/tasks.logs

# add code
ADD . /app

# aaaaand go!
CMD ["/usr/local/bin/supervisord", "-c","/app/supervisord.conf"]
