"""Installer boundary tests use temporary files only, never actual disks/firmware."""
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/installer'))
import common
spec = importlib.util.spec_from_file_location('verify_kit', ROOT / 'tools/installer/verify-kit.py')
verify_kit = importlib.util.module_from_spec(spec); spec.loader.exec_module(verify_kit)
spec = importlib.util.spec_from_file_location('prepare_installer', ROOT / 'tools/installer/prepare-installer.py')
prepare_installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare_installer)


class InstallerBoundaryTests(unittest.TestCase):
    def test_wifi_uses_itlwm_schema_without_echoing_secrets(self):
        phrase = 'x' * 12
        result = prepare_installer.wifi_configuration('A & B', phrase)
        self.assertEqual(result, {'WiFi_1': {'ssid': 'A & B', 'password': phrase}})
        for ssid, secret in [('', phrase), ('é' * 17, phrase), ('ok', 'short'),
                             ('ok', 'x' * 64), ('ok', 'é' * 8), ('ok', 'x' * 8 + '\n')]:
            with self.assertRaises(ValueError) as caught:
                prepare_installer.wifi_configuration(ssid, secret)
            self.assertNotIn(secret, str(caught.exception))

    def test_unknown_firmware_never_reaches_patch_offsets(self):
        for payload in (b'', b'DSDT' + bytes(636394)):
            with self.assertRaisesRegex(ValueError, 'Unknown DSDT'):
                common.patch_dsdt(payload)

    def test_hardware_guards_independent_of_original_firmware(self):
        fake_dsdt = b'unit-test-only'
        sha = hashlib.sha256(fake_dsdt).hexdigest()
        report = dict(schema=1, manufacturer='HP', product='HP Envy 15-fe0xxx', board='8BDF',
                      bios='F.03', bios_date='08/29/2023', cpu='i7-1355U', logical_cpus=12,
                      msr_cpus=list(range(12)), cfg_lock_clear=True,
                      pci=['8086:a7a1:103c:8bdf', '8086:51f1:8086:0094'], dsdt_sha256=sha)
        with patch.object(common, 'DSDT_SHA', sha):
            common.check_hardware(report, fake_dsdt)
            for key, value in [('board', '8BDD'), ('bios', 'F.04'), ('cpu', 'i5-1335U'),
                               ('logical_cpus', 10), ('cfg_lock_clear', False), ('msr_cpus', list(range(11))),
                               ('pci', ['8086:a7a1:103c:8bdf']), ('manufacturer', 'Different'),
                               ('dsdt_sha256', '0' * 64), ('bios_date', '01/01/2024')]:
                with self.subTest(key=key), self.assertRaises(ValueError):
                    common.check_hardware(dict(report, **{key: value}), fake_dsdt)

    def test_archive_rejects_paths_and_links_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for i, name in enumerate(['../escape', '/absolute', 'a/../../escape', 'a\\..\\escape', 'C:/escape', 'link']):
                archive = root / ('%d.zip' % i)
                with zipfile.ZipFile(archive, 'w') as z:
                    item = zipfile.ZipInfo(name)
                    if name == 'link':
                        item.create_system = 3; item.external_attr = (stat.S_IFLNK | 0o777) << 16
                    z.writestr(item, b'target')
                destination = root / ('out%d' % i)
                with self.subTest(name=name), self.assertRaises(ValueError):
                    common.extract(archive, destination)
                self.assertFalse(destination.exists())

    def test_tampered_cache_is_rejected_without_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'opencore').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                common.fetch('opencore', root)

    def test_readback_rejects_changed_extra_missing_and_linked_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'EFI').mkdir()
            file = root / 'EFI/test'; file.write_bytes(b'good')
            hashes = {'EFI/test': hashlib.sha256(b'good').hexdigest()}
            verify_kit.verify_files(root, hashes)
            file.write_bytes(b'bad')
            with self.assertRaises(ValueError): verify_kit.verify_files(root, hashes)
            file.write_bytes(b'good'); extra = root / 'EFI/extra'; extra.write_bytes(b'')
            with self.assertRaises(ValueError): verify_kit.verify_files(root, hashes)
            extra.unlink(); file.unlink()
            with self.assertRaises(ValueError): verify_kit.verify_files(root, hashes)
            extra.write_bytes(b'good'); file.symlink_to(extra)
            with self.assertRaises(ValueError): verify_kit.verify_files(root, hashes)

    def test_manifest_cannot_escape_boot_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            for path in ['../private/file', '/tmp/file', 'other/file', 'EFI/../../file']:
                with self.subTest(path=path), self.assertRaises(ValueError):
                    verify_kit.verify_files(Path(temp), {path: '0' * 64})


if __name__ == '__main__':
    unittest.main()
