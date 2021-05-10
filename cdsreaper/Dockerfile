FROM python:3.8-alpine

COPY requirements.txt /opt/cdsreaper/requirements.txt
RUN pip install -r /opt/cdsreaper/requirements.txt && rm -rf /root/.cache
COPY *.py /opt/cdsreaper/
USER nobody

CMD /usr/local/bin/python /opt/cdsreaper/cdsreaper.py