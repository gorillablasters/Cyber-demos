// groundstation/parser/telemetry_parser.c
//
// Vulnerable DOOM-FRAME telemetry parser for Stage 6.
// Listens on TCP port 5000. Expects a single line of hex-encoded frame.
//
// Frame format:
//   HEADER (2 bytes)   : 0xD0 0x0D
//   LEN    (1 byte)    : length of TYPE + PAYLOAD
//   TYPE   (1 byte)
//   PAYLOAD (LEN-1 bytes)
//   CRC    (1 byte)    : XOR of TYPE+PAYLOAD
//
// For TYPE 0xFE, we copy payload into a 32-byte buffer with strcpy(),
// and then print a nearby "status" string. Overflow can smash that status
// and force it to print attacker-controlled bytes, revealing the final flag.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

#define PORT 5000
#define HEADER0 0xD0
#define HEADER1 0x0D

static const char FINAL_FLAG[] = "DOOM{doomsday_sequence_complete}";

unsigned char crc8_xor(const unsigned char *data, size_t len) {
    unsigned char c = 0;
    for (size_t i = 0; i < len; i++) {
        c ^= data[i];
    }
    return c & 0xFF;
}

int hex_value(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return 10 + (c - 'a');
    if (c >= 'A' && c <= 'F') return 10 + (c - 'A');
    return -1;
}

// Convert ASCII hex string into bytes. Returns length or -1 on error.
ssize_t hex_to_bytes(const char *hex, unsigned char *out, size_t max_out) {
    size_t len = strlen(hex);
    if (len % 2 != 0) return -1;
    size_t out_len = len / 2;
    if (out_len > max_out) return -1;

    for (size_t i = 0; i < out_len; i++) {
        int hi = hex_value(hex[2*i]);
        int lo = hex_value(hex[2*i + 1]);
        if (hi < 0 || lo < 0) return -1;
        out[i] = (unsigned char)((hi << 4) | lo);
    }
    return (ssize_t)out_len;
}

void handle_frame(const unsigned char *frame, size_t len) {
    if (len < 5) {
        printf("[PARSER] Frame too short.\n");
        return;
    }
    if (frame[0] != HEADER0 || frame[1] != HEADER1) {
        printf("[PARSER] Bad DOOM header.\n");
        return;
    }

    unsigned char flen = frame[2];
    if (flen + 4 > len) {
        printf("[PARSER] Declared length does not match.\n");
        return;
    }

    unsigned char type = frame[3];
    const unsigned char *payload = &frame[4];
    size_t payload_len = (size_t)(flen - 1);
    unsigned char crc = frame[4 + payload_len];

    // Verify CRC
    unsigned char calc = crc8_xor(&frame[3], (size_t)flen);
    if (calc != crc) {
        printf("[PARSER] CRC mismatch (got 0x%02X, expected 0x%02X).\n", crc, calc);
        return;
    }

    printf("[PARSER] Valid frame: TYPE=0x%02X, PAYLOAD_LEN=%zu\n", type, payload_len);

    if (type == 0xFE) {
        // ---- VULNERABLE PATH ----
        // Intentionally dangerous: we treat PAYLOAD as a C string
        // and copy into a 32-byte buffer with strcpy(), then print
        // a nearby status string. Overflow of buf can smash status.
        char buf[32];
        char status[64] = "OK: Telemetry nominal";

        printf("[PARSER] Processing DANGER frame...\n");

        // VULNERABILITY: no bounds check
        strcpy(buf, (const char *)payload);

        printf("STATUS: %s\n", status);
        printf("[PARSER] (Hidden villain flag is at %p)\n", (void *)FINAL_FLAG);
    } else {
        printf("[PARSER] Non-danger frame processed.\n");
    }
}

int main(void) {
    int server_fd, client_fd;
    struct sockaddr_in addr;
    socklen_t addrlen = sizeof(addr);

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        return 1;
    }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(PORT);
    addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(server_fd);
        return 1;
    }

    if (listen(server_fd, 1) < 0) {
        perror("listen");
        close(server_fd);
        return 1;
    }

    printf("[PARSER] Listening on port %d...\n", PORT);

    while (1) {
        client_fd = accept(server_fd, (struct sockaddr *)&addr, &addrlen);
        if (client_fd < 0) {
            perror("accept");
            continue;
        }

        printf("[PARSER] Client connected.\n");

        char line[2048];
        ssize_t n = read(client_fd, line, sizeof(line) - 1);
        if (n <= 0) {
            printf("[PARSER] No data.\n");
            close(client_fd);
            continue;
        }
        line[n] = '\0';

        // Strip CRLF
        for (ssize_t i = 0; i < n; i++) {
            if (line[i] == '\r' || line[i] == '\n') {
                line[i] = '\0';
                break;
            }
        }

        unsigned char frame[512];
        ssize_t flen = hex_to_bytes(line, frame, sizeof(frame));
        if (flen < 0) {
            printf("[PARSER] Invalid hex input.\n");
            close(client_fd);
            continue;
        }

        handle_frame(frame, (size_t)flen);

        close(client_fd);
        printf("[PARSER] Client disconnected.\n");
    }

    close(server_fd);
    return 0;
}
