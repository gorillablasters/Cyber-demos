# Telnet, SSH, libssh and ports

## A port is an address for a service

An IP address identifies a network endpoint; a transport port identifies where an
application receives traffic at that endpoint. A TCP connection includes both
source and destination addresses and ports. A listening port means an application
is waiting there. It does not, by itself, reveal the application's identity or
whether it is secure.

Telnet conventionally uses TCP 23; SSH conventionally uses TCP 22. The lab uses
alternate ports to make its services convenient to run locally. Moving Telnet
to 2323 does not encrypt it, and using 2222 does not make SSH vulnerable.

| Service | Conventional port | This repository |
| --- | --- | --- |
| Telnet terminal | TCP 23 | Chat listens on TCP 2323 in both versions; demo API also listens on 2323 |
| SSH terminal | TCP 22 | Lab API's libssh server listens on TCP 2222 |
| Host access to chat Telnet | Deployment-specific | Demo 2323; lab 2324 with the provided environment settings |

Host port mappings and container listening ports are different layers. See the
[architecture port table](02-architecture.md) when deciding which to connect to.

## Telnet basics

Telnet carries a bidirectional terminal byte stream over TCP. It also negotiates
terminal options, rather than treating every byte as ordinary text. Its original
design uses a network virtual terminal to bridge differences between terminals.
[Telnet specification, RFC 854](https://www.rfc-editor.org/rfc/rfc854).

The lab implements a small Telnet-compatible console, not a complete production
Telnet daemon. It handles basic newline and option negotiation, then connects the
stream to `/bin/sh -i`. It has no full terminal emulator, PTY or job control.
A message such as “can't access tty; job control turned off” is therefore expected.
See [console.py](../lab-ver/app/console.py).

Plain Telnet in this lab provides no encryption or cryptographic integrity.
Someone able to observe the connection can read commands and output; an attacker
with an active position on the path may alter traffic. Traditional password-based
Telnet would also expose credentials without added protection. Here, the problem
is stronger: the teaching console does not ask for credentials at all.

For the assigned local lab, connect from the host:

```sh
# demo-ver, with its environment example
telnet 127.0.0.1 2323

# lab-ver, with TELNET_PORT=2324
telnet 127.0.0.1 2324
```

Run `id` to see the resulting identity, and `exit` to leave. These consoles run as
`student`; a successful connection is not root access. In the demo, a second
Telnet connection to `api 2323` is made from the chat shell. The lab replaces that
API endpoint with SSH.

## SSH and libssh are different things

**SSH** is a protocol family. Its architecture separates encrypted transport,
user authentication and channels such as terminal sessions. Server host keys help
the client authenticate the server; user credentials help the server authenticate
the client. Encryption alone does not replace either check.
[SSH architecture, RFC 4251](https://www.rfc-editor.org/rfc/rfc4251).

**libssh** is a software library for implementing SSH clients and servers.
**OpenSSH** is a separate implementation. “Uses SSH,” “uses libssh” and “contains a
particular vulnerable libssh version” are different claims requiring different
evidence.

The lab API uses the cloned teaching repository's `ssh_server_fork` example built
from libssh 0.8.3, with its supplied patches. Installing an OpenSSH client in the
container does not turn this server into OpenSSH. The actual server binary is
under `/opt/libssh/bin/`.

## Why this historical libssh endpoint is insecure

CVE-2018-10933 concerned authentication-state handling in affected libssh server
code. A client could send an authentication-success message where the server
expected an authentication request, causing the library to permit channels without
normal credential verification. The historical fixes were released as libssh
0.7.6 and 0.8.4; those are historical fix versions, not present-day deployment
recommendations. This does not mean every later libssh release is affected.
[Official libssh advisory](https://www.libssh.org/security/advisories/CVE-2018-10933.txt).

In this repository, `server.patch` also removes an extra example-application
authentication gate so the lesson can demonstrate shell access. Consequently,
this teaching target's behavior must not be generalized to every application that
embedded the affected library. The example retains known teaching credentials,
which are an additional reason not to treat it as a secure service.
See the [cloned teaching README](../lab-ver/cve-2018-10933/README.md),
[server patch](../lab-ver/cve-2018-10933/server.patch) and
[build integration](../lab-ver/Dockerfile).

The connection can still be encrypted while authentication is incorrect. The
failure is permission to enter a session, not a successful attack on the cipher.
The lab launches the service as `labssh`, so a successful teaching-client session
has UID 10004. The API/model identity remains `labapi`, UID 10003.

## What observations do and do not prove

| Observation | Reasonable conclusion | Not established |
| --- | --- | --- |
| TCP 2323 is open | Something accepts TCP connections there | It is necessarily Telnet |
| An SSH identification string is received | The endpoint speaks at least the opening SSH exchange | Authentication is correct or the banner is truthful |
| A terminal returns `id` | Commands executed under the reported account | Root or another process's privileges |
| Traffic is encrypted | Passive observers cannot simply read protected payloads | The server's authentication logic is sound |
| API 2323 is closed and 2222 is open | The intended transport change is observable from that scan location | The SSH implementation is secure |

## Defensive lesson and review

For a real remote-administration service, use a maintained SSH implementation,
verify server identity, configure authentication and restrict who can reach it.
The educational contrast is between plaintext/no-authentication access and an
encrypted protocol with a deliberately vulnerable implementation. Port numbers
alone do not provide those protections.

Review: Why does changing Telnet's port not protect the session? How can an
encrypted service grant unauthorized access? What evidence distinguishes a library
vulnerability from a weakness in the underlying protocol? What does `id` tell you
after entering the lab API shell?
