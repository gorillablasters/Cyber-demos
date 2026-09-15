import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ids'))
from policy import Policy


class ScanPolicyTests(unittest.TestCase):
    def test_normal_chat_connections_do_not_count_as_port_scan(self):
        p = Policy()
        for i in range(100):
            p.observe('172.30.109.10', 8000, i * .01)
        self.assertEqual(p.tick(2), [])

    def test_one_scanning_source_is_blocked_then_expires(self):
        p = Policy()
        for port in range(1, 9):
            p.observe('172.30.109.10', port, 0)
        self.assertEqual(p.tick(.4), [])
        self.assertEqual(p.tick(.6), [('block', '172.30.109.10')])
        self.assertEqual(p.tick(21), [('unblock', '172.30.109.10')])

    def test_two_apparent_scanners_suppress_blocking_but_are_logged(self):
        p = Policy()
        for port in range(1, 9):
            for source in ['172.30.109.10', '172.30.109.11']:
                p.observe(source, port, 0)
        self.assertEqual(set(p.tick(.6)), {('suppress', '172.30.109.10'), ('suppress', '172.30.109.11')})
        self.assertEqual(p.blocked, {})
        self.assertEqual(p.tick(1), [])

    def test_a_single_extra_connection_does_not_suppress_block(self):
        p = Policy()
        for port in range(1, 9):
            p.observe('172.30.109.10', port, 0)
        p.observe('172.30.109.11', 8000, 0)
        self.assertEqual(p.tick(.6), [('block', '172.30.109.10')])

    def test_slow_probes_age_out(self):
        p = Policy()
        for port in range(1, 20):
            p.observe('172.30.109.10', port, port)
            self.assertEqual(p.tick(port + .6), [])
