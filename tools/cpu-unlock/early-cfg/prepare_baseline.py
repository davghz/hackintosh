#!/usr/bin/env python3
"""Read the exact supported HP's CpuSetup and generate local-only build inputs.

Does not write firmware, EFI variables, the ESP, or MSRs. Linux only.
"""
from pathlib import Path
import os
import platform
import struct

WORK = Path(__file__).resolve().parent
CPU_NAME = 'CpuSetup-b08f97ff-e6e8-4193-a997-5e9e9b0adb32'
IDENTITY = {'board_vendor': 'HP', 'board_name': '8BDF',
            'bios_version': 'F.03', 'bios_date': '08/29/2023'}

def validate(raw, identity):
    if identity != IDENTITY:
        raise ValueError('Board, BIOS or firmware date mismatch')
    if len(raw) != 965 or struct.unpack_from('<I', raw)[0] != 7:
        raise ValueError('Expected 4 attribute bytes (7) and a 961-byte CpuSetup payload')
    if raw[4+0x43] != 1:
        raise ValueError('CFG byte is not 1; if already unlocked, do not arm the driver')
    return raw[4:]

def header(payload):
    rows = [', '.join(f'0x{x:02x}' for x in payload[i:i+16]) for i in range(0, len(payload), 16)]
    return '/* PRIVATE: generated from this machine; never publish. */\nstatic const unsigned char expected_cpu[] = {\n' + ',\n'.join(rows) + '\n};\n'

def main():
    if platform.system() != 'Linux':
        raise SystemExit('This helper requires Linux booted directly on the target HP')
    identity = {key: (Path('/sys/class/dmi/id')/key).read_text().strip() for key in IDENTITY}
    raw = (Path('/sys/firmware/efi/efivars')/CPU_NAME).read_bytes()
    payload = validate(raw, identity)
    baseline = WORK.parent/'CpuSetup-original.efivar'
    expected = WORK/'expected.h'
    if baseline.exists() or expected.exists():
        raise SystemExit('Existing baseline/header preserved; inspect before preparing another build')
    os.umask(0o077)
    with baseline.open('xb') as f:
        f.write(raw)
    with expected.open('x') as f:
        f.write(header(payload))
    print('Saved private baseline and generated expected.h; firmware untouched.')
    print('Build and run the exact-binary OVMF tests before using manage.py install.')

if __name__ == '__main__':
    main()
