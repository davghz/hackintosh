#!/usr/bin/env python3
"""Build only an isolated HP AX211 native Tahoe candidate; never install/load it."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import struct
import subprocess
import zlib

ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent.parent/'deps/itlwm'
BUILD=ROOT/'build'
SDK=ROOT.parent.parent/'deps/XPS-IrisXe/build/deps/MacKernelSDK'
SOURCE_COMMIT='738d4c61b5a64433b27c1ab09dba94916ab77d8d'
SDK_COMMIT='3f750085caa17ec3a7880f11c11bf4f48cd6a164'
NAME='AirportItlwmHP'
BID='local.hp8bdf.AirportItlwm'
VERSION='0.1.4'
def output(args,cwd=None): return subprocess.check_output(args,cwd=cwd,text=True).strip()
assert output(['git','rev-parse','HEAD'],SRC)==SOURCE_COMMIT
assert output(['git','rev-parse','HEAD'],SDK)==SDK_COMMIT
assert not output(['git','status','--porcelain'],SDK)
(BUILD/'objects').mkdir(parents=True,exist_ok=True)
(BUILD/'logs').mkdir(exist_ok=True)
kext=BUILD/(NAME+'.kext');(kext/'Contents/MacOS').mkdir(parents=True,exist_ok=True)
pbx=json.loads(output(['plutil','-convert','json','-o','-',str(SRC/'itlwm.xcodeproj/project.pbxproj')]))
objects=pbx['objects'];parents={c:k for k,v in objects.items() for c in v.get('children',[])}
def refpath(key):
    value=objects[key];path=Path(value.get('path',''))
    if value.get('sourceTree')=='SOURCE_ROOT':return path
    return (refpath(parents[key]) if key in parents else Path())/path
target=next(v for v in objects.values() if v.get('isa')=='PBXNativeTarget' and v.get('name')=='AirportItlwm-Tahoe')
original=[];empty_entries=0
for key in target['buildPhases']:
    phase=objects[key]
    if phase['isa']=='PBXSourcesBuildPhase':
        for f in phase['files']:
            if 'fileRef' not in objects[f]:empty_entries+=1;continue
            original.append(refpath(objects[f]['fileRef']))
excluded=[p for p in original if str(p).startswith(('itlwm/hal_iwm/','itlwm/hal_iwn/'))]
units=[p for p in original if p not in excluded]
units.append(Path('include/HPWifiDiag.cpp'))
assert len(original)==74 and empty_entries==1
assert all((SRC/p).is_file() for p in units if p!=Path('include/FwBinary.cpp'))
# Preserve all twelve pinned IWX ucodes; the fitted AX211 additionally requires
# this PNVM resource. It is already in this source commit and byte-identical to
# the working original itlwm binary. Fail before compilation if absent/changed.
REQUIRED_PNVM_NAME='iwlwifi-so-a0-gf-a0.pnvm'
REQUIRED_PNVM_SHA256='aedadb2c9e6ef9019902837d52c5ceb191603db8ea0a34d522c164250d1e02e9'
def select_firmware_files(source):
    iwx=(source/'itlwm/hal_iwx/ItlIwx.cpp').read_text()
    referenced=sorted(set(re.findall(r'\.fwname\s*=\s*"([^"]+)"',iwx)))
    ucodes=[source/'itlwm/firmware'/name for name in referenced if (source/'itlwm/firmware'/name).is_file()]
    assert len(ucodes)==12 and all(p.suffix=='.ucode' for p in ucodes)
    pnvm=source/'itlwm/firmware'/REQUIRED_PNVM_NAME
    if not pnvm.is_file():
        raise FileNotFoundError('Required fitted AX211 PNVM resource missing: '+REQUIRED_PNVM_NAME)
    if hashlib.sha256(pnvm.read_bytes()).hexdigest()!=REQUIRED_PNVM_SHA256:
        raise ValueError('Required fitted AX211 PNVM resource hash mismatch')
    return referenced,ucodes+[pnvm]
referenced,firmwares=select_firmware_files(SRC)
assert len(firmwares)==13
fwsource=BUILD/'FwBinary.cpp'
with fwsource.open('w') as f:
    f.write('// Generated from unmodified Intel firmware retained in the pinned source.\n#include "FwData.h"\n')
    for i,p in enumerate(firmwares):
        data=zlib.compress(p.read_bytes())
        f.write(f'static const unsigned char fw_{i}[]={{\n')
        for j in range(0,len(data),24):f.write(','.join(hex(x) for x in data[j:j+24])+',\n')
        f.write('};\n')
    f.write('const struct FwDesc fwList[]={\n')
    for i,p in enumerate(firmwares):f.write('{"'+p.name+f'",fw_{i},sizeof(fw_{i})'+'},\n')
    f.write('};\nconst int fwNumber=sizeof(fwList)/sizeof(fwList[0]);\n')
flags=['-target','x86_64-apple-macos10.15','-mkernel','-nostdinc','-fno-builtin','-fno-common',
       '-fno-stack-protector','-mno-mmx','-mno-sse','-mno-sse2','-mno-red-zone',
       '-fno-vectorize','-fno-slp-vectorize','-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE',
       '-DAPPLE','-DNeXT','-DAIRPORT_WCL','-DAIRPORT_VTD','-D__IO80211_TARGET=__MAC_26_0',
       '-DAIRPORT','-D__PRIVATE_SPI__','-DIO80211FAMILY_V2','-DIEEE80211_STA_ONLY',
       '-DITLWM_VERSION="2.4.0"','-DGIT_COMMIT="-hp0.1.4"',
       '-isystem',str(SDK/'Headers'),'-O1','-g']
# Xcode's source header maps resolve quoted leaf names. Reproduce their source
# directories without letting these directories override angle-bracket SDK headers.
for path in sorted({p.parent for p in SRC.rglob('*') if p.suffix in ('.h','.hpp')}):
    flags+=['-iquote',str(path)]
for path in ['itl80211/openbsd','itl80211','include']:
    flags+=['-I',str(SRC/path)]
cxx=['-x','c++','-std=gnu++14','-nostdinc++','-fno-exceptions','-fno-rtti','-fapple-kext',
     '-include',str(SRC/'itlwm/PrivateSPI.pch'),'-mllvm','-disable-atexit-based-global-dtor-lowering',
     '-Wno-deprecated-declarations','-Wno-inconsistent-missing-override','-Wno-deprecated-register']
jobs=[]
for p in units:
    source=fwsource if p==Path('include/FwBinary.cpp') else SRC/p
    name=str(p).replace('/','__')
    obj=BUILD/'objects'/(name+'.o')
    cmd=['clang++',*flags,*cxx,'-c',str(source),'-o',str(obj)]
    jobs.append((name,cmd,obj))
def compile_one(job):
    name,cmd,obj=job
    log=BUILD/'logs'/(name+'.log')
    with log.open('w') as f:
        f.write(' '.join(cmd)+'\n');f.flush()
        cp=subprocess.run(cmd,stdout=f,stderr=f,cwd=SRC)
    if cp.returncode:raise RuntimeError('Compilation failed: '+name+'; see '+str(log))
    print('Compiled '+name,flush=True)
    return obj
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    compiled=list(pool.map(compile_one,jobs))
kmod=BUILD/'objects/kmod_info.c'
kmod.write_text(f'''#include <mach/mach_types.h>
extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
KMOD_EXPLICIT_DECL({BID}, "{VERSION}", _start, _stop)
__private_extern__ kmod_start_func_t *_realmain = 0;
__private_extern__ kmod_stop_func_t *_antimain = 0;
__private_extern__ int _kext_apple_cc = __APPLE_CC__;
''')
subprocess.run(['clang',*flags,'-c',str(kmod),'-o',str(kmod.with_suffix('.o'))],check=True)
compiled.append(kmod.with_suffix('.o'))
binary=kext/'Contents/MacOS'/NAME
link=['clang++','-arch','x86_64','-mkernel','-nostdlib','-static','-Xlinker','-kext',
      '-Xlinker','-export_dynamic','-mmacosx-version-min=10.15',*map(str,compiled),
      str(SDK/'Library/x86_64/libkmod.a'),'-lcc_kext','-o',str(binary)]
with (BUILD/'link.log').open('w') as f:subprocess.run(link,stdout=f,stderr=f,check=True)
info=plistlib.loads((SRC/'AirportItlwm/WCL/Info.plist').read_bytes())
for key,value in {'CFBundleDevelopmentRegion':'en','CFBundleExecutable':NAME,'CFBundleIdentifier':BID,
                  'CFBundleName':NAME,'CFBundlePackageType':'KEXT','CFBundleVersion':VERSION,'CFBundleShortVersionString':VERSION}.items():info[key]=value
for personality in info['IOKitPersonalities'].values():personality['CFBundleIdentifier']=BID
p=info['IOKitPersonalities']['itlwm'];p.pop('IOPCIMatch')
p['IOPCIPrimaryMatch']='0x51F18086';p['IOPCISecondaryMatch']='0x00948086'
info['HPSourceCommit']=SOURCE_COMMIT
(kext/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
subprocess.run(['codesign','--force','--sign','-',str(kext)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(kext)],check=True)
raw=binary.read_bytes();assert struct.unpack_from('<IIII',raw)==(0xFEEDFACF,0x01000007,3,11)
manifest={'status':'source-built candidate only; never loaded or installed; runtime qualification pending',
    'name':NAME,'bundle_identifier':BID,'version':VERSION,'source_repository':'https://github.com/laobamac/itlwm',
    'source_commit':SOURCE_COMMIT,'sdk_commit':SDK_COMMIT,'compiler':output(['clang','--version']),
    'upstream_tahoe_units':list(map(str,original)),'excluded_legacy_transport_units':list(map(str,excluded)),
    'compiled_units':list(map(str,units)),'firmware_selection':'all twelve pinned IWX ucodes unchanged plus only fitted AX211 iwlwifi-so-a0-gf-a0.pnvm; selected so-a0-gf-a0-68.ucode proven on prior boots',
    'firmware_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in firmwares},
    'upstream_missing_nonHP_firmware_names':[n for n in referenced if not (SRC/'itlwm/firmware'/n).exists()],
    'binary_sha256':hashlib.sha256(raw).hexdigest(),'binary_bytes':len(raw),'build_jobs':4,'diagnostic_only':False,'functional_change':'Restore required fitted AX211 PNVM in embedded resource table; hardware qualification pending','diagnostic_stage_map_sha256':hashlib.sha256((ROOT/'stage-map.json').read_bytes()).hexdigest(),
    'trace_schema_sha256':hashlib.sha256((ROOT/'trace-schema.json').read_bytes()).hexdigest(),
    'required_pnvm':{'name':REQUIRED_PNVM_NAME,'sha256':REQUIRED_PNVM_SHA256,'origin':'same pinned source commit and working original itlwm binary'},
    'local_changes':'HP0.1.4 restores required PNVM in generated firmware table and updates bundle/root/service version labels, preserving all runtime transport source, ucodes, trace semantics, timeouts, retries and hardware/control operations from0.1.3. HP0.1.3 adds a fixed64-slot numeric startup command/IRQ/RX/error trace, first-two synchronous-command metadata, release/acquire slot publication, safe first-failure/cleanup snapshot, and eight-line progress console limit. No new hardware reads, timeouts, retries, cache changes, or control operations. HP0.1.2 adds nested firmware-wait stages, whitelisted firmware/hardware identity, atomic startup IRQ counters and existing timeout-status values to persistent root properties, preserving original results and hardware operations. Exact fitted AX211 PCI/subsystem and Darwin25 probe gate; initialize MSI capability offsets; guard HAL/workqueue allocations and release workqueue on failed wrapper start; define successful ether_ifattach return; omit IWM/IWN units/firmware; replace five IWM RSSI constant references with identical IWX constant; expose non-identifying selected firmware/build diagnostics; custom manual target.'}
(BUILD/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(BUILD/'hp-source.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=SRC))
shutil.copy2(SRC/'LICENSE',BUILD/'LICENSE-upstream')
shutil.copy2(SRC/'iwlwifi-firmware-license',BUILD/'LICENSE-Intel-firmware')
print('Built and signed source candidate: '+str(binary))
