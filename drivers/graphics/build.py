#!/usr/bin/env python3
"""Build the isolated HP NootedGreen source port; never install or enable it."""
import hashlib
import argparse
import json
import os
import plistlib
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent/'deps/XPS-IrisXe'
SRC = REPO/'src/NootedGreen'
SDK = REPO/'build/deps/MacKernelSDK'
LILU = REPO/'build/deps/Lilu.kext/Contents/Resources'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', default='build-v1.0.12')
args = parser.parse_args()
BUILD = ROOT/args.output
OBJ = BUILD/'objects'
KEXT = BUILD/'NootedGreenHP.kext'
NAME = 'NootedGreenHP'
BID = 'local.hp8bdf.NootedGreenHP'
VER = '1.0.12'
UNITS = ['DisplayMergeNub','DYLDPatches','Firmware','FirmwareADLP','HDMI',
         'IntelDPLinkTraining','kern_gen11','kern_genx','kern_green','kern_patcherplus','kern_start']
OBJ.mkdir(parents=True,exist_ok=True)
(KEXT/'Contents/MacOS').mkdir(parents=True,exist_ok=True)
flags=['-target','x86_64-apple-macos13','-mkernel','-nostdinc','-fno-builtin',
       '-fno-common','-fno-stack-protector','-mno-mmx','-mno-sse','-mno-sse2',
       '-mno-red-zone','-fno-vectorize','-fno-slp-vectorize',
       '-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-DAPPLE','-DNeXT',
       '-DDEBUG=1','-DAPPLE_KEXT_ASSERTIONS=1',f'-DPRODUCT_NAME={NAME}',f'-DMODULE_VERSION={VER}',
       '-isystem',str(SDK/'Headers'),'-I'+str(LILU),'-O2','-g']
cxx=['-std=gnu++17','-nostdinc++','-fno-exceptions','-fno-rtti','-fapple-kext',
     '-mllvm','-disable-atexit-based-global-dtor-lowering',
     '-Wno-deprecated-declarations','-Wno-inconsistent-missing-override','-Wno-unused-parameter']
log=(BUILD/'build.log').open('w')
def run(args):
    log.write(' '.join(map(str,args))+'\n');log.flush()
    subprocess.run(list(map(str,args)),stdout=log,stderr=log,check=True)

info=plistlib.loads((SRC/'Info.plist').read_bytes())
def substitute(value):
    if isinstance(value,str):
        for key,replacement in {'$(PRODUCT_BUNDLE_IDENTIFIER)':BID,'$(PRODUCT_NAME:rfc1034identifier)':NAME,
                                '$(PRODUCT_NAME)':NAME}.items():
            value=value.replace(key,replacement)
        return value
    if isinstance(value,dict): return {k:substitute(v) for k,v in value.items()}
    if isinstance(value,list): return [substitute(v) for v in value]
    return value
info=substitute(info)
for key,value in [('CFBundleIdentifier',BID),('CFBundleExecutable',NAME),('CFBundleName',NAME),
                  ('CFBundleVersion',VER),('CFBundleShortVersionString',VER)]:info[key]=value
# Dell display vendor/product IDs do not describe the HP panel.
info['IOKitPersonalities'].pop('DisplayAppleIDInjection',None)
personality=info['IOKitPersonalities'].pop('com.StezzaPilot.NootedGreen')
personality['CFBundleIdentifier']=BID
info['IOKitPersonalities'][BID]=personality
(KEXT/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
kmod=OBJ/'kmod_info.c'
kmod.write_text(f'''#include <mach/mach_types.h>
extern kern_return_t {NAME}_kern_start(kmod_info_t *, void *);
extern kern_return_t {NAME}_kern_stop(kmod_info_t *, void *);
__attribute__((visibility("default"))) KMOD_EXPLICIT_DECL({BID}, "{VER}", {NAME}_kern_start, {NAME}_kern_stop)
__private_extern__ kmod_start_func_t *_realmain = 0;
__private_extern__ kmod_stop_func_t *_antimain = 0;
__private_extern__ int _kext_apple_cc = __APPLE_CC__;
''')
run(['clang',*flags,'-c',kmod,'-o',OBJ/'kmod_info.o'])
objects=[OBJ/'kmod_info.o']
for unit in UNITS:
    print('Compiling',unit,flush=True)
    obj=OBJ/(unit+'.o');run(['clang++',*flags,*cxx,'-c',SRC/(unit+'.cpp'),'-o',obj]);objects.append(obj)
obj=OBJ/'plugin_start.o'
run(['clang++',*flags,*cxx,'-c',LILU/'Library/plugin_start.cpp','-o',obj]);objects.append(obj)
binary=KEXT/'Contents/MacOS'/NAME
run(['clang++','-arch','x86_64','-mkernel','-nostdlib','-static','-Xlinker','-kext',
     '-Xlinker','-export_dynamic','-mmacosx-version-min=13.0',*objects,
     SDK/'Library/x86_64/libkmod.a','-lcc_kext','-o',binary])
run(['codesign','--force','--sign','-',KEXT])
run(['codesign','--verify','--strict',KEXT])
raw=binary.read_bytes()
assert struct.unpack_from('<IIII',raw)==(0xFEEDFACF,0x01000007,3,11), 'Expected actual x86_64 MH_KEXT_BUNDLE'
source_diff=subprocess.check_output(['git','diff','--binary'],cwd=REPO)
(BUILD/'hp-source.patch').write_bytes(source_diff)
shutil.copy2(SRC/'kern_hp8bdf.hpp',BUILD/'kern_hp8bdf.hpp')
shutil.copy2(SRC/'kern_hp_dvmt.hpp',BUILD/'kern_hp_dvmt.hpp')
shutil.copy2(SRC/'kern_hp_cursor.hpp',BUILD/'kern_hp_cursor.hpp')
shutil.copy2(SRC/'kern_hp_sync.hpp',BUILD/'kern_hp_sync.hpp')
shutil.copy2(SRC/'kern_hp_sync_signatures.hpp',BUILD/'kern_hp_sync_signatures.hpp')
for name in ['kern_hp_fence.hpp','kern_hp_fence_signatures.hpp','kern_hp_nvram.hpp','kern_hp_linear.hpp','kern_hp_linear_signatures.hpp']:shutil.copy2(SRC/name,BUILD/name)
for name in ['LICENSE','NOTICE.md']:shutil.copy2(REPO/name,BUILD/name)
manifest={'status':'experimental build; not hardware validated; not enabled in EFI',
          'target':'HP 8BDF, physical 8086:A7A1 rev04, macOS Tahoe 26.7.1 (25G241)',
          'required_boot_arg':'-ngreenhp','binary_sha256':hashlib.sha256(raw).hexdigest(),
          'diagnostic_only_boot_arg':'-ngreenhpdiag',
          'bundle_identifier':BID,'version':VER,
          'repositories':{str(p.relative_to(ROOT.parent.parent)):subprocess.check_output(['git','rev-parse','HEAD'],cwd=p,text=True).strip()
                          for p in [REPO,SDK]},
          'lilu_debug_zip_sha256':hashlib.sha256((REPO/'build/deps/lilu.zip').read_bytes()).hexdigest(),
          'compiler':subprocess.check_output(['clang','--version'],text=True).strip(),
          'source_files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC.glob('*') if p.is_file()}}
(BUILD/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Built actual MH_KEXT_BUNDLE:',binary)
print('Native build and ad-hoc signature verified. Not loaded, installed, or enabled; hardware test still required.')
