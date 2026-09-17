# Educational threat model: demo-ver and lab-ver

## Purpose and scope

A threat model asks: what matters, who can interact with it, where trust changes,
and what can go wrong? Here it also distinguishes **deliberate teaching weaknesses**
from the controls intended to contain them.

The exercise covers Markdown-based prompt injection, service discovery, remote
shell access, network segmentation and scan attribution. Process injection is a
future lesson. Obtaining a shell in this lesson does not demonstrate injection
into another process, root access or a container escape.

The assumed student begins with browser and Telnet access to the assigned lab.
The instructor controls Docker, environment variables, images and logs. A student
with Docker administration rights can bypass the intended discovery path; that
is outside the student-access model.

## Assets and actors

| Asset | Why it matters |
| --- | --- |
| Instructor host and other workloads | Must remain outside the exercise targets |
| API and model processes | Provide the chatbot and represent the private service |
| Deployment inventory | Teaching data for the disclosure exercise; not a suitable place for real secrets |
| Service token | Authenticates gateway requests to the API's POST endpoints |
| Session notes and conversation history | Should remain associated with the intended browser session |
| IDS events and firewall state | Let students distinguish observation from enforcement |
| Classroom availability | Scans, model work and temporary bans can interrupt the exercise |

The student can submit messages and Markdown, connect to exposed services, and
run commands with the resulting shell's permissions. Apparent packet sources may
include lab decoy addresses. An apparent source IP is evidence about a packet,
not a verified identity of a person.

## Trust boundaries shared by both versions

1. **Browser to gateway:** HTTP input is student-controlled. The gateway assigns a
   session cookie and forwards requests to the private API.
2. **Gateway to API:** API POST requests require `X-Service-Token`. Network access
   and authorization are separate: being able to reach port 8000 is not sufficient
   to make an authorized POST request. `/health` is a separate unauthenticated GET.
3. **Uploaded data to model instructions:** Markdown is untrusted reference text.
   The parser checks prose but skips fenced blocks; the model still receives the
   full accepted document. That gap is the injection lesson.
4. **Remote connection to operating-system commands:** The terminal endpoints
   deliberately grant more capability than the chatbot interface.
5. **Container to host:** Container boundaries and limited mounts support
   containment. They are not proof against arbitrary hostile code or host-admin
   access.

The upload path validates `.md` names, text content and size. It retains up to
three notes per session. Accepted text is added as a user-role reference message;
it is not promoted to a system message or executed as Python or shell code.
See the [demo engine](../demo-ver/app/engine.py),
[lab engine](../lab-ver/app/engine.py) and [HTTP service](../lab-ver/app/server.py).

## Demo threat model

The current demo model policy openly shares deployment ports. Its simpler path is:
ask for the ports → connect to chat Telnet → discover the private API → connect
to API Telnet. Fenced Markdown remains available to illustrate the parser's blind
spot, but direct disclosure is expected behavior under this demo policy.

| Threat or teaching condition | Consequence | Existing boundary and limitation |
| --- | --- | --- |
| Instructions hidden inside a Markdown fence | Uninspected text reaches model context | Input validation limits format, not the meaning of model instructions |
| Unauthenticated chat Telnet | Student obtains a `student` shell | Non-root shell; still capable of running commands and contacting the private API |
| Unauthenticated API Telnet | Student obtains another `student` shell after discovering the target | API/model processes run separately as `bridgeapi`; this is not root access |
| Compromised gateway | Private service becomes reachable from the foothold | Internal networking reduces direct exposure but trusts a reachable gateway |
| Same-user access on chat | Shell and gateway share UID 10001 | A scrubbed shell environment does not prove that all gateway secrets are inaccessible |
| Excessive requests or commands | Slow or unavailable lesson | Bounded inputs and sessions help; no comprehensive resource-isolation guarantee |

Both Telnet consoles are plaintext, unauthenticated classroom implementations.
The API HTTP process runs as `bridgeapi` (10002); the API console runs as
`student` (10001). Different identities reduce direct same-user access, but
filesystem permissions and kernel policies still determine actual access.
See [demo supervision](../demo-ver/app/supervisor.py).

## Lab threat model

The lab retains a model policy that refuses deployment disclosure. Students
explore whether accepted Markdown can cause the model to violate that policy.
The intended progression then reaches chat Telnet, private service discovery,
scan detection and the historical libssh endpoint.

| Threat or teaching condition | Consequence | Existing boundary and limitation |
| --- | --- | --- |
| Fenced-document prompt injection | Model may disclose the chat inventory | A refusal prompt is probabilistic behavior, not a confidentiality boundary |
| Chat Telnet foothold | Student can investigate the private subnet | Shell is non-root but has ambient `NET_RAW` for lab SYN/decoy scans |
| Historical libssh authentication weakness | Student can obtain a shell without normal authentication in the teaching endpoint | Shell is `labssh` (10004), separate from API/model `labapi` (10003) |
| Single apparent scanning source | Guard temporarily drops new TCP connections from that source | Can also disrupt legitimate chat-to-API requests using the same address |
| Multiple apparent scanning sources | Guard deliberately withholds blocking | An attribution mistake; logs still identify matching scan traffic |
| Sensor or guard failure | Logging or enforcement may stop independently | An absent block does not prove an absent scan |
| Resource or log growth | Reduced availability or exhausted storage | Current Compose does not specify CPU/memory limits or an EVE rotation policy |

The historical weakness is an authentication-state error in affected libssh
server code. The lab's additional example-server patch makes shell access
observable. This is not a claim that SSH encryption is broken or that all SSH
servers are vulnerable. See [the protocol guide](03-telnet-and-libssh.md).

## Containment and current configuration qualifications

Both versions publish chat endpoints to host loopback, give the API no published
ports, and put the API only on an internal Docker network. This limits ordinary
student entry points. Native Linux host routing and Docker administration are
outside that boundary; the gateway is also attached to a non-internal network,
so API isolation must not be described as whole-lab air-gapping.
[Docker internal-network reference](https://docs.docker.com/reference/compose-file/networks/#internal).

Chat/API root filesystems are read-only with writable `/tmp`. A root supervisor
launches the application children under specified non-root UIDs. Neither setting
turns an intentionally exposed shell into a harmless interface.

**Current source qualification:** `lab-ver/compose.yaml` now declares Suricata
`privileged: true`. Its capability list must not be presented as a reliable
least-privilege boundary in that configuration. Privileged execution substantially
expands container privileges and device access.
[Docker privilege reference](https://docs.docker.com/engine/containers/run/#runtime-privilege-and-linux-capabilities).

The same entrypoint attempts to change ownership of `/rules/suricata.yaml` despite
mounting `/rules` read-only. That operation can fail before Suricata starts,
because startup uses `&&`. This is a source-review finding, not a new runtime
test. The earlier validation report predates these changes. These documents
leave the configuration as requested; they do not certify its current startup.

## Evidence students should collect

Record the Markdown accepted/rejected result, actual model reply, shell identity,
target address, port states, timestamped EVE records and guard events. Compare the
single-source and decoy trials only after the earlier ban expires. Model output
alone proves neither shell access nor API reachability; a scan alert alone proves
neither successful compromise nor blocking.

Instructor evidence sources:
[Compose](../lab-ver/compose.yaml), [supervisor](../lab-ver/app/supervisor.py),
[policy](../lab-ver/ids/policy.py), [guard](../lab-ver/ids/guard.py),
[live checker](../lab-ver/tests/verify_live.py),
[historical validation](../lab-ver/instructor/validation.md).

## Review questions

1. Why does a private API remain reachable after the gateway becomes a foothold?
2. Why does a valid `.md` extension say little about whether its contents contain instructions?
3. What differs between a non-root shell, API-process access and root access?
4. What evidence separates successful detection from successful blocking?
