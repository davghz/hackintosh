# CPU CFG Lock: the HP 8BDF F.03 procedure

This is the CPU unlock developed for this project: disabling **CFG Lock**,
verified by reading **MSR 0xE2 bit 15**. It is not multiplier overclocking,
a CPU-generation spoof, or a repair for graphics or sleep.

The original laptop completed the two-reboot procedure: every one of its
12 logical CPUs read `0x0000000074000008` (bit 15 = 0), the saved CFG byte was
0, and every other byte of the 961-byte CpuSetup payload was unchanged.
Temporary driver registration and the arm marker were removed. That already
unlocked machine does not need this procedure repeated.

## Exact supported target

| Guard | Required value |
| --- | --- |
| Board vendor / board | HP / 8BDF |
| BIOS version / date | F.03 / 08/29/2023 |
| CpuSetup GUID | B08F97FF-E6E8-4193-A997-5E9E9B0ADB32 |
| Payload size / attributes | 961 bytes / 7 |
| CFG Lock payload offset | 0x43, one byte, 1 → 0 |
| Original installer ESP | `/dev/nvme0n1p1`, vfat, mounted at `/boot/efi` |

The offset is relative to the **payload**, after the four attribute bytes in
a Linux efivarfs file. It is not an offset in a BIOS flash image.

The installed F.03 SetupUtility IFR established this mapping. Before adapting
the procedure to another firmware, establish its variable layout independently.
Do not change the identity checks to force a different board, BIOS or layout
through. Even another HP laptop requires its own analysis. Wrong firmware
settings can prevent boot; retain your normal boot/recovery route and local
backups before registering an EFI driver.

## Why an early driver

On the original machine both Linux runtime writes and normal EFI-shell writes
were rejected. The custom `EarlyCfg.efi` boot-services driver ran through
firmware `Driver####` / `DriverOrder` early enough for the constrained write.
That timing is an observation on F.03, not a guarantee for other firmware.
UEFI defines the separate driver and boot-option ordering in its
[Boot Manager specification](https://uefi.org/specs/UEFI/2.11/03_Boot_Manager.html).

The driver consumes a one-shot arm file, requires the exact identity and a full
match to the user's captured CpuSetup baseline, changes only byte 0x43,
then reads back the entire variable. It returns without rebooting. It does not
flash firmware code or write MSRs. Do not place the VM-only `Fixture.efi` on a
physical machine's ESP.

## 1. Prepare on Linux, directly on the supported HP

The installer and hardware verifier require Linux; do not run them from macOS
or a VM. Use a persistent working directory so the baseline and installation
record survive both reboots. The original build used GNU-EFI 4.0.0 and GCC.
The Makefile expects GNU-EFI headers in `/usr/include/efi` and its linker
script/startup object in `/usr/lib`. Adjust build search paths for your distro
if necessary; the board, variable and ESP checks remain mandatory.

Required tools: Python 3.9+, GCC, GNU make/binutils, GNU-EFI, QEMU x86_64, OVMF,
dosfstools, mtools, efibootmgr, findmnt, and the Linux `msr` module. The VM test
expects `/usr/share/OVMF/OVMF_CODE_4M.fd` and `OVMF_VARS_4M.fd`.

Inspect board and ESP identity first:

```sh
cat /sys/class/dmi/id/board_vendor /sys/class/dmi/id/board_name
cat /sys/class/dmi/id/bios_version /sys/class/dmi/id/bios_date
findmnt -T /boot/efi
```

The existing installer deliberately refuses any ESP other than the one listed
above. Do not mount or format an unrelated partition to satisfy it. A different
layout needs a separately reviewed installer adaptation. Firmware Secure Boot
must already be disabled for this unsigned driver; the tool will not disable it.

First check whether an unlock is needed, from the repository root:

```sh
sudo modprobe msr
sudo python3 tools/cpu-unlock/read-cfg-lock.py
```

Require a readable result for every online logical CPU (12 on the tested HP).
If bit 15 is already 0 everywhere, stop here. The checker prints the state;
an exit status of zero by itself does not mean unlocked.

## 2. Generate your private baseline and test your exact binary

```sh
cd tools/cpu-unlock/early-cfg
sudo python3 prepare_baseline.py
sudo chown "$(id -u):$(id -g)" expected.h ../CpuSetup-original.efivar
make EarlyCfg.efi Fixture.efi
python3 run_vm_test.py
```

`prepare_baseline.py` reads firmware state and writes only local build inputs.
It checks identity, size, attributes and the initial CFG byte. It refuses to
replace existing inputs. Your complete original efivar and generated `expected.h`
remain private and Git-ignored. No original machine's payload or prebuilt unlock
binary is distributed: each build must match that user's exact baseline.

The OVMF fixture tests single-byte success, one-shot behavior, firmware write
protection, baseline mismatch, attribute mismatch, identity mismatch and an
unarmed invocation. It records the SHA-256 of the binary it tested. **All cases
must pass for that exact binary.** VM tests do not reproduce HP firmware's
variable-lock timing. Changing the binary invalidates the recorded test result.

## 3. Register once and reboot manually

```sh
sudo python3 manage.py install
```

This command copies only `EarlyCfg.efi` to `EFI/CFGUnlock`, registers a temporary
firmware driver entry, saves a private installation record, checks Boot variables
were preserved, and creates the arm marker. It does not reboot. Keep
`installation.json`, the original baseline and this working directory intact.
If installation reports an error, inspect the saved state before rebooting.

Save your work and reboot normally, then return to the same Linux environment.

## 4. Inspect, remove registration, then reboot a second time

```sh
sudo python3 manage.py status
```

Interpret the result file at `/boot/efi/EFI/CFGUnlock/early-cfg-result.txt`:

| Result | Meaning |
| --- | --- |
| `READBACK EXACT` | The requested setting was stored; hardware unlock is not yet proved |
| `WRITE_PROTECTED` / status ending `0008` | Firmware rejected this attempt; do not keep rearming |
| `ABORT` | A guard failed; retain evidence and stop |
| Missing result / token still present | Execution was not established; no success claim |
| `READBACK MISMATCH` | Unexpected state; stop and inspect without retrying |

After collecting the result, remove the temporary registration:

```sh
sudo python3 manage.py remove
```

Removal checks the recorded driver entry before deleting it and removes the arm
marker. It does **not** restore CFG Lock; an accepted setting persists. Do not
delete every Driver entry or overwrite BootOrder. The original experiment began
with no DriverOrder; if existing driver entries are present, verify they remain.

After a successful exact readback and cleanup, reboot manually a second time.
The setting can be stored after CPU initialization on the first boot, which is
why a second boot is needed. Then run `manage.py status` again. Require
CpuSetup[0x43] = 0, MSR bit 15 = 0 on every online logical CPU, no arm marker,
and no remaining experiment driver registration. **Only this is hardware
confirmation.** Preserve results locally.

With CFG Lock verified disabled, this project's OpenCore configuration uses
`Kernel → Quirks → AppleXcpmCfgLock = False`. BIOS defaults or a firmware update
may reset the state; recheck afterward. If unlocking fails, do not copy that
False value as if unlocking succeeded. OpenCore's workaround and firmware
unlocking are separate approaches; see its
[configuration documentation](https://github.com/acidanthera/OpenCorePkg/blob/1.0.8/Docs/Configuration.tex).

There is no tested automatic relock operation in this tool. Cleanup removes
registration only. Do not flash the original project's partial SPI analysis dump
or restore somebody else's CpuSetup. Neither is a recovery procedure.

## Publication validation versus hardware history

The original production utility passed its OVMF tests and the original HP
completed both physical reboots. The public packaging retains the driver,
installer and fixture sources, adds a local-baseline generator, and adds the
missing explicit `Fixture.efi` Makefile rule. Packaging checks exercise the
generator without firmware access. A new user's regenerated binary still needs
the full VM test and both hardware verification stages above.
