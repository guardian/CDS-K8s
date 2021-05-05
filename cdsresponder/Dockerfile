FROM python:3.8-alpine

COPY requirements.txt /opt/cdsresponder/requirements.txt
RUN apk add --no-cache alpine-sdk libxml2 libxml2-dev libxslt libxslt-dev && pip install -r /opt/cdsresponder/requirements.txt && apk del alpine-sdk libxml2-dev libxslt-dev && rm -rf /root/.cache
COPY cdsresponder.py /opt/cdsresponder/cdsresponder.py
ADD cds /opt/cdsresponder/cds
ADD rabbitmq /opt/cdsresponder/rabbitmq
ADD templates /opt/cdsresponder/templates

CMD /opt/cdsresponder/cdsresponder.py