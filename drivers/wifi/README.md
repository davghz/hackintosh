# AirportItlwmHP 0.1.4

Native-menu Wi-Fi adaptation of laobamac/itlwm for the fitted Intel AX211
8086:51F1 / subsystem 8086:0094. Network discovery and traffic worked on the
original HP. This path does not need HeliPort.

Build with `python3 drivers/wifi/build.py` after dependency preparation in
[BUILD.md](../../docs/BUILD.md). The build keeps IWX transport units, twelve
pinned ucodes and the fitted `iwlwifi-so-a0-gf-a0.pnvm` resource. Omitting that
PNVM caused the earlier firmware startup/discovery failure. Its name and hash
are checked before compilation.

`overlay/` supplies modified/new sources; `stage-map.json` and `trace-schema.json`
describe bounded numeric diagnostics. They contain no collected network names
or credentials. The historical manifest describes the original build, before
runtime qualification. Do not interpret a successful rebuild as a new radio test.

Retain the [GPL terms](LICENSE-upstream), embedded file notices and the
[Intel firmware terms](LICENSE-Intel-firmware). Other Intel radios and newer
macOS builds require separate qualification.
