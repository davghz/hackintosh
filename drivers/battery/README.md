# HPBAT1Bridge 0.1.2

The normal battery source reads the HP BAT1 ACPI interface and publishes native
battery information. It retains exact HP/kernel/build guards. Public charge
reporting and the menu icon worked on the original machine.

Build with `python3 drivers/battery/build.py` after dependency preparation in
[BUILD.md](../../docs/BUILD.md). The generated bundle is `HPBAT1Bridge.kext`;
the existing EFI directory calls it `HPBAT1Bridge12.kext`. Match the configured
BundlePath when deploying a separately reviewed candidate.

The included OpenCore fragment is disabled by default. The kernel's separate
AC adapter policy notification is incomplete in this version. The proposed
0.1.3 correction is preserved in `experiments/power-policy/` and is not included
in this build or claimed as a sleep fix. Original source uses the scoped
[MIT license](../../LICENSE).
