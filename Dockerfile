FROM python:3-alpine
  
RUN mkdir -p /opt/bot

ENV VIRTUAL_ENV=/opt/bot/env
RUN pip install --upgrade pip && \
    apk add libxml2-dev libxslt-dev && \
    python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin/:$PATH"

COPY ./ /opt/bot
WORKDIR /opt/bot

RUN apk add --virtual .build build-base && \
    pip install -r requirements.txt && \
    apk del .build

STOPSIGNAL SIGINT

CMD ["python3", "main.py"]
