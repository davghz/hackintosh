# Deferred experiments — not installed fixes

Sleep/wake work is paused. The following source is preserved for future review;
the normal build commands do not include it:

- `power-policy/`: battery 0.1.3 proposal to publish validated AC adapter state
  to the kernel root-domain policy. The corrected object and helper were
  reviewed/tested, but a corrected linked package and hardware qualification
  are still outstanding. It does not establish a sleep repair.
- `gpu-recovery/`: staged GPU recovery validation patch(es), not installed.
  Preserve all hardware/build guards when evaluating them.

Do not apply these together with the established baseline or promote a source
test result into a hardware success claim. The original reports, rejected
artifacts and raw captures remain in the private local archive.
