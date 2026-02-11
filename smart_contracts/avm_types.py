from algopy import Account, Struct


class CirculatingSupplyConfig(Struct, kw_only=True):
    """ASA Circulating Supply Configuration"""

    burned_addr: Account
    locked_addr: Account
    custom_1_addr: Account
    custom_2_addr: Account
    custom_3_addr: Account
    custom_4_addr: Account
