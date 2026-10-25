"""Exercise the publication helper without reading/writing real firmware."""
import importlib.util
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('baseline', ROOT/'tools/cpu-unlock/early-cfg/prepare_baseline.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)

class BaselineGuardTests(unittest.TestCase):
    def setUp(self):
        self.raw = bytearray(struct.pack('<I',7)+bytes(961))
        self.raw[4+0x43] = 1
        self.identity = dict(baseline.IDENTITY)

    def test_payload_excludes_attributes_and_preserves_other_bytes(self):
        for i in range(961):
            if i != 0x43: self.raw[4+i] = i % 256
        self.assertEqual(baseline.validate(bytes(self.raw),self.identity),bytes(self.raw[4:]))

    def test_each_identity_guard(self):
        for key in self.identity:
            changed = dict(self.identity);changed[key] += '-different'
            with self.assertRaises(ValueError): baseline.validate(bytes(self.raw),changed)

    def test_length_and_attributes(self):
        for bad in [self.raw[:-1], self.raw+b'\0', struct.pack('<I',3)+self.raw[4:]]:
            with self.assertRaises(ValueError): baseline.validate(bytes(bad),self.identity)

    def test_rejects_already_unlocked_and_unexpected_values(self):
        for value in [0,2,255]:
            self.raw[4+0x43] = value
            with self.assertRaises(ValueError): baseline.validate(bytes(self.raw),self.identity)

    def test_header_has_entire_payload(self):
        import re
        payload = baseline.validate(bytes(self.raw),self.identity)
        text = baseline.header(payload)
        self.assertEqual(bytes(int(x,16) for x in re.findall(r'0x([0-9a-f]{2})',text)),payload)

if __name__ == '__main__': unittest.main()
