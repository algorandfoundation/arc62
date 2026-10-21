from algopy import Account, Struct, UInt64


class CirculatingSupplyConfig(Struct, kw_only=True):
    """ASA Circulating Supply Configuration"""

    burned_addr: Account
    custom_1_addr: Account
    custom_2_addr: Account
    custom_3_addr: Account
    custom_4_addr: Account


# ARC-28 Events
class Arc62ConfigUpdated(Struct, kw_only=True):
    """Event emitted when the ASA Circulating Supply Configuration is created or updated"""

    asset_id: UInt64
    round: UInt64
    timestamp: UInt64
    burned_addr: Account
    custom_1_addr: Account
    custom_2_addr: Account
    custom_3_addr: Account
    custom_4_addr: Account


class Arc62ConfigDeleted(Struct, kw_only=True):
    """Event emitted when the ASA Circulating Supply Configuration is deleted"""

    asset_id: UInt64
    round: UInt64
    timestamp: UInt64
    asa_exists: bool
