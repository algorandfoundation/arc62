from typing import LiteralString

# ── Auth ──────────────────────────────────────────────────────────────────────
# Unauthorized, it must be the ASA Manager
UNAUTHORIZED: LiteralString = "unauthorized"

# ── ASA ───────────────────────────────────────────────────────────────────────
# The specified ASA does not exist
ASA_NOT_EXIST: LiteralString = "asaNotExist"

# The ASA must not have a clawback address
ASA_NOT_ARC54_COMPLIANT: LiteralString = "asaNotArc54Compliant"

# ── Config ────────────────────────────────────────────────────────────────────
# Circulating supply config already exists for the specified ASA
CONFIG_EXIST: LiteralString = "configExist"

# Circulating supply config does not exist for the specified ASA
CONFIG_NOT_EXIST: LiteralString = "configNotExist"

# ── Labels ────────────────────────────────────────────────────────────────────
# Invalid label, it must be burned, custom_1, custom_2, custom_3, or custom_4
LABEL_INVALID: LiteralString = "labelInvalid"

# Address is not opted in to the ASA
ADDRESS_NOT_OPTED_IN: LiteralString = "addressNotOptedIn"

# Address is the ASA Reserve Address
ADDRESS_IS_RESERVE: LiteralString = "addressIsReserve"

# Address is already assigned to another label
ADDRESS_ALREADY_ASSIGNED: LiteralString = "addressAlreadyAssigned"

# Invalid burned address, it must be the ARC-54 burn address
BURNED_ADDRESS_INVALID: LiteralString = "burnedAddressInvalid"

# ── MBR ───────────────────────────────────────────────────────────────────────
# Invalid MBR receiver, it must be the Circulating Supply App
MBR_RECEIVER_INVALID: LiteralString = "mbrReceiverInvalid"

# Invalid MBR amount, it must cover the circulating supply config MBR
MBR_AMOUNT_INVALID: LiteralString = "mbrAmountInvalid"
