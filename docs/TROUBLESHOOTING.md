# Troubleshooting

| Symptom | First check | What the result does not prove |
| --- | --- | --- |
| GPU shows 7 MB / basic display | Check the selected versus running boot arguments and actual driver attachment | A booting desktop alone does not prove Metal acceleration |
| Wi-Fi menu has no networks | Confirm the fitted AX211 IDs and required PNVM in the generated resource manifest | Phone tethering or a Wi-Fi icon does not prove AX211 traffic |
| Battery menu works but policy disagrees | Read STATUS's AC-policy limitation | Public percentage does not prove the kernel received an AC adapter notification |
| Screen returns from a brief blank | Distinguish display-off from actual system sleep | A brief lid cycle is not a full sleep/wake qualification |
| Black screen and no Caps Lock response after sleep | Treat as the known unresolved full-sleep failure; recover through the preserved working setup | Do not infer a particular driver from the last console line alone |
| CFG utility says `ABORT` | Keep its result and compare the exact identity/baseline guards | Bypassing a guard is not a compatible port |
| CFG utility says `READBACK EXACT` | Remove registration, reboot again and check every CPU's MSR bit | Saved variable state alone does not prove the hardware lock cleared |

Build failures should be reported with the component, compiler version, pinned
dependency revisions and a short redacted error excerpt. Do not update every
dependency to its latest version as a first response: these builds intentionally
pin their inputs. The CPU EFI build requires Linux/GNU-EFI, while the macOS
components require Apple tools.

If a hardware experiment regresses, restore the exact known-good configuration
and binaries from your own backup. This source repository does not contain a
universal recovery image or a firmware relock utility. Avoid changing multiple
components before the original result can be reproduced.
