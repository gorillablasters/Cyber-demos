import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from console import TelnetInput

class TelnetTests(unittest.TestCase):
    def test_normalizes_crlf_even_across_packets(self):
        decoder = TelnetInput()
        self.assertEqual(decoder.decode(b'id\r')[0], b'id\n')
        self.assertEqual(decoder.decode(b'\nexit\r\x00')[0], b'exit\n')

    def test_declines_options_without_passing_them_to_shell(self):
        decoder = TelnetInput()
        self.assertEqual(decoder.decode(bytes([255, 251, 1])), (b'', bytes([255, 254, 1])))
        self.assertEqual(decoder.decode(bytes([255, 253, 3])), (b'', bytes([255, 252, 3])))
        self.assertEqual(decoder.decode(b'id\n'), (b'id\n', b''))
