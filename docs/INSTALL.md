# Build an HP installer USB

This is an **experimental installer builder**, not a preinstalled macOS image
or a guarantee of a successful installation. It assembles a complete Recovery
EFI locally, generates a fresh boot identity, downloads Apple Recovery directly,
and checks the result. The new assembly has not yet completed a fresh physical
installation. Do not erase your only working system to test it.

The first supported build host is **Intel macOS with Python 3.9+ and Apple's
Command Line Tools**. The target HP must also be booted into a Linux live
session once to collect its firmware and check CFG Lock. Windows-only setup
and a one-click firmware unlock are not supplied. Those are real prerequisites,
not steps the download has already performed for you.

## Exact target

- HP Envy x360 15-fe0xxx, HP board **8BDF**, BIOS **F.03 / 08/29/2023**.
- Intel **i7-1355U**, all 12 logical CPUs online; the tested machine has 16 GB RAM.
- Intel GPU **8086:A7A1 / 103C:8BDF**; AX211 **8086:51F1 / 8086:0094**.
- Exact original DSDT fingerprint and measured CFG Lock clear on every CPU.
- Recovery **26.6.2 / 25G83** or **26.7.1 / 25G241**; installed baseline
  **Tahoe 26.7.1 / 25G241**, Darwin 25.6.0.

A model label alone is insufficient. The builder stops on mismatched firmware,
hardware, downloads or Recovery versions. Do not remove the checks or downgrade
firmware merely to make a mismatch pass. See [status](STATUS.md).

## What the builder handles

| Included in your locally generated USB | Source |
| --- | --- |
| OpenCore 1.0.8 DEBUG and its three UEFI drivers | Official release, pinned SHA-256 |
| Lilu, VirtualSMC, PS/2 keyboard, USB map | Pinned releases and HP metadata |
| HP polling trackpad, Tahoe HID termination correction | Pinned Voodoo sources, rebuilt locally |
| HP CPU/EC/RTC/USB/input ACPI tables | Supplied sources, compiled locally |
| DSDT pass-one and I2C0 resource corrections | Applied only to your matching original table |
| Unique MacBookPro16,2 serial/MLB/UUID/ROM | Generated locally; never the maintainer's identity |
| Installer networking | itlwm 2.3.0 with your WPA2 Personal network, or your supported wired adapter |
| Apple BaseSystem and chunklist | Fetched directly by OpenCore's macrecovery and verified |

**The Recovery profile intentionally uses basic, unaccelerated graphics.**
It does not install the custom GPU stack, native-menu Wi-Fi driver, battery
bridge or audio workaround into a new macOS system. Those remain separate
post-install engineering steps below. A successful Recovery boot therefore
does not mean every feature in the project's working-status table is enabled.

## 1. Download and check the target HP

Download the project source from [GitHub](https://github.com/davghz/hackintosh)
and extract it. All commands below start in the extracted `hackintosh` directory.
Keep AC power connected. Preserve your existing operating-system recovery route
and disk backups. Disable firmware Secure Boot before booting unsigned OpenCore;
the tools do not change that firmware setting for you.

On the **target HP**, start a Linux live session. Use Python 3.9+ and load the
read-only MSR interface:

```sh
sudo modprobe msr
sudo python3 tools/installer/collect-hardware.py /path/to/persistent/HP-hardware
```

Replace the destination with a new folder on persistent storage. The command
reads hardware state; it does not unlock the CPU or modify firmware. It saves
`hardware.json` and your original `DSDT.aml`. No serial number, network password
or CpuSetup variable is collected. Keep this folder private.

If CFG Lock is reported locked, complete the separately guarded
[CPU CFG Lock procedure](CPU-UNLOCK.md), including its VM test, cleanup and
two reboot verifications. Recollect into a new folder afterward. The original
unlock manager supports only its documented ESP layout; it is not a universal
firmware tool. An already-unlocked HP does not need another unlock.

Copy the resulting `HP-hardware` folder to your macOS build host.

## 2. Assemble the installer on macOS

Install Apple's Command Line Tools if `xcrun --find clang` is unavailable:

```sh
xcode-select --install
```

After that installation finishes, run:

```sh
python3 tools/installer/prepare-installer.py --hardware /path/to/HP-hardware
```

Alternatively, open `tools/installer/Prepare Installer.command` in Terminal;
it asks you to choose the hardware folder. If Finder blocks a downloaded
launcher, use the explicit Python command above rather than changing your
system's security policy.

The default network setup asks for your **WPA2 Personal** Wi-Fi name and
passphrase without echoing the passphrase. They are stored in your generated
itlwm configuration so Recovery can join without HeliPort. This is an installer
connection exposed as Ethernet, not the later native Wi-Fi menu. WPA3-only,
enterprise and captive-portal networks are not qualified; the passphrase must
use 8–63 printable ASCII characters. For a macOS-supported
wired USB Ethernet adapter, add `--network wired`; no Wi-Fi credentials are saved.
An arbitrary adapter or phone tether is not guaranteed to work in Recovery.

Allow several GB of local space and time for a roughly 1 GB Recovery download.
The builder fetches pinned dependencies, compiles the input/ACPI fixes, generates
your identity, runs matching `ocvalidate`, verifies Apple's chunklist and checks
Recovery's build. Detailed logs are under the output's `work/` directory.

Default output: `build/HP-installer/`. It refuses to replace an existing output;
use `--output build/HP-installer-2` for another build. Downloads are cached and
rechecked. `--recovery /path/to/folder` accepts an existing Apple BaseSystem.dmg
and BaseSystem.chunklist pair and performs the same verification. `--efi-only`
is for developers: its result cannot install macOS by itself.

**Do not share your generated output.** It contains your identity, firmware
table and, when selected, Wi-Fi password. Share the reviewed source download.
`INCOMPLETE.txt` means assembly failed; do not copy that output to a boot USB.
If Apple starts serving an unqualified build, assembly deliberately stops.

## 3. Copy to a spare USB and verify

Use a **spare USB of at least 8 GB**. Keep the known-working boot/recovery USB.
If needed, prepare the spare in Disk Utility with a FAT32 (MS-DOS FAT) volume
and GUID partition map. Erasing destroys that selected USB's contents: confirm
the device identity in Disk Utility. The project scripts never format disks.

With the prepared volume mounted, replace `HPINSTALL` with its actual name:

```sh
python3 tools/installer/verify-kit.py build/HP-installer
python3 tools/installer/verify-kit.py build/HP-installer --copy-to /Volumes/HPINSTALL
```

The copy tool requires the root of an **external FAT32** volume and refuses
existing EFI or Recovery directories. It stages files first, checks every byte,
then exposes EFI last and reads everything back again. It neither installs
OpenCore internally nor replaces another working EFI. Eject the USB in Finder.

The resulting USB root contains:

```text
EFI/BOOT/BOOTx64.efi
EFI/OC/OpenCore.efi
EFI/OC/config.plist
EFI/OC/ACPI/...
EFI/OC/Kexts/...
EFI/OC/Drivers/...
com.apple.recovery.boot/BaseSystem.dmg
com.apple.recovery.boot/BaseSystem.chunklist
```

## 4. First boot and installation

1. Connect AC power and the installer USB to the checked HP. Keep the lid open.
2. Power on and use **Esc, then F9** for HP's boot menu. Choose the USB's UEFI
   entry. If Recovery is hidden in OpenCore, press **Space** to show auxiliary
   entries, then choose the USB Recovery entry.
3. First confirm Recovery reaches its desktop, keyboard/trackpad respond, and
   networking works. Its display may report 7 MB/basic graphics. That is expected
   for this profile. Do not mistake it for a failed post-install GPU driver.
4. Only after that check, choose your intended installation volume. For a new,
   empty destination, Apple's installer expects an APFS volume on a GUID disk.
   Do not erase an existing OS or recovery partition just to test the kit.
5. Start installation. Keep booting through the USB across restarts. Select
   **macOS Installer** on the destination while it exists; afterward choose the
   installed macOS volume. The multiple restart stages are normal.
6. Before adding custom drivers, run `sw_vers` and confirm **26.7.1 / 25G241**.
   Recovery's own 25G83 version does not guarantee the version Apple's online
   installer will offer. Stop before post-install patches if the installed
   build differs.

If the screen stops, photograph the first panic lines and backtrace. OpenCore
logs are saved on the USB. Preserve them privately; boot logs can contain
identifiers. Return to the known-working USB if needed. See
[troubleshooting](TROUBLESHOOTING.md). Do not repeatedly force changes to CPU,
memory, GPU and input settings together.

## 5. After macOS installs: limits and next work

This builder gets the **Recovery/installation stage** assembled. It is not yet
an automated reproduction of the maintainer's complete post-install system:

- GPU acceleration needs the exact Apple TGL bundles, HookCase, the modified
  Metal/shader components, HP patches and kernel-cache registration. Apple
  bundles are not included, and the project does not currently provide a
  portable automatic GPU deployment command. Building NootedGreenHP alone
  does not enable acceleration. See [configuration](CONFIGURATION.md) and
  [source builds](BUILD.md).
- Native-menu Wi-Fi and the battery bridge have source/build recipes, but are
  not automatically enabled by the Recovery EFI. Keep installer networking
  available while working through post-install changes.
- Full sleep/wake, built-in speakers and brightness keys remain unresolved.
  Bluetooth and touchscreen operation are not qualified. Do not close the lid
  or rely on sleep during installation; a responsive display is not a sleep test.
- The CPU unlock, first-boot identity and target firmware checks cannot be
  replaced with another person's files.

For these reasons, this release must **not** be advertised as “download and
immediately get a fully working Mac.” The next qualification is a boot of the
newly assembled kit, followed by a clean install on expendable storage and
another matching HP. No such result is claimed by automated build verification.

References: [OpenCore installer guidance](https://dortania.github.io/OpenCore-Install-Guide/installer-guide/),
[OpenCore 1.0.8 configuration](https://github.com/acidanthera/OpenCorePkg/blob/1.0.8/Docs/Configuration.tex),
[macrecovery](https://github.com/acidanthera/OpenCorePkg/tree/1.0.8/Utilities/macrecovery),
and [local provenance](../tools/installer/ACPI-PROVENANCE.md).
