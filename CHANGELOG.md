# Changelog

## Initial public source snapshot — 2026-10-25

This is a development snapshot, not a binary release or a new hardware validation.

- Preserves HP NootedGreenHP 1.0.12 graphics changes, including qualified
  60 MiB stolen-memory handling and the corrected cursor rendering path.
- Preserves AirportItlwmHP 0.1.4 with the fitted AX211's required PNVM resource
  and native Wi-Fi menu support.
- Includes HPBAT1Bridge 0.1.2 battery source; distinguishes working public
  reporting from the unresolved kernel AC-policy notification.
- Publishes the constrained HP F.03 CPU CFG Lock source, Linux management
  tools, OVMF fixture and two-reboot procedure. Private expected payloads and
  personalized EFI binaries are excluded.
- Adds portable dependency preparation and component build paths, a local
  baseline generator, an explicit fixture build rule and publication checks.
- Preserves uninstalled power-policy/GPU proposals under `experiments/`.
- Documents full sleep/wake as unresolved and paused, along with remaining
  audio, brightness, Bluetooth and touchscreen qualification work.
- Adds the maintainer's noncommercial hobbyist declaration, a prominent
  working/unresolved status table and optional ETH support scoped to original
  MIT-licensed tools/documentation, preserving the GPU's separate terms.

The original GPU/Wi-Fi/battery source algorithms are preserved. Packaging and
read-only verification helpers may evolve independently from deployed drivers.
