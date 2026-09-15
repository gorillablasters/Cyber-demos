# Lab-ver validation status

This variant replaces the copied demo topology. The old demo's live-test results
must not be applied to this SSH/IDS setup.

2026-09-15: all 14 local tests pass, including five scan-attribution policy tests.
Live Docker build, libssh authentication bypass, Suricata rule loading, and packet
blocking/decoy suppression are pending: Docker sockets were unavailable in this
session. See README.md for the exact live checks.
