# How the pieces fit together

The project combines firmware configuration, OpenCore, ACPI/device matching,
kernel extensions and userspace GPU support. Success at one layer does not
prove all the others work.

| Layer | Responsibility | Important boundary |
| --- | --- | --- |
| EarlyCfg one-shot EFI driver | Store one validated CpuSetup byte before firmware variable locking | Runs from firmware DriverOrder, outside macOS; removed after the experiment |
| OpenCore configuration | CPU compatibility, ACPI selection, dependency loading and device properties | Sanitized example requires matching files and a new personal identity |
| NootedGreenHP / native graphics stack | Qualify this GPU, patch matching native images and correct HP-specific paths | NootedGreenHP alone is not the entire graphics installation |
| AirportItlwmHP | Native macOS Wi-Fi interface plus AX211 transport and embedded firmware selection | Intel firmware/PNVM and exact fitted-device guards must match |
| HPBAT1Bridge | Read ACPI battery information and publish IOPMPowerSource data | Public menu values do not establish root-domain AC policy or sleep correctness |
| Input ACPI/personality resources | Match I2C1 and expose the HP touchscreen resources | Driver attachment is not physical touch verification |

## Graphics

`drivers/graphics/overlay/` contains the source overlays used for the
qualified version, including HP headers that were originally untracked by
upstream Git. The build overlays it on a pinned upstream checkout. Unchanged upstream firmware payload files are omitted from this repository
and remain in the pinned dependency. The saved diff alone is incomplete. Exact HP guards and binary signature checks constrain
where patches run. The POSH cleanup hook source is preserved separately under
`drivers/graphics/tools/`; overlapping upstream deallocation hooks must not be
stacked. See [build limitations](BUILD.md).

## Wi-Fi

`drivers/wifi/overlay/` contains the modified/new files from the pinned itlwm
fork. The build selects IWX transport units and firmware resources for the fitted
AX211. The native interface avoids a separate HeliPort app. The required PNVM
was missing in earlier generated resources; restoring it enabled discovery.
Numeric diagnostics are source artifacts, not captured networks or credentials.

## Battery and deferred work

The normal build uses battery 0.1.2. A proposed 0.1.3 AC-policy correction is
kept under `experiments/power-policy/`, separate from deployable claims. Its
kernel ABI review and helper tests did not qualify a linked/installed package.
Full sleep investigations are paused; see [STATUS.md](STATUS.md).

## Private versus public evidence

The maintainer's original workspace, USB backup and raw captures remain ignored
under `private/`. Public reports record check scope and limitations, avoiding
machine/account identifiers. A signature check proves a build's form/integrity;
it does not prove GPU execution, radio behavior, or reliable suspend/resume.
