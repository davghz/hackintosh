# Contributing

Start with [current status](docs/STATUS.md) and the [component license map](licenses/README.md).
This project targets one HP 8BDF F.03 laptop. Keep device/build guards intact;
adding another model requires evidence for that model, not just a name change.

## Report a problem

Include the board ID, BIOS version, CPU/GPU PCI IDs, macOS build, component
version, the exact action that failed, and whether you can recover through your
fallback. Separate reproducible observations from a suspected cause. For display
issues, distinguish cursor artifacts, rendering corruption and full system sleep.

Sanitize reports before posting. Do not attach complete IORegistry, NVRAM,
system logs, EFI folders, Wi-Fi settings, screenshots with account information,
firmware-variable backups, serial/MLB/ROM/UUID values or passwords. Include the
smallest relevant redacted excerpt. Keep raw evidence locally.

## Make a source change

1. Put GPU/Wi-Fi changes in `drivers/*/overlay/`; dependency working trees are
   generated and not published. Battery and CPU tools are direct source.
2. Record the upstream revision, intended target and why the change is needed.
3. Run `python3 -m unittest discover -s tests -v`, rebuild the affected component
   using [BUILD.md](docs/BUILD.md), then stage and run `tools/audit-public.py`.
4. Describe the validation level: source review, host test, VM test, physical
   boot, or physical functional test. These are different forms of evidence.
5. Include rollback instructions and unresolved concerns in the change description.

No script should automatically reboot, sleep the machine, flash firmware, remove
hardware guards or install a new kernel extension merely as part of a build/test.
Do not claim a sleep fix based on screen blanking or power notifications alone.

Preserve upstream notices. Original contributions may use the scoped MIT grant;
changes derived from GPU or Wi-Fi code must retain those components' terms.
Do not introduce credentials, personal firmware payloads, Apple binaries,
generated dependency trees or unreviewed prebuilt drivers.
