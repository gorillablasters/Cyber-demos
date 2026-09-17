# Educational lab guides

Five guides for students and instructors using `demo-ver` and `lab-ver`.
Prepared September 17, 2026, from the repository at commit `857a783`.
These are documentation guides; preparing them did not modify or restart services.

| Guide | What it covers |
| --- | --- |
| [Educational threat model](01-educational-threat-model.md) | Assets, actors, trust boundaries, intended weaknesses, containment and residual risks in both versions |
| [Architecture](02-architecture.md) | Components, network diagrams, ports, process identities and request flows |
| [Telnet and libssh basics](03-telnet-and-libssh.md) | Remote terminals, encryption, authentication, port numbers and the historical SSH weakness |
| [Port discovery with Nmap](04-nmap-port-discovery.md) | Choosing a target, interpreting results and comparing the two lab scan trials |
| [IDS and Suricata basics](05-ids-and-suricata.md) | Visibility, rules, EVE logs and the deliberately weak response policy |

For a first lesson, read architecture, remote protocols, Nmap and IDS in that order.
Use the threat model to discuss what each exercise demonstrates and what it does
not prove. Each guide includes short review questions.

## Shared classroom conventions

- Host commands run in a terminal on the machine running Docker.
- Student commands run in the chatbot's Telnet shell when explicitly indicated.
- Instructor commands use Docker Compose from the named version's directory.
- Examples use only the assigned lab containers. The lab's default private API
  address is `172.30.109.20`; the demo's API address is dynamically assigned.
- The checked-in environment examples and current local settings use host HTTP
  ports **8080 / 8081** and host Telnet ports **2323 / 2324** for demo / lab.
  Environment overrides can change these mappings.

## Current source versus historical validation

The current demo intentionally permits direct port disclosure. Its Markdown
parser still skips fenced content when looking for override text, but obtaining
the demo's port list no longer requires an injection.

The [September 15 lab validation report](../lab-ver/instructor/validation.md)
records successful tests of an earlier configuration. The current Compose file
has subsequent changes, including privileged Suricata execution and an ownership
operation on a read-only rules mount. The architecture and threat model identify
these differences. Historical results are not a new runtime verification of the
current checkout.

Primary protocol/tool references are linked beside the relevant explanations.
Repository links identify the implementation on which the lab-specific material
is based.
