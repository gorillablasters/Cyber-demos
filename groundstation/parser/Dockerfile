FROM gcc:13

WORKDIR /app

COPY telemetry_parser.c .

RUN gcc -O0 -g -fno-stack-protector -no-pie -o telemetry_parser telemetry_parser.c

EXPOSE 5000

CMD ["./telemetry_parser"]
