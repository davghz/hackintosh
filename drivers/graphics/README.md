# NootedGreenHP 1.0.12

HP adaptation of the pinned NootedGreen/Iris Xe stack for physical A7A1 rev 04,
subsystem 103C:8BDF, 96 EUs, 60 MiB stolen memory and macOS build 25G241.
The original laptop passed bounded GPU compute/render checks and the user
confirmed the fix. Full system sleep remains unresolved.

- `overlay/`: source copied over the pinned upstream directory, including HP
  qualification and patch helpers. Unchanged firmware payload files are omitted.
- `hp-source.patch`: supplementary historical diff, insufficient alone because
  originally untracked headers are not represented there.
- `build.py`: local-only build; see [instructions](../../docs/BUILD.md).
- `tools/`: probes/tests and the separate POSH cleanup source; some tests need
  exact private driver-image fixtures.
- `original-build-manifest.json`: historical build inputs/hashes. Its
  build-time "not hardware validated" wording predates subsequent testing.

Building this kext is not a complete graphics installation. Matching native
graphics bundles, dependency/cache setup and the userspace hook are separate.
Do not relax guards for another machine or combine overlapping POSH free hooks.
See [LICENSE](LICENSE), [NOTICE](NOTICE.md), [status](../../docs/STATUS.md) and
[architecture](../../docs/ARCHITECTURE.md).
