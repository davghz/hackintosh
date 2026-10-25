# HP Envy x360 15-fe — macOS engineering project

Experimental macOS support for one **HP Envy x360 15-fe0xxx, board 8BDF,
BIOS F.03, Intel Core i7-1355U**. This repository collects the source changes
developed and tested on that machine, including Iris Xe graphics, native-menu
AX211 Wi-Fi, battery reporting, and a one-shot CPU CFG Lock utility.

The recorded macOS baseline is **Tahoe 26.7.1 / 25G241**, Darwin 25.6.0,
with OpenCore 1.0.8. Several patches depend on exact hardware and binary
signatures. Similar model names do not establish compatibility.

**Full system sleep/wake is broken and development on it is paused.**
This is an experimental development snapshot, not a finished daily-use release
or a complete bootable EFI download.

This is a **free, noncommercial hobbyist project**. There are no paid downloads
or paid GPU support/services. Contributions and testing reports are welcome.

## Start here

1. Read [hardware and current status](docs/STATUS.md).
2. For our CPU unlock procedure, read [CPU CFG Lock guide](docs/CPU-UNLOCK.md).
3. To compile the macOS changes, read [building from source](docs/BUILD.md).
4. Before adapting an EFI, read [configuration and deployment](docs/CONFIGURATION.md).
5. For the implementation map, read [architecture](docs/ARCHITECTURE.md).
6. For attribution and redistribution terms, read [licenses](licenses/README.md).

## What works and what does not

| Component | Status on the original laptop | Details |
| --- | --- | --- |
| macOS boot | Works with the recorded USB/OpenCore setup | This repository is not a complete bootable EFI |
| Iris Xe graphics | Working in bounded tests | Metal compute/render checks passed; split cursor corrected in [GPU 1.0.12](drivers/graphics/) |
| Intel AX211 Wi-Fi | Working | Native-menu discovery and traffic with [Wi-Fi 0.1.4](drivers/wifi/) |
| Battery | Partly working | Menu/charge reporting work; kernel AC-policy notification is incomplete in [0.1.2](drivers/battery/) |
| CPU CFG Lock | Unlock verified | MSR 0xE2 bit 15 cleared on all 12 logical CPUs after two reboots; [guide](docs/CPU-UNLOCK.md) |
| Keyboard / trackpad | Basic input working | Full gesture coverage has not been qualified |
| Safari video | Works with a workaround | Original machine uses the BlackHole/Parrot clock workaround; not proof of working speakers |
| Touchscreen | Unverified | Controller attached; physical touch not qualified; [I2C1 resources](drivers/input/) |
| Built-in speakers | Not working | Physical speaker output is silent; amplifier initialization remains open |
| Screen brightness keys | Not working | Backlight/brightness work remains unresolved |
| Bluetooth | Not qualified | Prototype remains disabled; no working Bluetooth claim |
| Full sleep/wake | Not working reliably | Can hang and require forced restart; investigation paused |
| Other hardware / OS builds | Unverified | External displays, DRM, hibernation and other machines/builds are not qualified |

See [STATUS.md](docs/STATUS.md) for the exact hardware, limitations and deferred
work. Display-off recovery is not evidence that full system sleep works.

These are bounded results from the original laptop, not fresh qualification of
every rebuild or another machine. GPU support extends the NootedGreen/Iris Xe
work of upstream authors; Wi-Fi extends itlwm. This is not all original driver
code, and macOS still needs third-party components.

## Repository layout

```text
docs/                 usage, builds, limitations
drivers/              tested-version source overlays and build scripts
tools/cpu-unlock/     constrained HP F.03 one-shot EFI utility and VM fixture
config/               sanitized reference configuration; no bootable EFI
experiments/          uninstalled proposals; not release fixes
verification/         preparation and validation reports
licenses/             component provenance and license boundaries
```

The maintainer's Desktop copy also has an ignored `private/` folder containing
the complete original development tree and USB backup. It contains credentials,
firmware records and logs. **Do not upload or zip the entire Desktop folder.**
Only the reviewed Git file set belongs on GitHub. `deps/` and generated outputs
are also ignored. Original development files and the running USB remain separate.

No Apple kernel, recovery image, GPU driver bundle, firmware-variable baseline,
personal SMBIOS identity, or configured Wi-Fi password is included in the
shareable source set. The build scripts prepare files locally; they do not
install drivers, rebuild system caches, restart, or put the machine to sleep.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md), [troubleshooting](docs/TROUBLESHOOTING.md),
and the [changelog](CHANGELOG.md). Original project code is MIT-licensed.
Wi-Fi and GPU derivatives keep their upstream terms; the GPU's nonprofit
restriction means this collection as a whole is not an unrestricted open-source
release. Read the [license map](licenses/README.md) before reusing a component.

## Optional support for the original tools and documentation

If you want to contribute toward development costs such as compute credits for
the **original MIT-licensed tools and documentation**, voluntary ETH gifts can
be sent to the maintainer's Ethereum address:

```text
0x61bfcf2fa9e7d8cef32c1778444e2a4c5e315b21
```

These gifts are optional and do not buy access, support, priority or a promised
fix. This is not a fundraising request for the TSNPL-covered GPU component or
related support/services, which remain outside this support note under their
upstream no-revenue terms. An Ethereum transfer does not directly transfer
provider-specific AI/API credits. See the [support scope](docs/SUPPORT.md).
