# Preparing the GitHub upload

The Desktop repository contains a complete private development copy alongside
the curated source files. Only staged, reviewed Git files should be published.
Do not use Finder to upload the entire folder, and do not force-add ignored
files. The original USB backup contains network credentials and firmware data.

Review the component boundaries in [licenses/README.md](../licenses/README.md).
The MIT grant covers original project code; upstream terms remain binding.

From the repository root:

```sh
git diff --cached --stat
python3 -m unittest discover -s tests
python3 tools/audit-public.py
python3 tools/audit-public.py --zip ../hackintosh-source.zip
```

The exporter refuses to replace an existing ZIP and verifies every member
against the staged bytes. It exports no Git history, private tree, downloaded
dependencies, firmware baselines or binaries. Common secret-pattern checks are
useful but cannot prove all future edits are free of sensitive data.

Use your own Git identity when committing. Before every push, audit the exact
staged content and review the diff. Publication verification should compare
the remote commit and file tree with the audited local commit. New edits must
be staged and audited again; an older ZIP/report does not cover them.
