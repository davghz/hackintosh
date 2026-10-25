#!/usr/bin/env python3
"""Build only in this directory. Never installs, loads or changes boot config."""
import hashlib, json, pathlib, plistlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent
SDK = ROOT.parent.parent/'deps/XPS-IrisXe/build/deps/MacKernelSDK'
OUT = ROOT / 'build'
KEXT = OUT / 'HPBAT1Bridge.kext'
BIN = KEXT / 'Contents/MacOS/HPBAT1Bridge'
OUT.mkdir(exist_ok=True)
BIN.parent.mkdir(parents=True, exist_ok=True)

def run(args):
    subprocess.run([str(a) for a in args], check=True)

flags = ['-target','x86_64-apple-macos13','-mkernel','-nostdinc','-fno-builtin',
         '-fno-common','-fno-stack-protector','-mno-mmx','-mno-sse','-mno-sse2',
         '-mno-red-zone','-fno-vectorize','-fno-slp-vectorize','-DKERNEL',
         '-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-DAPPLE','-DNeXT',
         '-isystem',str(SDK/'Headers'),'-O2','-g']
cxx = ['-std=gnu++17','-nostdinc++','-fno-exceptions','-fno-rtti','-fapple-kext',
       '-mllvm','-disable-atexit-based-global-dtor-lowering',
       '-Wno-deprecated-declarations','-Wno-inconsistent-missing-override',
       '-Wall','-Wextra','-Werror']
mod = OUT/'kmod_info.c'
mod.write_text('''#include <mach/mach_types.h>
extern kern_return_t HPBAT1Bridge_kern_start(kmod_info_t *, void *);
extern kern_return_t HPBAT1Bridge_kern_stop(kmod_info_t *, void *);
extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
KMOD_EXPLICIT_DECL(local.hp8bdf.HPBAT1Bridge, "0.1.2", _start, _stop)
__private_extern__ kmod_start_func_t *_realmain = HPBAT1Bridge_kern_start;
__private_extern__ kmod_stop_func_t *_antimain = HPBAT1Bridge_kern_stop;
__private_extern__ int _kext_apple_cc = __APPLE_CC__;
''')
run(['clang',*flags,'-c',mod,'-o',OUT/'kmod_info.o'])
run(['clang++',*flags,*cxx,'-c',ROOT/'HPBAT1Bridge.cpp','-o',OUT/'HPBAT1Bridge.o'])
run(['clang++','-arch','x86_64','-mkernel','-nostdlib','-static','-Xlinker','-kext',
     '-Xlinker','-export_dynamic','-mmacosx-version-min=13.0',
     OUT/'kmod_info.o',OUT/'HPBAT1Bridge.o',SDK/'Library/x86_64/libkmod.a',
     '-lcc_kext','-o',BIN])
info = {
    'CFBundleDevelopmentRegion':'English','CFBundleExecutable':'HPBAT1Bridge',
    'CFBundleIdentifier':'local.hp8bdf.HPBAT1Bridge','CFBundleInfoDictionaryVersion':'6.0',
    'CFBundleName':'HPBAT1Bridge','CFBundlePackageType':'KEXT',
    'CFBundleShortVersionString':'0.1.2','CFBundleVersion':'0.1.2',
    'OSBundleRequired':'Root',
    'OSBundleLibraries':{'com.apple.kpi.iokit':'8.0.0','com.apple.kpi.libkern':'8.0.0',
                         'com.apple.kpi.mach':'8.0.0','com.apple.iokit.IOACPIFamily':'1.4.0'},
    'IOKitPersonalities':{'HP 8BDF BAT1 read-only bridge':{
        'CFBundleIdentifier':'local.hp8bdf.HPBAT1Bridge','IOClass':'HPBAT1Bridge',
        'IOProviderClass':'IOACPIPlatformDevice','IONameMatch':'PNP0C0A'}}
}
(KEXT/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
run(['codesign','--force','--sign','-',KEXT])
run(['codesign','--verify','--strict',KEXT])
fragment = {'Kernel':{'Add':[{'Arch':'x86_64','BundlePath':'HPBAT1Bridge.kext',
    'Comment':'STAGED ONLY: custom HP 8BDF ACPI battery bridge, requires separate review/boot',
    'Enabled':False,'ExecutablePath':'Contents/MacOS/HPBAT1Bridge',
    'MinKernel':'25.6.0','MaxKernel':'25.6.99','PlistPath':'Contents/Info.plist'}]}}
(ROOT/'disabled-opencore-fragment.plist').write_bytes(plistlib.dumps(fragment))
files = [ROOT/'BatteryModel.hpp',ROOT/'HPBAT1Bridge.cpp',ROOT/'build.py',BIN,KEXT/'Contents/Info.plist']
manifest = {'built_only':True,'hardware_runtime_tested':False,'build_guard':'25G241',
    'board_guard':'HDAS PCI8086:51ca subsystem103c:8bdf; BAT1 under _SB.PC00.LPCB',
    'compiler':subprocess.check_output(['clang','--version'],text=True).strip(),
    'sdk':str(SDK),'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(ROOT/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Built only:',KEXT)
