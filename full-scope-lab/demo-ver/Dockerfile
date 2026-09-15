FROM ollama/ollama:0.34.0 AS ollama-dist
# Keep the CPU runtime; omit the multi-GB GPU libraries.
RUN mkdir /cpu && cp -L /usr/lib/ollama/*.so* /usr/lib/ollama/llama-* /cpu/ && cp /usr/lib/ollama/*LICENSE* /cpu/

FROM python:3.13-slim AS common
RUN apt-get update && apt-get install -y --no-install-recommends iproute2 nmap inetutils-telnet netcat-openbsd procps ca-certificates libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -u 10001 -m -s /bin/sh student \
    && useradd -u 10002 -m -s /bin/sh bridgeapi
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["python", "supervisor.py"]

FROM common AS chat
RUN apt-get update && apt-get install -y --no-install-recommends net-tools \
    && rm -rf /var/lib/apt/lists/*
COPY --chmod=755 app/netstat /usr/local/bin/netstat
COPY app/ /app/

FROM common AS inference
COPY --from=ollama-dist /bin/ollama /usr/bin/ollama
COPY --from=ollama-dist /cpu/ /usr/lib/ollama/
ENV OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS=/opt/models OLLAMA_NO_CLOUD=1 OLLAMA_VULKAN=0

FROM inference AS model-download
ARG OLLAMA_MODEL=qwen2.5:0.5b
RUN ollama serve >/tmp/ollama-build.log 2>&1 & server_pid=$!; \
    for attempt in 1 2 3 4 5 6 7 8 9 10; do ollama list >/dev/null 2>&1 && break; sleep 1; done; \
    ollama pull "$OLLAMA_MODEL"; result=$?; kill "$server_pid"; exit "$result"

FROM inference AS api
COPY --from=model-download --chown=10002:10002 /opt/models/ /opt/models/
COPY app/ /app/
