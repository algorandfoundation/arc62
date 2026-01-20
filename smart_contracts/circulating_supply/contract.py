from algopy import (
    Account,
    Asset,
    BoxMap,
    Global,
    String,
    Txn,
    UInt64,
    gtxn,
    itxn,
    op,
    size_of,
    subroutine,
)
from algopy.arc4 import abimethod

import smart_contracts.errors as err
from smart_contracts.arc62_interface import Arc62Interface
from smart_contracts.avm_types import CirculatingSupplyConfig

from . import config as cfg


@subroutine
def _asa_exists(asa: Asset) -> bool:
    _creator, exists = op.AssetParamsGet.asset_creator(asa)
    return exists


class CirculatingSupply(Arc62Interface):
    """
    Singleton Application providing ARC-62 getter for ASA Circulating Supply
    """

    def __init__(self) -> None:
        self.circulating_supply = BoxMap(Asset, CirculatingSupplyConfig, key_prefix="")

    @abimethod
    def init_config(self, asset: Asset, mbr_payment: gtxn.PaymentTransaction) -> UInt64:
        """
        Non-normative: Initialize the circulating supply configuration for an ASA
        Authorization: ASA Manager Address.

        Args:
            asset: The ASA ID to initialize the circulating supply configuration for
            mbr_payment: Circulating supply configuration MBR payment transaction

        Returns:
            MBR (in microALGO) for the circulating supply configuration initialization
        """
        # Preconditions
        assert (
            Txn.sender == asset.manager
        ), err.UNAUTHORIZED  # Implicit ASA existence check
        assert asset not in self.circulating_supply, err.CONFIG_EXISTS
        assert (
            mbr_payment.receiver == Global.current_application_address
        ), err.INVALID_MBR_RECEIVER

        # Initialize ASA Circulating Supply Configuration
        mbr_i = Global.current_application_address.min_balance
        _exists = self.circulating_supply.box(asset).create(
            size=size_of(CirculatingSupplyConfig)
        )
        self.circulating_supply[asset].burned_addr = Global.zero_address
        self.circulating_supply[asset].locked_addr = Global.zero_address
        self.circulating_supply[asset].custom_addr = Global.zero_address

        # Postconditions
        mbr_delta_amount = Global.current_application_address.min_balance - mbr_i
        assert mbr_payment.amount >= mbr_delta_amount, err.INVALID_MBR_AMOUNT

        return mbr_delta_amount

    @abimethod
    def set_not_circulating_address(
        self, asset: Asset, address: Account, label: String
    ) -> None:
        """
        Non-normative: Set non-circulating supply addresses
        Authorization: ASA Manager Address.

        Args:
            asset: ASA ID of the circulating supply
            address: Address to assign to the non-circulating supply label to
            label: Not-circulating supply label selector
        """
        # Preconditions
        assert Txn.sender == asset.manager, err.UNAUTHORIZED
        assert asset in self.circulating_supply, err.CONFIG_NOT_EXISTS
        assert address.is_opted_in(asset), err.NOT_OPTED_IN

        # Effects
        match label:
            case cfg.BURNED:
                self.circulating_supply[asset].burned_addr = address
            case cfg.LOCKED:
                self.circulating_supply[asset].locked_addr = address
            case cfg.CUSTOM:
                self.circulating_supply[asset].custom_addr = address
            case _:
                op.err(err.INVALID_LABEL)

    @abimethod
    def delete_config(self, asset: Asset) -> UInt64:
        """
        Non-normative: Delete the circulating supply configuration for an ASA
        Authorization: ASA Manager Address.

        Args:
            asset: The ASA ID to delete the circulating supply configuration for

        Returns:
            MBR (in microALGO) for the circulating supply configuration deletion
        """
        # Preconditions
        assert asset in self.circulating_supply, err.CONFIG_NOT_EXISTS
        if _asa_exists(asset):
            assert Txn.sender == asset.manager, err.UNAUTHORIZED

        # Delete ASA Circulating Supply Configuration
        mbr_i = Global.current_application_address.min_balance
        del self.circulating_supply[asset]
        mbr_delta_amount = mbr_i - Global.current_application_address.min_balance

        # Refund MBR
        itxn.Payment(receiver=Txn.sender, amount=mbr_delta_amount).submit()

        return mbr_delta_amount

    @abimethod(readonly=True)
    def get_config(self, asset: Asset) -> CirculatingSupplyConfig:
        """
        Non-normative: Get ASA circulating supply configuration.

        Args:
            asset: The ASA ID to get the circulating supply configuration for

        Returns:
            ASA circulating supply configuration
        """
        assert asset in self.circulating_supply, err.CONFIG_NOT_EXISTS
        return self.circulating_supply[asset]

    @abimethod(readonly=True)
    def arc62_get_circulating_supply(self, asset_id: UInt64) -> UInt64:
        """
        Get ASA circulating supply.

        Args:
            asset_id: ASA ID of the circulating supply

        Returns:
            ASA circulating supply
        """
        asset = Asset(asset_id)

        # Preconditions
        assert asset in self.circulating_supply, err.CONFIG_NOT_EXISTS

        # Effects
        asa_exists = _asa_exists(asset)

        reserve_balance = (
            UInt64(0)
            if asset.reserve == Global.zero_address
            or not asa_exists
            or not asset.reserve.is_opted_in(asset)
            else asset.balance(asset.reserve)
        )

        burned_addr = self.circulating_supply[asset].burned_addr
        burned_balance = (
            UInt64(0)
            if burned_addr == Global.zero_address
            or not asa_exists
            or not burned_addr.is_opted_in(asset)
            else asset.balance(burned_addr)
        )

        locked_addr = self.circulating_supply[asset].locked_addr
        locked_balance = (
            UInt64(0)
            if locked_addr == Global.zero_address
            or not asa_exists
            or not locked_addr.is_opted_in(asset)
            else asset.balance(locked_addr)
        )

        custom_addr = self.circulating_supply[asset].custom_addr
        custom_balance = (
            UInt64(0)
            if custom_addr == Global.zero_address
            or not asa_exists
            or not custom_addr.is_opted_in(asset)
            else asset.balance(custom_addr)
        )

        return (
            asset.total
            - reserve_balance
            - burned_balance
            - locked_balance
            - custom_balance
        )

    @abimethod
    def extra_resources(self) -> None:
        """
        Non-normative: Placeholder method to acquire AVM extra resources.
        """
        pass

    @abimethod
    def withdraw_balance_excess(self) -> None:
        """
        Non-normative: Method to withdraw balance excess due to accidental deposits
        (it should never happen if deposits match exactly the required MBR. Deleted
        config MBR is not included in the excess, since it is immediately returned
        on delete).
        """
        excess_balance = (
            Global.current_application_address.balance
            - Global.current_application_address.min_balance
        )
        itxn.Payment(
            receiver=Global.creator_address,
            amount=excess_balance,
        ).submit()
