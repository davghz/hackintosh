# Configuration and deployment scope

`config/config.example.plist` is the restored working configuration with
SMBIOS serial, MLB, UUID and ROM removed, and password fields empty. It is a
reference for this exact hardware. Stale descriptive comments were updated
to name the current graphics version and input verification limits; operational
configuration values were preserved. It is **not ready to boot** and is not a
universal HP configuration. Generate your own identity; never reuse another
machine's serial, ROM or saved network configuration.

`config/components.json` lists its ACPI, kext and UEFI entries. Those referenced
binaries/tables are not all included. Preserve correct dependency order and
match every enabled entry to its actual file. The original laptop's full active
EFI is retained only in the local ignored backup.

For a new machine, first establish a recoverable USB OpenCore installation
for its measured hardware using the [OpenCore documentation](https://github.com/acidanthera/OpenCorePkg/blob/1.0.8/Docs/Configuration.tex).
Compare the device IDs, BIOS, ACPI and OS build with this project's status.
Keep a separate verified fallback USB/EFI before testing custom drivers. Do
not overwrite the only working EFI or disable exact-build guards to force a
match. Validate with `ocvalidate` from the same OpenCore release.

The repository does not supply a general macOS installer or an automatic
system-wide graphics deployment command. Building NootedGreenHP alone is
insufficient: its matching native graphics bundles, dependencies, cache
registration and private exact-image checks must be prepared and reviewed
on the target. Old project `manage_*` scripts in the private archive have
machine-specific paths and recovery hashes; do not run them on another system.

Change and verify one component at a time. After boot, verify actual attachment
and behavior: GPU compute/readback and cursor rendering, Wi-Fi discovery and
traffic, or battery values. Preserve a rollback before moving on. Full sleep is
currently unresolved and is not part of a claimed successful installation.

The CPU CFG utility has its own explicit install/cleanup process and two manual
reboots. Follow [that guide](CPU-UNLOCK.md); it does not belong in OpenCore's
permanent driver list and does not run from macOS.
