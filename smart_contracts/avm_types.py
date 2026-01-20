from algopy import Account, Struct


class CirculatingSupplyConfig(Struct, kw_only=True):
    """ASA Circulating Supply Configuration"""

    burned_addr: Account
    locked_addr: Account
    custom_addr: Account
