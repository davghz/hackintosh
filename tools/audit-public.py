#!/usr/bin/env python3
"""Check the staged Git file set, optionally exporting only those exact bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'README.md', 'LICENSE', 'CONTRIBUTING.md', 'CHANGELOG.md', '.gitignore', '.gitattributes', 'docs', 'drivers',
           'tools', 'config', 'experiments', 'licenses', 'verification', 'tests'}
DENIED_SUFFIX = {'.efivar', '.efi', '.o', '.so', '.kc', '.dmg', '.img', '.fd',
                 '.zip', '.gz', '.zst', '.jpg', '.jpeg', '.png', '.heic', '.pyc'}

def staged_files():
    entries = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=ROOT).decode().split('\0')
    for entry in filter(None, entries):
        metadata, name = entry.split('\t', 1)
        mode, _, stage = metadata.split()
        if mode not in {'100644','100755'} or stage != '0':
            raise SystemExit('Non-regular or unmerged index entry: '+name)
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    return {name: subprocess.check_output(['git', 'show', ':'+name], cwd=ROOT)
            for name in names if name}

def audit(files):
    failures = []
    if not files:
        failures.append('Nothing staged')
    for name, data in files.items():
        p = Path(name)
        if not p.parts or p.parts[0] not in ALLOWED or p.is_absolute() or '..' in p.parts:
            failures.append(name+': outside publication directories')
        if (p.suffix.lower() in DENIED_SUFFIX or any(x in {'private','deps','.git','__pycache__','vm-test','build'}
            or x.startswith('build-v') for x in p.parts) or p.name in {'expected.h','installation.json','vm-test-result.json','build-manifest.json',
            'IGGucBinary.h','IGHucBinary.h','Firmware.cpp','FirmwareADLP.cpp'}):
            failures.append(name+': private or generated artifact')
        if b'\0' in data or len(data) > 50*1024*1024:
            failures.append(name+': binary or oversized file')
        text = data.decode('utf-8', errors='replace')
        # Report locations only, never secret values.
        for pattern in [r'gh[pousr]_[A-Za-z0-9]{30,}', r'github_pat_[A-Za-z0-9_]{40,}',
                        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                        r'(?i)(?:password|passwd|psk)\s*[:=]\s*[\x22\x27][^\x22\x27\n]{8,}[\x22\x27]']:
            if re.search(pattern, text):
                failures.append(name+': credential-like literal needs review')
        if p.suffix == '.plist':
            try:
                parsed = plistlib.loads(data)
            except Exception:
                failures.append(name+': invalid plist')
                continue
            def inspect(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key in {'SystemSerialNumber','MLB','SystemUUID','Password','PasswordHash','PasswordSalt','WiFiConfig'} and value:
                            failures.append(name+': private identity/credential field populated')
                        if key == 'ROM' and value not in (b'', bytes(6)):
                            failures.append(name+': ROM identity populated')
                        inspect(value)
                elif isinstance(obj, list):
                    for value in obj: inspect(value)
            inspect(parsed)
    return failures

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, help='Write a new public-only ZIP; refuses replacement')
    args = parser.parse_args()
    files = staged_files()
    failures = audit(files)
    result = {'passed': not failures, 'files':len(files), 'bytes':sum(map(len,files.values())), 'failures':failures,
              'scope':'Staged paths, identifiers, common credential patterns and excluded artifacts; not an exhaustive secret detector'}
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(1)
    if args.zip:
        with zipfile.ZipFile(args.zip, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in sorted(files.items()):
                z.writestr('hackintosh/'+name, data)
        with zipfile.ZipFile(args.zip) as z:
            assert len(z.infolist()) == len(files)
            for name, data in files.items():
                assert z.read('hackintosh/'+name) == data
        print('Verified every exported file. ZIP SHA-256:', hashlib.sha256(args.zip.read_bytes()).hexdigest())

if __name__ == '__main__':
    main()
