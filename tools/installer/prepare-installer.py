#!/usr/bin/env python3
"""Assemble a private HP 8BDF installer on macOS. Never installs to a disk.

Usage and prerequisites: docs/INSTALL.md. Output contains a unique identity
and optionally a Wi-Fi password; do not publish it.
"""
import argparse
import contextlib
import getpass
import importlib.util
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import secrets
import shutil
import subprocess
import sys
import uuid
from common import HERE, PINS, check_hardware, digest, extract, fetch, patch_dsdt, require
import build_input

GUID = '7C436110-AB2A-4BBB-A880-FE41995C9F82'


def wifi_configuration(ssid, passphrase):
    require(0 < len(ssid.encode('utf-8')) <= 32, 'Invalid SSID length')
    require(8 <= len(passphrase) <= 63 and all(32 <= ord(c) <= 126 for c in passphrase),
            'This setup path supports WPA2 Personal passphrases of 8–63 printable ASCII characters')
    return {'WiFi_1': {'ssid': ssid, 'password': passphrase}}


def validate_efi(efi, validator):
    config = plistlib.loads((efi / 'OC/config.plist').read_bytes())
    require((efi / 'BOOT/BOOTx64.efi').is_file() and (efi / 'OC/OpenCore.efi').is_file(), 'Bootloader missing')
    for section, directory, key in [('ACPI', 'ACPI', 'Path'), ('Kernel', 'Kexts', 'BundlePath')]:
        for entry in config[section]['Add']:
            if not entry['Enabled']:
                continue
            rel = Path(entry[key])
            require(not rel.is_absolute() and '..' not in rel.parts, 'Unsafe config path')
            path = efi / 'OC' / directory / rel
            require(path.exists(), 'Missing enabled component: ' + str(rel))
            if section == 'Kernel':
                info = plistlib.loads((path / entry['PlistPath']).read_bytes())
                if entry['ExecutablePath']:
                    binary = path / entry['ExecutablePath']
                    require(binary.is_file(), 'Kext executable missing: ' + str(rel))
                    require(binary.name == info['CFBundleExecutable'], 'Executable/plist mismatch')
    for entry in config['UEFI']['Drivers']:
        if entry['Enabled']:
            require((efi / 'OC/Drivers' / entry['Path']).is_file(), 'UEFI driver missing')
    identity = config['PlatformInfo']['Generic']
    require(re.fullmatch(r'[A-Z0-9]{12}', identity['SystemSerialNumber']) is not None, 'Serial missing')
    require(re.fullmatch(r'[A-Z0-9]{17}', identity['MLB']) is not None, 'MLB missing')
    uuid.UUID(identity['SystemUUID'])
    require(len(identity['ROM']) == 6 and identity['ROM'] != bytes(6), 'ROM missing')
    subprocess.run([str(validator), str(efi / 'OC/config.plist')], check=True)


def prepare_recovery(opencore, destination, supplied, work):
    helper = opencore / 'Utilities/macrecovery/macrecovery.py'
    if supplied:
        destination.mkdir()
        for name in ['BaseSystem.dmg', 'BaseSystem.chunklist']:
            require((supplied / name).is_file(), 'Recovery input missing ' + name)
            shutil.copyfile(supplied / name, destination / name)
    else:
        print('Downloading Apple Recovery; progress is saved in work/recovery-download.log', flush=True)
        with (work / 'recovery-download.log').open('w') as log:
            subprocess.run([sys.executable, str(helper), '-b', 'Mac-27AD2F918AE68F61',
                            '-m', '00000000000000000', '-os', 'latest', '-n', 'BaseSystem',
                            '-o', str(destination), 'download'], check=True, stdout=log, stderr=log)
    spec = importlib.util.spec_from_file_location('macrecovery', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with (work / 'recovery-verification.log').open('w') as log, contextlib.redirect_stdout(log):
        module.verify_image(str(destination / 'BaseSystem.dmg'), str(destination / 'BaseSystem.chunklist'))
    mount = work / 'recovery-mount'
    mount.mkdir()
    attached = False
    try:
        subprocess.run(['hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', str(mount),
                        str(destination / 'BaseSystem.dmg')], check=True, capture_output=True)
        attached = True
        version = plistlib.loads((mount / 'System/Library/CoreServices/SystemVersion.plist').read_bytes())
        require(version['ProductBuildVersion'] in {'25G83', '25G241'},
                'Apple supplied unqualified Recovery ' + version['ProductBuildVersion'] + '; do not boot this kit')
        return {k: version[k] for k in ['ProductVersion', 'ProductBuildVersion']}
    finally:
        if attached:
            subprocess.run(['hdiutil', 'detach', str(mount)], check=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hardware', required=True, type=Path, help='Output from collect-hardware.py on the target HP')
    parser.add_argument('--output', type=Path, default=HERE.parents[1] / 'build/HP-installer')
    parser.add_argument('--cache', type=Path, default=HERE.parents[1] / 'build/downloads')
    parser.add_argument('--network', choices=['wifi', 'wired'], default='wifi')
    parser.add_argument('--recovery', type=Path, help='Existing Apple BaseSystem.dmg and BaseSystem.chunklist directory')
    parser.add_argument('--efi-only', action='store_true', help='Skip Recovery: output cannot install macOS by itself')
    args = parser.parse_args()
    require(sys.flags.optimize == 0, 'Do not use Python -O/PYTHONOPTIMIZE; Apple chunklist verification uses assertions')
    require(platform.system() == 'Darwin', 'This build entry point requires macOS and Command Line Tools')
    require(os.geteuid() != 0, 'Build as your user, without sudo')
    subprocess.run(['xcrun', '--find', 'clang'], check=True, capture_output=True)
    report = json.loads((args.hardware / 'hardware.json').read_text())
    original = (args.hardware / 'DSDT.aml').read_bytes()
    check_hardware(report, original)
    out = args.output.resolve()
    require(not out.exists(), 'Output already exists; choose a new path')
    require(not str(out).startswith(('/Volumes/', '/Library/', '/System/')), 'Build on a local workspace, not a live volume/system path')
    out.mkdir(parents=True, mode=0o700)
    (out / 'INCOMPLETE.txt').write_text('Assembly is incomplete. Do not boot or copy this directory.\n')
    deps, work, usb = out / 'dependencies', out / 'work', out / 'USB'
    deps.mkdir(); work.mkdir(); usb.mkdir()
    for name in PINS:
        archive = fetch(name, args.cache.resolve())
        if name == 'iasl':
            shutil.copyfile(archive, work / 'iasl')
            (work / 'iasl').chmod(0o755)
        else:
            extract(archive, deps / name)
    oc = deps / 'opencore'
    efi = usb / 'EFI'
    (efi / 'BOOT').mkdir(parents=True)
    for d in ['ACPI', 'Kexts', 'Drivers']:
        (efi / 'OC' / d).mkdir(parents=True, exist_ok=True)
    for path in ['BOOT/BOOTx64.efi', 'OC/OpenCore.efi', 'OC/Drivers/OpenRuntime.efi',
                 'OC/Drivers/OpenHfsPlus.efi', 'OC/Drivers/ResetNvramEntry.efi']:
        shutil.copyfile(oc / 'X64/EFI' / path, efi / path)
    config = plistlib.loads((HERE / 'templates/recovery.plist').read_bytes())
    config['Kernel']['Add'] = [e for e in config['Kernel']['Add'] if e['Enabled']]
    config['ACPI']['Add'] = [e for e in config['ACPI']['Add'] if e['Enabled']]
    config['Misc']['Tools'] = []
    config['Misc']['Entries'] = []
    # Preserve the measured unlocked-CPU profile; never silently bypass its preflight.
    require(config['Kernel']['Quirks']['AppleXcpmCfgLock'] is False, 'Unexpected CPU profile')
    identity = config['PlatformInfo']['Generic']
    serial_tool = oc / 'Utilities/macserial/macserial'
    serial_tool.chmod(0o755)
    generated = subprocess.check_output([str(serial_tool), '-m', identity['SystemProductName'], '-n', '1'], text=True)
    match = re.search(r'\b([A-Z0-9]{12})\s*\|\s*([A-Z0-9]{17})\b', generated)
    require(match is not None, 'macserial could not generate this SMBIOS model')
    identity.update(SystemSerialNumber=match.group(1), MLB=match.group(2), SystemUUID=str(uuid.uuid4()).upper())
    identity['ROM'] = bytes([0x02]) + secrets.token_bytes(5)
    # NVRAM Add must overwrite a preceding trial's boot args/SIP on the target.
    for key in ['boot-args', 'csr-active-config']:
        if key not in config['NVRAM']['Delete'].setdefault(GUID, []):
            config['NVRAM']['Delete'][GUID].append(key)
    kexts = efi / 'OC/Kexts'
    for dependency, name in [('lilu', 'Lilu'), ('virtualsmc', 'VirtualSMC'), ('ps2', 'VoodooPS2Controller'),
                             ('i2c-release', 'VoodooI2C'), ('i2c-release', 'VoodooI2CHID'), ('itlwm', 'itlwm')]:
        matches = list((deps / dependency).rglob(name + '.kext'))
        matches = [p for p in matches if 'dSYM' not in p.parts]
        require(len(matches) == 1, 'Unexpected bundle archive layout: ' + name)
        shutil.copytree(matches[0], kexts / (name + '.kext'))
    shutil.rmtree(kexts / 'VoodooI2C.kext/Contents/PlugIns/VoodooInput.kext')
    for name in ['VoodooPS2Mouse', 'VoodooPS2Trackpad']:
        shutil.rmtree(kexts / 'VoodooPS2Controller.kext/Contents/PlugIns' / (name + '.kext'))
    p = kexts / 'USBMapHP8BDF.kext/Contents'
    p.mkdir(parents=True)
    shutil.copyfile(HERE / 'templates/USBMapHP8BDF.plist', p / 'Info.plist')
    build_input.build(deps, work / 'input', kexts)
    wifi_info = kexts / 'itlwm.kext/Contents/Info.plist'
    wifi = plistlib.loads(wifi_info.read_bytes())
    wifi['IOKitPersonalities']['itlwm']['WiFiConfig'] = {}
    if args.network == 'wifi':
        ssid = input('Installer Wi-Fi name (WPA2 Personal): ')
        password = getpass.getpass('Wi-Fi password (saved only in your private output): ')
        wifi['IOKitPersonalities']['itlwm']['WiFiConfig'] = wifi_configuration(ssid, password)
    wifi_info.write_bytes(plistlib.dumps(wifi))
    shutil.rmtree(wifi_info.parent / '_CodeSignature', ignore_errors=True)
    (efi / 'OC/ACPI/DSDT-HP8BDF-Pass1-I2C.aml').write_bytes(patch_dsdt(original))
    for source in sorted((HERE / 'acpi').glob('*.dsl')):
        subprocess.run([str(work / 'iasl'), '-p', str(efi / 'OC/ACPI' / source.stem), str(source)],
                       check=True, capture_output=True)
    (efi / 'OC/config.plist').write_bytes(plistlib.dumps(config))
    validator = oc / 'Utilities/ocvalidate/ocvalidate'
    validator.chmod(0o755)
    validate_efi(efi, validator)
    recovery = None if args.efi_only else prepare_recovery(oc, usb / 'com.apple.recovery.boot', args.recovery, work)
    # This manifest contains hashes, never credentials/serial values.
    manifest = {'schema': 1, 'profile': 'HP8BDF-F03-recovery', 'recovery': recovery,
                'fresh_install_tested': False, 'network': args.network,
                'sha256': {str(p.relative_to(usb)): digest(p) for p in sorted(usb.rglob('*')) if p.is_file()}}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (out / 'INCOMPLETE.txt').unlink()
    print('Prepared and structurally validated:', usb)
    print('Hardware boot/install qualification is still required. Read docs/INSTALL.md before copying to USB.')
    if args.efi_only:
        print('EFI ONLY: add a supported Apple installer/Recovery before use.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('Stopped:', error, file=sys.stderr)
        sys.exit(1)
