"""Shared installer checks. No system, firmware, or disk writes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / 'downloads.json').read_text())
DSDT_SHA = '85ba996338970eade321de17b0399a253aba02b2ebf525233551c7ecc4d86a6b'
DSDT_FIXED_SHA = '46ee3d58c8bb0b5977b6d5e8dd148afa145b2217cf30c3b5e762e5d13fb83464'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def fetch(name, cache):
    pin = PINS[name]
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / name
    if not dest.exists():
        temp = cache / (name + '.download')
        print('Downloading ' + name, flush=True)
        try:
            with urllib.request.urlopen(pin['url'], timeout=90) as response, temp.open('wb') as f:
                shutil.copyfileobj(response, f)
            require(digest(temp) == pin['sha256'], 'Download checksum mismatch: ' + name)
            temp.replace(dest)
        finally:
            temp.unlink(missing_ok=True)
    require(digest(dest) == pin['sha256'], 'Cached download checksum mismatch: ' + name)
    return dest


def extract(archive, dest):
    """Extract only ordinary files/directories; reject path traversal and links."""
    require(not dest.exists(), 'Extraction destination already exists')
    with zipfile.ZipFile(archive) as z:
        seen = set()
        for item in z.infolist():
            p = PurePosixPath(item.filename)
            mode = item.external_attr >> 16
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in item.filename
                    and ':' not in item.filename and item.filename not in seen,
                    'Unsafe or duplicate archive member')
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), 'Archive contains a link/special file')
            seen.add(item.filename)
        dest.mkdir(parents=True)
        for item in z.infolist():
            target = dest / item.filename
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(item) as src, target.open('xb') as out:
                    shutil.copyfileobj(src, out)
                target.chmod(0o755 if (item.external_attr >> 16) & 0o111 else 0o644)
    return dest


def check_hardware(report, dsdt):
    require(report.get('schema') == 1, 'Unsupported hardware report')
    require(report.get('board') == '8BDF' and report.get('bios') == 'F.03'
            and report.get('bios_date') == '08/29/2023', 'Only HP 8BDF BIOS F.03 (08/29/2023) is qualified')
    require(report.get('manufacturer') == 'HP' and '15-fe0' in report.get('product', ''), 'Wrong HP model')
    require('i7-1355U' in report.get('cpu', ''), 'Only the i7-1355U profile is qualified')
    require(report.get('logical_cpus') == 12, 'All 12 logical CPUs must be online')
    pci = report.get('pci', [])
    for device in ('8086:a7a1:103c:8bdf', '8086:51f1:8086:0094'):
        require(device in pci, 'Required device absent: ' + device)
    require(report.get('cfg_lock_clear') is True and report.get('msr_cpus') == list(range(12)),
            'CFG Lock must be measured clear on every CPU; follow docs/CPU-UNLOCK.md and recollect')
    require(hashlib.sha256(dsdt).hexdigest() == DSDT_SHA, 'Firmware DSDT differs; no automatic patch is safe for this table')
    require(report.get('dsdt_sha256') == DSDT_SHA, 'Hardware report and DSDT disagree')


def patch_dsdt(original):
    """Exact-byte replay of the qualified HP patch, not a general AML rewriter.

    Deferring the HS07 scope with If(One) follows nullmoth/1401's pass-one
    repair. This fixed transformation is independently encoded for this table.
    See ACPI-PROVENANCE.md. Firmware itself is never written.
    """
    require(hashlib.sha256(original).hexdigest() == DSDT_SHA, 'Unknown DSDT')
    data = bytearray(original)
    # The 721-byte Scope becomes a 725-byte If package: predicate One + Scope.
    # Parent PkgLength is updated below; all other payload bytes are preserved.
    offset = 0x9717d
    data[offset:offset] = bytes.fromhex('a0442d01')
    # Parent package has a three-byte AML PkgLength at 0x966ad.
    lead = data[0x966ad]
    count = lead >> 6
    length = (lead & 15) + sum(data[0x966ad + i] << (4 + 8 * (i - 1)) for i in range(1, count + 1))
    length += 4
    data[0x966ad] = (count << 6) | (length & 15)
    for i in range(1, count + 1):
        data[0x966ad + i] = (length >> (4 + 8 * (i - 1))) & 255
    data[4:8] = len(data).to_bytes(4, 'little')
    data[9] = 0
    data[9] = -sum(data) & 255
    require(hashlib.sha256(data).hexdigest() == '0899799edc05029d58579091569666aa8ce9f85dcafb573fbb9993cfc6293d37',
            'Pass-one output differs from the qualified table')
    require(data[0x70f40:0x70f44] == b'_CRS', 'I2C0 resource method mismatch')
    data[0x70f40] = ord('X')
    data[9] = 0
    data[9] = -sum(data) & 255
    require(hashlib.sha256(data).hexdigest() == DSDT_FIXED_SHA, 'Final ACPI table mismatch')
    return bytes(data)
