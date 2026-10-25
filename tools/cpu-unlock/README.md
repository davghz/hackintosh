# HP F.03 CPU CFG Lock utility

Read the complete [CPU unlock guide](../../docs/CPU-UNLOCK.md) before building
or registering the driver. It targets HP board 8BDF, BIOS F.03 dated 08/29/2023;
it is not a general Intel unlocker.

The original EFI driver, Linux management script and OVMF fixture are preserved.
The public packaging adds a local-only baseline generator and an explicit
fixture build rule. Your own exact binary must pass the VM fixture before
registration, and actual success requires the documented two reboots and MSR
checks on every online logical CPU. The status reader enumerates available MSR
devices; manually check that none of the expected 12 CPUs is missing.

No personal expected payload or prebuilt unlock EFI is distributed. Never
publish the generated baseline, `expected.h`, installation record or binary.
`Fixture.efi` is VM-only and must not be placed on a physical laptop's ESP.
The original utility is under the scoped [MIT license](../../LICENSE).
