# This file is auto-generated, do not modify
# flake8: noqa
# fmt: off
import typing

import algopy

class CirculatingSupplyConfig(algopy.arc4.Struct):
    burned_addr: algopy.arc4.Address
    custom_1_addr: algopy.arc4.Address
    custom_2_addr: algopy.arc4.Address
    custom_3_addr: algopy.arc4.Address
    custom_4_addr: algopy.arc4.Address

class CirculatingSupply(algopy.arc4.ARC4Client, typing.Protocol):
    """

        Singleton Application providing ARC-62 getter for ASA Circulating Supply
    
    """
    @algopy.arc4.abimethod
    def init_config(
        self,
        asset: algopy.arc4.UIntN[typing.Literal[64]],
        mbr_payment: algopy.gtxn.PaymentTransaction,
    ) -> algopy.arc4.UIntN[typing.Literal[64]]:
        """
        Non-normative: Initialize the circulating supply configuration for an ASA
        Authorization: ASA Manager Address.
        """

    @algopy.arc4.abimethod
    def set_not_circulating_address(
        self,
        asset: algopy.arc4.UIntN[typing.Literal[64]],
        address: algopy.arc4.Address,
        label: algopy.arc4.String,
    ) -> None:
        """
        Non-normative: Set not-circulating supply addresses
        Authorization: ASA Manager Address.
        """

    @algopy.arc4.abimethod
    def delete_config(
        self,
        asset: algopy.arc4.UIntN[typing.Literal[64]],
    ) -> algopy.arc4.UIntN[typing.Literal[64]]:
        """
        Non-normative: Delete the circulating supply configuration for an ASA
        Authorization: ASA Manager Address.
        """

    @algopy.arc4.abimethod(readonly=True)
    def get_config(
        self,
        asset: algopy.arc4.UIntN[typing.Literal[64]],
    ) -> CirculatingSupplyConfig:
        """
        Non-normative: Get ASA circulating supply configuration.
        """

    @algopy.arc4.abimethod(readonly=True)
    def arc62_get_circulating_supply(
        self,
        asset_id: algopy.arc4.UIntN[typing.Literal[64]],
    ) -> algopy.arc4.UIntN[typing.Literal[64]]:
        """
        Get ASA circulating supply.
        """

    @algopy.arc4.abimethod(readonly=True)
    def extra_resources(
        self,
    ) -> None:
        """
        Non-normative: Placeholder method to acquire AVM extra resources.
        """

    @algopy.arc4.abimethod
    def withdraw_balance_excess(
        self,
    ) -> None:
        """
        Non-normative: Method to withdraw balance excess due to accidental deposits
        (it should never happen if deposits match exactly the required MBR. Deleted config MBR is not included in the excess, since it is immediately returned on delete).
        """
