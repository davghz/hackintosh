/*
 * HP Envy 15-fe / board8BDF: macOS EC compatibility device.
 * Firmware DSDT and Linux enumerate the real controller as
 * \_SB.PC00.LPCB.EC0. ECDT separately names H_EC (recorded for investigation).
 * This table neither renames nor disables either firmware object.
 * Existing SSDT-USBX remains responsible for USB power properties.
 */
DefinitionBlock ("", "SSDT", 2, "HPPOC", "EC8BDF", 0x00000001)
{
    External (_SB_.PC00.LPCB, DeviceObj)

    Scope (\_SB.PC00.LPCB)
    {
        Device (EC)
        {
            Name (_HID, "ACID0001")
            Method (_STA, 0, NotSerialized)
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Return (Zero)
            }
        }
    }
}
