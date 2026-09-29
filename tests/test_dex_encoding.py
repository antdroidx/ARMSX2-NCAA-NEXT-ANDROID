"""Independent synthetic encodings exercise the new audit's key boundary."""
import hashlib
import struct
import sys
import unittest
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_dex import audit


def fixture(parameters, encoded, opcode=0x76):
    data = bytearray(112)
    data[:8] = b"dex\n035\0"
    def u4(at, value):
        struct.pack_into("<I", data, at, value)
    def block(content):
        off = len(data)
        data.extend(content)
        return off
    strings = ["LExample;", "I", "<init>"]
    string_ids = block(b"\0" * 12)
    u4(56, 3)
    u4(60, string_ids)
    types = block(struct.pack("<II", 0, 1))
    u4(64, 2)
    u4(68, types)
    proto = block(b"\0" * 12)
    u4(72, 1)
    u4(76, proto)
    method = block(struct.pack("<HHI", 0, 0, 2))
    u4(88, 1)
    u4(92, method)
    params = block(struct.pack("<I", parameters) + struct.pack("<H", 1) * parameters)
    u4(proto+8, params)
    for i, value in enumerate(strings):
        u4(string_ids+4*i, block(bytes([len(value)]) + value.encode() + b"\0"))
    offset = block(bytes([opcode, encoded, 0, 0, 0, 0]))
    u4(32, len(data))
    u4(40, 0x12345678)
    data[12:32] = hashlib.sha1(data[32:]).digest()
    u4(8, zlib.adler32(data[12:]))
    return data, f"{offset:06x}: 7600 0000 0000 |0000: invoke-direct/range {{}}"


class EncodingTests(unittest.TestCase):
    def test_255_word_call_is_valid(self):
        self.assertEqual(1, audit(*fixture(254, 255))["invokes_checked"])

    def test_256_word_call_wrapped_to_zero_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "expected 256 words, encoded 0"):
            audit(*fixture(255, 0))

    def test_zero_word_instance_call_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "expected 1 words, encoded 0"):
            audit(*fixture(0, 0))

    def test_zero_word_static_call_is_valid(self):
        self.assertEqual(1, audit(*fixture(0, 0, 0x77))["invokes_checked"])

    def test_missing_disassembly_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "No supported invokes"):
            audit(fixture(0, 0, 0x77)[0], "")


if __name__ == "__main__":
    unittest.main()
