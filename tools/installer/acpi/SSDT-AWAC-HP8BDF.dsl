/*
 * HP Envy x360 15-fe0xxx / board 8BDF, Insyde F.03.
 * The inspected DSDT exposes AWAC for STAS=0 and the existing RTC for STAS=1.
 * STAS is an 8-bit field in the firmware's GNVS operation region.
 * Select the legacy RTC only for Darwin. No new RTC, method rename, _INI
 * replacement or RTC resource override is needed on this machine.
 *
 * Pattern: https://dortania.github.io/Getting-Started-With-ACPI/Universal/awac-methods/manual.html
 * Paired DSDT SHA256: 0899799edc05029d58579091569666aa8ce9f85dcafb573fbb9993cfc6293d37
 */
DefinitionBlock ("", "SSDT", 2, "HPPOC", "AWAC8BDF", 0x00000001)
{
    External (\STAS, FieldUnitObj)

    Scope (\_SB)
    {
        If (_OSI ("Darwin"))
        {
            Store (One, \STAS)
        }
    }
}
