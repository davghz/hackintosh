# Build the macOS components

Use an Intel Mac/macOS development environment with Python 3.9+, Git and Apple
Command Line Tools. The recorded compiler was Apple clang 21.0.0. Build outputs
remain ignored and are never automatically loaded or installed.

From the repository root:

```sh
python3 tools/prepare-build.py
python3 drivers/graphics/build.py
python3 drivers/wifi/build.py
python3 drivers/battery/build.py
```

The preparation script downloads pinned repositories into `deps/`, copies the
tracked HP overlays into those working trees, and verifies the Lilu archive's
SHA-256. It treats `deps/` as generated build input; make your edits to the
tracked overlays, since rerunning preparation replaces corresponding files in
`deps/`. To use the original local development cache instead of the network:

```sh
python3 tools/prepare-build.py --local-cache /path/to/hp-macos-postinstall
```

| Dependency | Pinned revision |
| --- | --- |
| JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe | `6b5f0492f72308243af222a0aa43fe11db64db3c` |
| laobamac/itlwm | `738d4c61b5a64433b27c1ab09dba94916ab77d8d` |
| acidanthera/MacKernelSDK | `3f750085caa17ec3a7880f11c11bf4f48cd6a164` |
| Lilu DEBUG | 1.7.2, archive SHA-256 `e95df95d82e8b151047abf359ecd9c853755c59293e19dfcc3907da8fbd8cf89` |

Outputs:

- `drivers/graphics/build-v1.0.12/NootedGreenHP.kext`
- `drivers/wifi/build/AirportItlwmHP.kext`
- `drivers/battery/build/HPBAT1Bridge.kext`

The existing EFI calls the battery bundle directory `HPBAT1Bridge12.kext`;
the executable and bundle identifier remain HPBAT1Bridge. A folder-name change
requires matching `Kernel/Add/BundlePath`.

The source overlays plus the pinned upstream checkout are authoritative.
Four unchanged upstream firmware payload files (`IGGucBinary.h`, `IGHucBinary.h`,
`Firmware.cpp`, `FirmwareADLP.cpp`) are deliberately not redistributed here;
they remain in the downloaded upstream dependency. Its contents and terms
must be reviewed independently before redistributing a compiled bundle. The historical `hp-source.patch` files
are supplementary: Git diffs can omit originally untracked HP headers. Applying
only those patches is not a complete build. Original build manifests describe
the build-time state, before later hardware qualification; consult STATUS for
the observed results. Different build paths/debug information can change binary
hashes, so rebuilt binaries are not claimed byte-identical to installed ones.

The GPU kext is one part of the working graphics stack. The original system also
uses its matching Apple TGL/Metal bundles, HookCase support, and the HP POSH
cleanup hook. Apple binaries are not redistributed here. The POSH source is
under `drivers/graphics/tools/`; it is included for development, not an automatic
installer. Do not combine it with an upstream overlapping deallocation patch.

Wi-Fi rebuilds retain the exact fitted AX211 PNVM resource plus twelve pinned
IWX ucodes; firmware is fetched from the pinned upstream source under Intel's
terms. Omitting the PNVM was a real cause of the earlier scan failure.

Graphics test sources are provided in `drivers/graphics/tools/`. Some require
matching private driver bytes as fixtures; do not fabricate those or publish
Apple binary windows to make a test appear self-contained. Compilation,
signature checks and source equality do not replace device qualification.

CPU unlock builds use Linux/GNU-EFI instead; follow the separate
[CPU guide](CPU-UNLOCK.md). The uninstalled battery 0.1.3 and GPU recovery
proposals in `experiments/` are deliberately excluded from these builds.
