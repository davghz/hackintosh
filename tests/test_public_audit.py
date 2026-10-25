"""Exercise rejection of accidental private material in a publication."""
import importlib.util
from pathlib import Path
import plistlib
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('public_audit', ROOT/'tools/audit-public.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class PublicAuditTests(unittest.TestCase):
    def test_accepts_source_and_empty_identity(self):
        values = {'SystemSerialNumber':'','MLB':'','SystemUUID':'','ROM':bytes(6)}
        self.assertFalse(audit.audit({'README.md':b'Documentation',
            'config/example.plist':plistlib.dumps(values)}))

    def test_rejects_private_and_generated_paths(self):
        for name in ['private/data.txt','deps/a.c','tools/cpu-unlock/early-cfg/expected.h',
                     'tools/state.efivar','drivers/gpu/build/a.cpp','drivers/gpu/a.efi',
                     'drivers/graphics/overlay/IGGucBinary.h']:
            with self.subTest(name=name): self.assertTrue(audit.audit({name:b'example'}))

    def test_rejects_populated_identity(self):
        for key in ['SystemSerialNumber','MLB','SystemUUID','Password','WiFiConfig']:
            with self.subTest(key=key):
                self.assertTrue(audit.audit({'config/example.plist':plistlib.dumps({key:'example-value'})}))

    def test_rejects_token_and_key_without_echoing_value(self):
        for value in [('ghp_'+'A'*40).encode(), ('-----BEGIN '+'PRIVATE KEY-----').encode()]:
            messages = audit.audit({'docs/example.md':value})
            self.assertTrue(messages)
            self.assertNotIn(value.decode(),str(messages))

    def test_rejects_empty_binary_and_traversal_sets(self):
        self.assertTrue(audit.audit({}))
        self.assertTrue(audit.audit({'docs/file.txt':b'a\0b'}))
        self.assertTrue(audit.audit({'docs/../private/file.txt':b'example'}))

if __name__ == '__main__': unittest.main()
