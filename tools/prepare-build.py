#!/usr/bin/env python3
"""Prepare pinned, ignored build dependencies. Does not install any drivers."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'XPS-IrisXe': ('https://github.com/JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe.git',
                  '6b5f0492f72308243af222a0aa43fe11db64db3c', 'graphics/source/XPS-IrisXe'),
    'itlwm': ('https://github.com/laobamac/itlwm.git',
              '738d4c61b5a64433b27c1ab09dba94916ab77d8d', 'fixes-20261024/wifi-native-pnvm/source'),
    'XPS-IrisXe/build/deps/MacKernelSDK': ('https://github.com/acidanthera/MacKernelSDK.git',
              '3f750085caa17ec3a7880f11c11bf4f48cd6a164', 'graphics/source/XPS-IrisXe/build/deps/MacKernelSDK'),
}
LILU_SHA = 'e95df95d82e8b151047abf359ecd9c853755c59293e19dfcc3907da8fbd8cf89'

def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-cache', type=Path, help='Existing hp-macos-postinstall tree; avoids downloads')
    args = parser.parse_args()
    deps = ROOT/'deps'
    deps.mkdir(exist_ok=True)
    for name, (url, commit, cache) in PINS.items():
        dest = deps/name
        if not dest.exists():
            source = str(args.local_cache/cache) if args.local_cache else url
            run('git', 'clone', '--no-hardlinks', '--no-checkout', source, str(dest))
            run('git', 'checkout', '--detach', commit, cwd=dest)
        if run('git', 'rev-parse', 'HEAD', cwd=dest) != commit:
            raise SystemExit('Dependency revision changed: '+name)
    for component, dest in [('graphics', deps/'XPS-IrisXe/src/NootedGreen'), ('wifi', deps/'itlwm')]:
        for source in (ROOT/'drivers'/component/'overlay').rglob('*'):
            if source.is_file():
                target = dest/source.relative_to(ROOT/'drivers'/component/'overlay')
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and target.read_bytes() == source.read_bytes():
                    continue
                shutil.copyfile(source, target)
    build_deps = deps/'XPS-IrisXe/build/deps'
    archive = build_deps/'lilu.zip'
    if not archive.exists():
        if args.local_cache:
            shutil.copyfile(args.local_cache/'graphics/source/XPS-IrisXe/build/deps/lilu.zip', archive)
        else:
            urllib.request.urlretrieve('https://github.com/acidanthera/Lilu/releases/download/1.7.2/Lilu-1.7.2-DEBUG.zip', archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != LILU_SHA:
        raise SystemExit('Lilu archive hash mismatch; refusing extraction')
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            rel = Path(member.filename)
            if rel.is_absolute() or '..' in rel.parts:
                raise SystemExit('Unsafe ZIP member')
            if rel.parts and rel.parts[0] == 'Lilu.kext':
                z.extract(member, build_deps)
    if not (build_deps/'Lilu.kext/Contents/Resources/Library/plugin_start.cpp').is_file():
        raise SystemExit('Lilu development resources missing')
    print('Pinned dependencies and HP source overlays prepared. Nothing installed.')

if __name__ == '__main__':
    main()
