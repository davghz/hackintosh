// Staged experiment only. Requires the exact I2C1.TPL1 _CRS-to-XCRS rename.
// Firmware BADR/SPED/HID2 and all amplifier objects remain unchanged.
DefinitionBlock ("", "SSDT", 2, "HP8BDF", "HPI2C1PL", 1)
{
    External (_SB_.PC00.I2C1, DeviceObj)
    External (_SB_.PC00.I2C1.I2CX, IntObj)
    External (_SB_.PC00.I2C1.TPL1, DeviceObj)
    External (_SB_.PC00.I2C1.TPL1.BADR, FieldUnitObj)
    External (_SB_.PC00.I2C1.TPL1.SPED, FieldUnitObj)
    External (_SB_.PC00.I2C1.TPL1.XCRS, MethodObj)
    External (_SB_.PC00.I2CM, MethodObj)

    Scope (\_SB.PC00.I2C1.TPL1)
    {
        Method (_CRS, 0, Serialized)
        {
            If (_OSI ("Darwin"))
            {
                Return (\_SB.PC00.I2CM (\_SB.PC00.I2C1.I2CX, BADR, SPED))
            }
            Return (XCRS ())
        }
    }
}
