# Hardware and known issues — 2026-10-25

Target: HP Envy x360 15-fe0xxx, board 8BDF, BIOS F.03, Core i7-1355U
(2 performance cores + 8 efficiency cores, 12 threads), 16 GB RAM.
Physical GPU is 8086:A7A1 rev 04 / subsystem 103C:8BDF, 96 EUs and
60 MiB stolen memory. Internal display is 1920×1080 eDP. Wi-Fi is Intel AX211
8086:51F1 / subsystem 8086:0094. Audio uses 8086:51CA, ALC245 and CS35L41 amps.

The user restarted into the restored accelerated profile before publication
preparation. The running boot arguments include `-ngreenhp` and no diagnostic
`-ngreenhpdiag`. No new sleep test, boot change, driver installation or reboot
was performed during this packaging task.

## Established, with limits

- GPU 1.0.12: earlier compute/readback and rendering checks passed; the user
  confirmed the split-cursor problem was fixed. Full suspend/resume is separate.
- Wi-Fi 0.1.4: native menu discovery and traffic worked after restoring the
  required PNVM resource to the source build. No HeliPort app is required by
  this driver path.
- Battery 0.1.2: public battery reporting and the menu icon worked. The kernel's
  separate AC-policy state is incomplete; a proposed correction remains staged.
- Keyboard and basic trackpad input work. The touchscreen controller attached,
  but physical touch has not been qualified.
- CFG Lock: the original two-reboot experiment verified MSR bit 15 clear on all
  12 logical CPUs. This does not claim a general CPU unlock across other models.

## Unresolved

- **Full sleep/wake: paused at the user's request.** Accelerated full-sleep
  attempts hung and needed forced restart. A basic-graphics control never
  entered full sleep because Apple's fallback framebuffer vetoed it. That
  control does not isolate the original hang's cause. Display blanking, a brief
  lid cycle, and WillSleep/WillPowerOn notifications alone are not S3 success.
- The existing local idle-sleep guard (`caffeinate -i`) mitigates automatic
  idle sleep only. It does not make manual/lid sleep safe. Shut down when
  leaving the machine rather than relying on unresolved sleep.
- Physical speakers: silent; hardware amplifier initialization remains open.
- Safari video: the original machine uses the BlackHole/Parrot clock workaround;
  that is not a working-speaker claim.
- Brightness/backlight keys: unresolved; experimental PNLF/backlight changes
  remain disabled.
- Bluetooth: staged, disabled and not runtime-qualified.
- Retained `TSC_sync_margin=0`: an installation-time CPU-startup comparison
  bypass, not a TSC synchronization fix. It needs its own later controlled test.
- Automatic macOS updates, other builds/BIOS versions, external displays, DRM,
  hibernation and another laptop are not qualified by these results.

This project's present configuration uses reduced SIP/AMFI protections needed
by its experimental stack. It is not a stock-security or Apple-supported system.
The reference configuration records those settings so users can assess the
actual requirements rather than assuming a normal macOS installation.
