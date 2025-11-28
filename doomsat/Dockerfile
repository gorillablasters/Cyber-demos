
FROM python:3.11-slim

WORKDIR /opt/doomsat
COPY . /opt/doomsat

RUN mkdir -p /opt/doomsat/memory/flags

EXPOSE 7000

CMD ["python", "doomcore.py"]
