"""Deliberately weak attribution policy, NOT a general Nmap/decoy detector."""
from collections import defaultdict


class Policy:
    def __init__(self, threshold=8, window=3.0, grace=0.5, ban_seconds=20.0):
        self.threshold, self.window, self.grace, self.ban_seconds = threshold, window, grace, ban_seconds
        self.ports = defaultdict(dict)
        self.pending, self.blocked, self.suppressed = {}, {}, set()

    def observe(self, source, port, now):
        self.ports[source][port] = now
        self._prune(now)
        if len(self.ports[source]) >= self.threshold and source not in self.blocked and source not in self.suppressed:
            self.pending.setdefault(source, now + self.grace)

    def _prune(self, now):
        for source in list(self.ports):
            self.ports[source] = {port: seen for port, seen in self.ports[source].items() if now - seen <= self.window}
            if not self.ports[source]:
                del self.ports[source]
                self.pending.pop(source, None)
                self.suppressed.discard(source)

    def tick(self, now):
        self._prune(now)
        actions = []
        for source, until in list(self.blocked.items()):
            if now >= until:
                del self.blocked[source]
                actions.append(('unblock', source))
        actors = {source for source, ports in self.ports.items() if len(ports) >= self.threshold}
        for source, deadline in list(self.pending.items()):
            if now < deadline:
                continue
            del self.pending[source]
            if source not in actors:
                continue
            if len(actors) >= 2:
                self.suppressed.add(source)
                actions.append(('suppress', source))
            else:
                self.blocked[source] = now + self.ban_seconds
                actions.append(('block', source))
        return actions
