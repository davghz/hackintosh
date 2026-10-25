# Validation records

The publication audit checks the shareable source and documentation. It does
not requalify the laptop's drivers or establish a sleep fix.

- `pass-1.json` and `pass-2.json` record the earlier Desktop packaging checks.
  They are historical snapshots: later documentation, license and publication
  scope changes supersede individual observations such as no configured remote
  or a pending original-code license.
- `publication-audit.json` records the final pre-upload audit and source digest.
  It supersedes the earlier export's firmware inclusion and stale comments.
- Fresh builds use a separate source-only directory with dependencies fetched
  from the pinned public repositories, without the original development cache.
  Three macOS kext builds and ad-hoc signature checks are distinct from hardware
  qualification.
- CPU helper/publication tests use synthetic inputs and make no firmware writes.
  No new Linux/OVMF run or physical CPU-unlock experiment was performed for
  publication; the original successful VM/hardware history is documented in
  the CPU guide with that limitation.

Raw logs, local identifiers and original firmware records remain private.
The staged-content scanner also has negative tests, but it is not an exhaustive
secret detector. Review new content and its licensing before every publication.
