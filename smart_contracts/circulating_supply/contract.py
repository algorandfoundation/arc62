from algopy import (
    Account,
    Asset,
    BoxMap,
    Global,
    String,
    TemplateVar,
    Txn,
    UInt64,
    arc4,
    gtxn,
    itxn,
    logged_assert,
    logged_err,
    op,
    size_of,
    subroutine,
)
from algopy.arc4 import abimethod

import smart_contracts.errors as err
from smart_contracts.arc62_interface import Arc62Interface
from smart_contracts.avm_types import (
    Arc62ConfigDeleted,
    Arc62ConfigUpdated,
    CirculatingSupplyConfig,
)
from smart_contracts.template_vars import ARC54_BURN_ADDRESS

from . import config as cfg


@subroutine
def _asa_exists(asa: Asset) -> bool:
    _creator, exists = op.AssetParamsGet.asset_creator(asa)
    return exists


@subroutine
def _is_arc54_compliant(asa: Asset) -> bool:
    clawback, exists = op.AssetParamsGet.asset_clawback(asa)
    return exists and clawback == Global.zero_address


class CirculatingSupply(Arc62Interface, avm_version=13):
    """
    Singleton Application providing ARC-62 getter for ASA Circulating Supply
    """

    def __init__(self) -> None:
        self.circulating_supply = BoxMap(Asset, CirculatingSupplyConfig, key_prefix="")

    def _emit_config_updated(self, asset: Asset) -> None:
        config = self.circulating_supply[asset].copy()
        arc4.emit(
            Arc62ConfigUpdated(
                asset_id=asset.id,
                round=Global.round,
                timestamp=Global.latest_timestamp,
                burned_addr=config.burned_addr,
                custom_1_addr=config.custom_1_addr,
                custom_2_addr=config.custom_2_addr,
                custom_3_addr=config.custom_3_addr,
                custom_4_addr=config.custom_4_addr,
            )
        )

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
        logged_assert(_asa_exists(asset), err.ASA_NOT_EXIST)
        logged_assert(Txn.sender == asset.manager, err.UNAUTHORIZED)
        logged_assert(asset not in self.circulating_supply, err.CONFIG_EXIST)
        logged_assert(
            mbr_payment.receiver == Global.current_application_address,
            err.MBR_RECEIVER_INVALID,
        )

        # Initialize ASA Circulating Supply Configuration
        mbr_i = Global.current_application_address.min_balance
        _exists = self.circulating_supply.box(asset).create(
            size=size_of(CirculatingSupplyConfig)
        )
        self.circulating_supply[asset].burned_addr = Global.zero_address
        self.circulating_supply[asset].custom_1_addr = Global.zero_address
        self.circulating_supply[asset].custom_2_addr = Global.zero_address
        self.circulating_supply[asset].custom_3_addr = Global.zero_address
        self.circulating_supply[asset].custom_4_addr = Global.zero_address

        # Postconditions
        mbr_delta_amount = Global.current_application_address.min_balance - mbr_i
        logged_assert(mbr_payment.amount >= mbr_delta_amount, err.MBR_AMOUNT_INVALID)

        self._emit_config_updated(asset)
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
            address: Address to assign to the non-circulating supply label to (the
                Zero Address unsets the label)
            label: Not-circulating supply label selector
        """
        # Preconditions
        logged_assert(_asa_exists(asset), err.ASA_NOT_EXIST)
        logged_assert(Txn.sender == asset.manager, err.UNAUTHORIZED)
        logged_assert(asset in self.circulating_supply, err.CONFIG_NOT_EXIST)
        config = self.circulating_supply[asset].copy()
        is_unset = address == Global.zero_address
        if not is_unset:
            logged_assert(address.is_opted_in(asset), err.ADDRESS_NOT_OPTED_IN)
            logged_assert(address != asset.reserve, err.ADDRESS_IS_RESERVE)
            # An address can be assigned to one label only
            logged_assert(
                label == cfg.BURNED or address != config.burned_addr,
                err.ADDRESS_ALREADY_ASSIGNED,
            )
            logged_assert(
                label == cfg.CUSTOM_1 or address != config.custom_1_addr,
                err.ADDRESS_ALREADY_ASSIGNED,
            )
            logged_assert(
                label == cfg.CUSTOM_2 or address != config.custom_2_addr,
                err.ADDRESS_ALREADY_ASSIGNED,
            )
            logged_assert(
                label == cfg.CUSTOM_3 or address != config.custom_3_addr,
                err.ADDRESS_ALREADY_ASSIGNED,
            )
            logged_assert(
                label == cfg.CUSTOM_4 or address != config.custom_4_addr,
                err.ADDRESS_ALREADY_ASSIGNED,
            )

        # Effects
        match label:
            case cfg.BURNED:
                if not is_unset:
                    logged_assert(
                        _is_arc54_compliant(asset), err.ASA_NOT_ARC54_COMPLIANT
                    )
                    logged_assert(
                        address == TemplateVar[Account](ARC54_BURN_ADDRESS),
                        err.BURNED_ADDRESS_INVALID,
                    )
                self.circulating_supply[asset].burned_addr = address
            case cfg.CUSTOM_1:
                self.circulating_supply[asset].custom_1_addr = address
            case cfg.CUSTOM_2:
                self.circulating_supply[asset].custom_2_addr = address
            case cfg.CUSTOM_3:
                self.circulating_supply[asset].custom_3_addr = address
            case cfg.CUSTOM_4:
                self.circulating_supply[asset].custom_4_addr = address
            case _:
                logged_err(err.LABEL_INVALID)

        # Handle Not Idempotent
        if self.circulating_supply[asset] != config:
            self._emit_config_updated(asset)

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
        logged_assert(asset in self.circulating_supply, err.CONFIG_NOT_EXIST)
        asa_exists = _asa_exists(asset)
        if asa_exists:
            logged_assert(Txn.sender == asset.manager, err.UNAUTHORIZED)

        # Delete ASA Circulating Supply Configuration
        mbr_i = Global.current_application_address.min_balance
        del self.circulating_supply[asset]
        mbr_delta_amount = mbr_i - Global.current_application_address.min_balance

        # Refund MBR
        itxn.Payment(receiver=Txn.sender, amount=mbr_delta_amount).submit()

        arc4.emit(
            Arc62ConfigDeleted(
                asset_id=asset.id,
                round=Global.round,
                timestamp=Global.latest_timestamp,
                asa_exists=asa_exists,
            )
        )

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
        logged_assert(asset in self.circulating_supply, err.CONFIG_NOT_EXIST)
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
        logged_assert(asset in self.circulating_supply, err.CONFIG_NOT_EXIST)

        # Effects
        if not _asa_exists(asset):
            circulating_supply = UInt64(0)
        else:
            reserve = asset.reserve
            reserve_balance = (
                UInt64(0)
                if reserve == Global.zero_address or not reserve.is_opted_in(asset)
                else asset.balance(reserve)
            )

            # The Reserve Address can be changed after the labels are set: a label
            # assigned to the current Reserve Address is counted once, as reserve
            burned_addr = self.circulating_supply[asset].burned_addr
            burned_balance = (
                UInt64(0)
                if burned_addr == Global.zero_address
                or burned_addr == reserve
                or not burned_addr.is_opted_in(asset)
                else asset.balance(burned_addr)
            )

            custom_1_addr = self.circulating_supply[asset].custom_1_addr
            custom_balance_1 = (
                UInt64(0)
                if custom_1_addr == Global.zero_address
                or custom_1_addr == reserve
                or not custom_1_addr.is_opted_in(asset)
                else asset.balance(custom_1_addr)
            )

            custom_2_addr = self.circulating_supply[asset].custom_2_addr
            custom_balance_2 = (
                UInt64(0)
                if custom_2_addr == Global.zero_address
                or custom_2_addr == reserve
                or not custom_2_addr.is_opted_in(asset)
                else asset.balance(custom_2_addr)
            )

            custom_3_addr = self.circulating_supply[asset].custom_3_addr
            custom_balance_3 = (
                UInt64(0)
                if custom_3_addr == Global.zero_address
                or custom_3_addr == reserve
                or not custom_3_addr.is_opted_in(asset)
                else asset.balance(custom_3_addr)
            )

            custom_4_addr = self.circulating_supply[asset].custom_4_addr
            custom_balance_4 = (
                UInt64(0)
                if custom_4_addr == Global.zero_address
                or custom_4_addr == reserve
                or not custom_4_addr.is_opted_in(asset)
                else asset.balance(custom_4_addr)
            )

            circulating_supply = (
                asset.total
                - reserve_balance
                - burned_balance
                - custom_balance_1
                - custom_balance_2
                - custom_balance_3
                - custom_balance_4
            )

        return circulating_supply

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
