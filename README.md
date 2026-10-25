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

## Start here

1. Read [hardware and current status](docs/STATUS.md).
2. For our CPU unlock procedure, read [CPU CFG Lock guide](docs/CPU-UNLOCK.md).
3. To compile the macOS changes, read [building from source](docs/BUILD.md).
4. Before adapting an EFI, read [configuration and deployment](docs/CONFIGURATION.md).
5. For the implementation map, read [architecture](docs/ARCHITECTURE.md).
6. For attribution and redistribution terms, read [licenses](licenses/README.md).

| Component | Recorded result | Source |
| --- | --- | --- |
| Iris Xe A7A1, 96 EU, 60 MiB stolen memory | Metal compute/render tests passed; split cursor corrected | [GPU 1.0.12](drivers/graphics/) |
| Intel AX211, 51F1:0094 | Native Wi-Fi menu discovery and traffic worked | [Wi-Fi 0.1.4](drivers/wifi/) |
| Battery | Menu and charge reporting worked; kernel AC-policy notification incomplete | [Battery 0.1.2](drivers/battery/) |
| CPU CFG Lock | MSR 0xE2 bit 15 cleared on all 12 logical CPUs after two reboots | [Unlock source](tools/cpu-unlock/) |
| Keyboard / trackpad | Basic input works | Existing Voodoo input stack; see configuration |
| Touchscreen | Controller attached; physical touch remains unverified | [I2C1 resources](drivers/input/) |
| Speakers, brightness keys, Bluetooth | Unresolved | See [status](docs/STATUS.md) |
| Full sleep/wake | Can hang and require forced restart; paused | [Deferred work](experiments/README.md) |

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
