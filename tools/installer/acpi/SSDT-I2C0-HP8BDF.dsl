// HP 8BDF only. Needs TPD0-local _CRS -> XCRS method rename.
// Keep firmware address/speed and descriptor discovery; suppress false APIC routing
// on Darwin so VoodooI2C controller-scoped force-polling is effective.
DefinitionBlock ("", "SSDT", 2, "HP8BDF", "HPI2CPOL", 0x00000001)
{
    External (\_SB.PC00.I2C0, DeviceObj)
    External (\_SB.PC00.I2C0.TPD0, DeviceObj)
    External (\_SB.PC00.I2C0.TPD0.XCRS, MethodObj)
    External (\_SB.PC00.I2CM, MethodObj)
    External (\_SB.PC00.I2C0.I2CX, IntObj)
    External (\_SB.PC00.I2C0.TPD0.BADR, FieldUnitObj)
    External (\_SB.PC00.I2C0.TPD0.SPED, FieldUnitObj)
    Scope (\_SB.PC00.I2C0.TPD0)
    {
        Method (_CRS, 0, Serialized)
        {
            If (_OSI ("Darwin"))
            {
                Return (\_SB.PC00.I2CM (\_SB.PC00.I2C0.I2CX, BADR, SPED))
            }
            Return (XCRS ())
        }
    }
}
