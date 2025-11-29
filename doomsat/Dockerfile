FROM python:3.11-slim
WORKDIR /opt/doomsat
COPY . /opt/doomsat
RUN mkdir -p /opt/doomsat/memory/flags
RUN apt update && apt install net-tools procps netcat-openbsd -y
EXPOSE 7000
CMD ["python", "doomcore.py"]
