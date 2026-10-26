#!/usr/bin/env python3
"""Read the target HP from a Linux live session; save a private installer input.

Run: sudo modprobe msr
     sudo python3 collect-hardware.py /path/on/USB/HP-hardware
No serial numbers, network credentials or firmware variables are collected.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    if platform.system() != 'Linux' or os.geteuid() != 0:
        p.error('Use sudo in a Linux live session on the target HP')
    if args.output.exists():
        p.error('Output already exists; choose a new directory')
    dmi = Path('/sys/class/dmi/id')
    read = lambda name: (dmi / name).read_text().strip()
    data = Path('/sys/firmware/acpi/tables/DSDT').read_bytes()
    cpus = []
    for group in Path('/sys/devices/system/cpu/online').read_text().strip().split(','):
        ends = list(map(int, group.split('-')))
        cpus.extend(range(ends[0], ends[-1] + 1))
    states = []
    for cpu in cpus:
        with open('/dev/cpu/%d/msr' % cpu, 'rb', buffering=0) as f:
            value = os.pread(f.fileno(), 8, 0xe2)
        if len(value) != 8:
            raise ValueError('Short MSR read')
        states.append(bool(int.from_bytes(value, 'little') & (1 << 15)))
    pci = []
    for device in Path('/sys/bus/pci/devices').iterdir():
        fields = [device / n for n in ('vendor', 'device', 'subsystem_vendor', 'subsystem_device')]
        if all(f.exists() for f in fields):
            pci.append(':'.join(f.read_text().strip().removeprefix('0x').lower() for f in fields))
    model = re.search(r'^model name\s*:\s*(.*)$', Path('/proc/cpuinfo').read_text(), re.M)
    report = dict(schema=1, manufacturer=read('sys_vendor'), product=read('product_name'),
                  board=read('board_name'), bios=read('bios_version'), bios_date=read('bios_date'),
                  cpu=model.group(1) if model else '', logical_cpus=len(cpus), msr_cpus=cpus,
                  cfg_lock_clear=not any(states), pci=sorted(set(pci)),
                  dsdt_sha256=hashlib.sha256(data).hexdigest())
    args.output.mkdir(mode=0o700, parents=True)
    (args.output / 'hardware.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'DSDT.aml').write_bytes(data)
    print('Saved private hardware input to', args.output)
    print('CFG Lock:', 'clear on all online CPUs' if not any(states) else 'LOCKED; follow docs/CPU-UNLOCK.md')


if __name__ == '__main__':
    main()
