# ACPI and input provenance

The builder never distributes or flashes a firmware DSDT. It accepts the
user's original DSDT only when SHA-256 is
`85ba996338970eade321de17b0399a253aba02b2ebf525233551c7ecc4d86a6b`.
The recorded HP F.03 table has a forward HS07 Scope which macOS's older ACPI
interpreter cannot resolve during pass one. Wrapping it in `If (One)` follows
the [nullmoth/1401 repair](https://github.com/nullmoth/1401/blob/v2.0.1/p1401/dsdt_pass1.py).
`common.py` independently encodes the exact, bounded byte transformation for
this table; it does not include that upstream parser. The intermediate and
final output hashes must equal the qualified HP results. A different table
is refused, even if the laptop has the same model label.

The second change renames only I2C0.TPD0's resource method to XCRS; the supplied
SSDT supplies the matching polling resources. This recovery profile does not
enable the experimental I2C1 touchscreen changes.

SSDT-PLUG-ALT-HP12 derives from OpenCorePkg 1.0.8's SSDT-PLUG-ALT and retains
the accompanying BSD license. The HP EC, AWAC, I2C0 and USBX tables are the
project's recorded model-specific implementations. Recompilation can change
AML compiler metadata while preserving their AML body.

Input source revisions are pinned in downloads.json. VoodooI2C's implementation
is unchanged; its HP personality and polling metadata are supplied in templates.
VoodooInput and VoodooI2CHID are rebuilt with four already-existing Tahoe
IOHIDDevice override declarations in a private SDK header overlay. No new
virtual slots or instance data are introduced. The source build eliminates the
shared IOService/IOHIDDevice termination import that affected the original
installer restart. These rebuilds still need a new physical installation test.

VoodooI2C/HID/GPIO metadata retains the VoodooI2C GPL terms; VoodooInput metadata
retains its upstream license, supplied beside the templates. Downloaded source
and binary dependencies retain their own licenses. No corresponding source
is hidden: the exact archives, revision URLs and build recipe are available.
The public kit is source tooling; generated binary EFIs are private local output.
