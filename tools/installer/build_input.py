"""Rebuild the installer input drivers with the qualified Tahoe HID declarations.

Implementation sources are downloaded at pinned revisions; see downloads.json.
Only the SDK header overlay and HP metadata differ from upstream sources.
"""
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
from common import HERE, require


def source_root(deps, name):
    children = [p for p in (deps / name).iterdir() if p.is_dir()]
    require(len(children) == 1, 'Unexpected source archive layout: ' + name)
    return children[0]


def build(deps, work, kexts):
    sdk = source_root(deps, 'sdk')
    src = source_root(deps, 'i2c')
    gpio = source_root(deps, 'gpio')
    inp = source_root(deps, 'input')
    hid = source_root(deps, 'hid')
    hid_base = source_root(deps, 'i2c-hid-base')
    for parent in [src, hid_base]:
        shutil.copytree(gpio, parent / 'Dependencies/VoodooGPIO', dirs_exist_ok=True)
    hid_dest = hid_base / 'VoodooI2C Satellites/VoodooI2CHID'
    shutil.copytree(hid, hid_dest, dirs_exist_ok=True)
    overlay = work / 'include/IOKit/hid'
    overlay.mkdir(parents=True)
    header = (sdk / 'Headers/IOKit/hid/IOHIDDevice.h').read_text()
    anchor = '    virtual void stop( IOService * provider ) APPLE_KEXT_OVERRIDE;'
    require(header.count(anchor) == 1, 'SDK IOHIDDevice header differs')
    header = header.replace(anchor, anchor + '''
    // Existing Tahoe overrides: no added instance data or virtual slots.
    virtual bool willTerminate(IOService *provider, IOOptionBits options) APPLE_KEXT_OVERRIDE;
    virtual bool didTerminate(IOService *provider, IOOptionBits options, bool *defer) APPLE_KEXT_OVERRIDE;
    virtual IOReturn configureReport(IOReportChannelList *channels, IOReportConfigureAction action, void *result, void *destination) APPLE_KEXT_OVERRIDE;
    virtual IOReturn updateReport(IOReportChannelList *channels, IOReportUpdateAction action, void *result, void *destination) APPLE_KEXT_OVERRIDE;
''')
    (overlay / 'IOHIDDevice.h').write_text(header)
    units = list((src / 'VoodooI2C/VoodooI2C').rglob('*.cpp'))
    units += list((src / 'Multitouch Support').rglob('*.cpp'))
    units += [src / 'Dependencies/helpers.cpp', src / 'Dependencies/VoodooI2CACPIResourcesParser/VoodooI2CACPIResourcesParser.cpp']
    targets = [
        ('VoodooI2C', kexts / 'VoodooI2C.kext', units, inp, False),
        ('VoodooInput', kexts / 'VoodooPS2Controller.kext/Contents/PlugIns/VoodooInput.kext',
         sorted((inp / 'VoodooInput').rglob('*.cpp')), inp / 'VoodooInput', True),
        ('VoodooI2CHID', kexts / 'VoodooI2CHID.kext',
         sorted((hid_dest / 'VoodooI2CHID').rglob('*.cpp')), hid_dest / 'VoodooI2CHID', True),
    ]
    for name, bundle, sources, includes, use_overlay in targets:
        print('Building ' + name, flush=True)
        out = work / name
        out.mkdir()
        require(sources, 'No implementation source for ' + name)
        info = plistlib.loads((HERE / 'templates' / (name + '.plist')).read_bytes())
        (bundle / 'Contents/MacOS').mkdir(parents=True, exist_ok=True)
        (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))
        shutil.rmtree(bundle / 'Contents/_CodeSignature', ignore_errors=True)
        kmod = out / 'kmod.c'
        kmod.write_text('''#include <mach/mach_types.h>
extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
KMOD_EXPLICIT_DECL(%s, "%s", _start, _stop)
__private_extern__ kmod_start_func_t *_realmain = 0;
__private_extern__ kmod_stop_func_t *_antimain = 0;
__private_extern__ int _kext_apple_cc = __APPLE_CC__;
''' % (info['CFBundleIdentifier'], info['CFBundleVersion']))
        flags = ['-target', 'x86_64-apple-macos13', '-mkernel', '-nostdinc', '-fno-builtin',
                 '-fno-common', '-fno-stack-protector', '-mno-red-zone', '-mno-mmx', '-mno-sse',
                 '-mno-sse2', '-mno-avx', '-fno-vectorize', '-fno-slp-vectorize', '-DKERNEL',
                 '-DKERNEL_PRIVATE', '-DDRIVER_PRIVATE', '-DAPPLE', '-DNeXT', '-O2', '-g']
        if use_overlay:
            flags += ['-I', str(work / 'include')]
        flags += ['-isystem', str(sdk / 'Headers')]
        for directory in [includes, *sorted(p for p in includes.rglob('*') if p.is_dir())]:
            flags += ['-I', str(directory)]
        cxx = ['-std=gnu++14', '-nostdinc++', '-fno-exceptions', '-fno-rtti', '-fapple-kext',
               '-Werror', '-Wno-deprecated-declarations', '-Wno-inconsistent-missing-override',
               '-Wno-unused-parameter', '-Wno-macro-redefined', '-Wno-non-c-typedef-for-linkage']
        with (out / 'build.log').open('w') as log:
            def run(args):
                subprocess.run(list(map(str, args)), check=True, stdout=log, stderr=log)
            objects = []
            for i, unit in enumerate([kmod, *sources]):
                obj = out / ('%03d.o' % i)
                run(['xcrun', 'clang' if unit.suffix == '.c' else 'clang++', *flags,
                     *([] if unit.suffix == '.c' else cxx), '-c', unit, '-o', obj])
                objects.append(obj)
            binary = bundle / 'Contents/MacOS' / name
            run(['xcrun', 'clang++', '-arch', 'x86_64', '-mkernel', '-nostdlib', '-static',
                 '-Xlinker', '-kext', '-Xlinker', '-export_dynamic', '-mmacosx-version-min=13.0',
                 *objects, sdk / 'Library/x86_64/libkmod.a', '-lcc_kext', '-o', binary])
            require(struct.unpack_from('<IIII', binary.read_bytes()) == (0xfeedfacf, 0x1000007, 3, 11),
                    'Invalid kext Mach-O: ' + name)
            run(['codesign', '--force', '--sign', '-', bundle])
            run(['codesign', '--verify', '--strict', bundle])
    gp = kexts / 'VoodooI2C.kext/Contents/PlugIns/VoodooGPIO.kext'
    (gp / 'Contents/Info.plist').write_bytes((HERE / 'templates/VoodooGPIO.plist').read_bytes())
    shutil.rmtree(gp / 'Contents/_CodeSignature', ignore_errors=True)
    # Re-sign only modified families; retain upstream signatures elsewhere.
    families = [kexts / 'VoodooI2C.kext', kexts / 'VoodooPS2Controller.kext']
    bundles = [p for family in families for p in [family, *family.rglob('*.kext')]]
    for bundle in sorted(bundles, key=lambda p: len(p.parts), reverse=True):
        subprocess.run(['codesign', '--force', '--sign', '-', str(bundle)], check=True, capture_output=True)
