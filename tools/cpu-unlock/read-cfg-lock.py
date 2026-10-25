"""Read CFG Lock status on every available logical CPU; makes no changes."""
import glob
import os

locked = 0
errors = 0
paths = sorted(glob.glob('/dev/cpu/[0-9]*/msr'), key=lambda p: int(p.split('/')[3]))
if not paths:
    raise SystemExit('No MSR devices. Load the msr module, then retry as root.')
for path in paths:
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            raw = os.pread(fd, 8, 0xE2)
        finally:
            os.close(fd)
        if len(raw) != 8:
            raise OSError('Short MSR read')
        value = int.from_bytes(raw, 'little')
        bit = (value >> 15) & 1
        locked += bit
        print(f'CPU {path.split("/")[3]}: MSR 0xE2=0x{value:016X}; CFG Lock bit15={bit}')
    except OSError as exc:
        errors += 1
        print(f'{path}: {exc}')
if errors:
    raise SystemExit('Could not verify every CPU.')
print('CFG LOCK IS STILL ENABLED.' if locked else 'CFG LOCK IS DISABLED on all checked CPUs.')
