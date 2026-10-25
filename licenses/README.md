# Provenance and license boundaries

Original project code is released under the scoped [MIT license](../LICENSE).
GPU and Wi-Fi derivatives retain their upstream licenses. No single license
overrides them. The graphics license restricts commercial redistribution, so
this entire mixed-license collection must not be described as wholly
OSI-open-source. Its original MIT and GPL-covered components are open source.
See the [Open Source Definition](https://opensource.org/osd) for that distinction.

| Component | Origin / terms |
| --- | --- |
| GPU source and HP modifications | NootedGreen by StezzaPilot/sgiammori, extended by JulioNectar's Iris Xe project; see [GPU LICENSE](../drivers/graphics/LICENSE) and [upstream notice](../drivers/graphics/NOTICE.md). The supplied license is Thou Shalt Not Profit License 1.0; it is not MIT. |
| Wi-Fi source and HP modifications | [laobamac/itlwm](https://github.com/laobamac/itlwm), derived from OpenIntelWireless/itlwm; retain [upstream license](../drivers/wifi/LICENSE-upstream) and all embedded file notices. |
| Intel Wi-Fi firmware | Retrieved during builds; [Intel firmware terms](../drivers/wifi/LICENSE-Intel-firmware). |
| HookCase dependency | Steven Michaud and upstream modifications; MIT in the pinned dependency's `src/LICENSE-HookCase`. |
| MacKernelSDK / Lilu / OpenCore / Voodoo components | Their respective authors and original terms; retrieved as dependencies or referenced, not relicensed here. |
| CPU unlock, battery bridge, project-specific packaging/docs | Original project work, except any retained third-party notices; MIT under the scope in the root LICENSE. |

Pinned upstream revisions are recorded in [BUILD.md](../docs/BUILD.md). Source
overlays and build recipes are included so modifications can be inspected;
binary-only redistributions require their own corresponding-source and license
review. The GPU upstream NOTICE describes its original repository, including
components that this smaller collection does not ship.

Apple driver bundles, the macOS kernel, recovery images, original firmware
dumps and machine-specific variable payloads are not part of the shareable set.
Apple, Intel and HP names identify tested hardware/software; no endorsement
or vendor support is claimed.
