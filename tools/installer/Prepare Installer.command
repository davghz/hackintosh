#!/bin/zsh
set -eu
cd "${0:A:h}/../.."
print 'HP 8BDF installer builder (macOS). Read docs/INSTALL.md first.'
print 'This builds a folder. It does not format or modify any USB or internal disk.'
hardware=$(/usr/bin/osascript -e 'POSIX path of (choose folder with prompt "Choose the HP-hardware folder collected on the target HP")')
python3 tools/installer/prepare-installer.py --hardware "$hardware"
print 'Finished. Read docs/INSTALL.md for verification and USB copying.'
read -r '?Press Return to close.'
