# Reproduce the cloned Hacker House Dockerfile's vulnerable source and both patches.
# Bullseye supplies OpenSSL 1.1 for this historical libssh; no current libssh substitute.
FROM python:3.13-slim AS certificates
FROM debian:bullseye-slim AS libssh-build
COPY --from=certificates /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
# Freeze the historical toolchain: live Bullseye indexes referenced removed packages.
# Snapshot signatures remain verified; only their historical expiry is ignored.
ARG DEBIAN_SNAPSHOT=20260824T000000Z
RUN printf 'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/%s bullseye main\ndeb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/%s bullseye-security main\n' "$DEBIAN_SNAPSHOT" "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list \
    && apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends build-essential cmake patch libssl-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
ADD cve-2018-10933/libssh-0.8.3.tar.xz /build/
COPY cve-2018-10933/cve-2018-10933.patch cve-2018-10933/server.patch /build/
RUN cd libssh-0.8.3 && patch -p0 < ../cve-2018-10933.patch && patch -p0 < ../server.patch \
    && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DWITH_GSSAPI=OFF -DWITH_EXAMPLES=ON -DWITH_SERVER=ON \
    && cmake --build build --target ssh_server_fork ssh-client -j2 \
    && mkdir -p /opt/libssh/bin /opt/libssh/lib \
    && cp build/examples/ssh_server_fork build/examples/ssh-client /opt/libssh/bin/ \
    && cp -L build/src/libssh.so* /opt/libssh/lib/ \
    && cp -L /usr/lib/*/libcrypto.so.1.1 /opt/libssh/lib/
COPY cve-2018-10933/LICENSE /opt/libssh/HACKERHOUSE-LICENSE
RUN cp /build/libssh-0.8.3/COPYING /opt/libssh/LIBSSH-COPYING

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
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client python3-paramiko util-linux \
    && rm -rf /var/lib/apt/lists/*
COPY --from=libssh-build /opt/libssh/ /opt/libssh/
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
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -u 10003 -m -s /bin/sh labapi \
    && useradd -u 10004 -m -s /bin/sh labssh
COPY --from=libssh-build /opt/libssh/ /opt/libssh/
COPY --from=model-download --chown=10003:10003 /opt/models/ /opt/models/
COPY app/ /app/
