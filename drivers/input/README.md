# HP I2C1 resources

These source/configuration fragments describe the fitted I2C1 touchscreen
controller and its Darwin polling resources. They are not a complete standalone
input-driver package. The original system also uses VoodooI2C/VoodooI2CHID and
the exact matching HP ACPI repairs recorded in `config/components.json`.

Controller attachment was observed; physical touch remains unverified. The
trackpad's basic input works separately. Do not overwrite another laptop's DSDT
with the original HP table or infer touchscreen functionality from attachment.
See [configuration](../../docs/CONFIGURATION.md).
