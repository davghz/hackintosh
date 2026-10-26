/*
 * Derived from OpenCorePkg1.0.8 SSDT-PLUG-ALT.dsl.
 * https://github.com/acidanthera/OpenCorePkg/blob/1.0.8/Docs/AcpiSamples/Source/SSDT-PLUG-ALT.dsl
 * Retain accompanying OpenCore-LICENSE.txt for redistribution.
 * HP board8BDF F.03: only MADT-enabled processor UIDs0..11.
 * Darwin-only compatibility Processor objects, plugin-type on CP00.
 * PBlockAddress follows the official sample (ignored by macOS).
 * Original firmware PRxx devices are not renamed or disabled.
 */
DefinitionBlock ("", "SSDT", 2, "HPPOC", "PLUG12", 0x00000001)
{
    External (_SB_, DeviceObj)
    Scope (\_SB)
    {
        Processor (CP00, 0x00, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)  // _HID: Hardware ID
            Name (_UID, Zero)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }

            Method (_DSM, 4, NotSerialized)
            {
                If (LEqual (Arg2, Zero)) {
                    Return (Buffer (One) { 0x03 })
                }

                Return (Package (0x02)
                {
                    "plugin-type",
                    One
                })
            }
        }
        Processor (CP01, 0x01, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 1)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
        Processor (CP02, 0x02, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 2)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
        Processor (CP03, 0x03, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 3)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
        Processor (CP04, 0x04, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 4)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
        Processor (CP05, 0x05, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 5)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
        Processor (CP06, 0x06, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 6)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
        Processor (CP07, 0x07, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 7)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
        Processor (CP08, 0x08, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 8)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
        Processor (CP09, 0x09, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 9)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
        Processor (CP10, 0x0A, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 10)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
        Processor (CP11, 0x0B, 0x00000510, 0x06)
        {
            Name (_HID, "ACPI0007" /* Processor Device */)
            Name (_UID, 11)
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
    }
}
