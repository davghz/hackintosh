#!/usr/bin/env python3
"""Verify an assembled private kit, optionally copying it to a blank external FAT32 volume.

Never formats a disk or replaces an existing EFI or Recovery directory.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import shutil
import subprocess
import sys
import uuid
from common import digest, require


def verify_files(root, hashes):
    require(hashes, 'Empty file manifest')
    expected = set()
    for name, sha in hashes.items():
        rel = PurePosixPath(name)
        require(not rel.is_absolute() and '..' not in rel.parts and '\\' not in name
                and rel.parts[0] in {'EFI', 'com.apple.recovery.boot'}, 'Unsafe manifest path')
        require(len(sha) == 64, 'Invalid manifest digest')
        path = root / name
        require(path.is_file() and not path.is_symlink(), 'Missing/non-regular file: ' + name)
        require(all(not (root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts))),
                'Symlink in kit path')
        require(digest(path) == sha, 'Changed file: ' + name)
        expected.add(name)
    actual = {str(p.relative_to(root)) for directory in ('EFI', 'com.apple.recovery.boot')
              for p in (root / directory).rglob('*') if p.is_file()}
    require(actual == expected, 'Extra or missing files in boot directories')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('kit', type=Path)
    p.add_argument('--copy-to', type=Path, help='Mounted external FAT32 volume; must have no EFI/Recovery directories')
    args = p.parse_args()
    kit = args.kit.resolve()
    require(not (kit / 'INCOMPLETE.txt').exists(), 'This build did not complete')
    manifest = json.loads((kit / 'manifest.json').read_text())
    require(manifest.get('schema') == 1, 'Unknown manifest version')
    verify_files(kit / 'USB', manifest['sha256'])
    spec = importlib.util.spec_from_file_location('prepare', Path(__file__).with_name('prepare-installer.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.validate_efi(kit / 'USB/EFI', kit / 'dependencies/opencore/Utilities/ocvalidate/ocvalidate')
    print('Every boot file and OpenCore configuration verified.')
    if not args.copy_to:
        return
    require(manifest.get('recovery') is not None, 'EFI-only output cannot be copied as a complete installer')
    target = args.copy_to.resolve()
    info = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', str(target)]))
    require(info.get('Internal') is False and info.get('FilesystemType') == 'msdos'
            and info.get('MountPoint') == str(target), 'Target must be the root of a mounted external FAT32 volume')
    for name in ('EFI', 'com.apple.recovery.boot'):
        require(not (target / name).exists(), 'Existing ' + name + ' preserved; use a blank installer USB')
    total = sum((kit / 'USB' / name).stat().st_size for name in manifest['sha256'])
    require(shutil.disk_usage(target).free > total + 64 * 1024**2, 'Insufficient USB space')
    require(all((kit / 'USB' / name).stat().st_size < 2**32 for name in manifest['sha256']), 'A file exceeds FAT32 limits')
    staging = target / ('.hp-installer-' + uuid.uuid4().hex)
    # Files copy into staging first. EFI becomes visible only after full readback.
    shutil.copytree(kit / 'USB', staging, copy_function=shutil.copyfile)
    verify_files(staging, manifest['sha256'])
    os.sync()
    for name in ('com.apple.recovery.boot', 'EFI'):
        require(not (target / name).exists(), 'Target changed during copy; refusing replacement')
        (staging / name).rename(target / name)
    staging.rmdir()
    os.sync()
    verify_files(target, manifest['sha256'])
    print('Copied and read back every byte:', target)
    print('Eject the USB in Finder, then follow docs/INSTALL.md for the HP boot test.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('Stopped:', error, file=sys.stderr)
        sys.exit(1)
