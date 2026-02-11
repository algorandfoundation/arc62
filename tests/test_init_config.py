import pytest
from algokit_utils import (
    AlgoAmount,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)
from algosdk.constants import ZERO_ADDRESS

from smart_contracts import errors as err
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
    InitConfigArgs,
)
from tests.conftest import CONFIG_MBR


def test_pass_init_config(
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
) -> None:
    config = asset_circulating_supply_client.state.box.circulating_supply.get_value(
        asset
    )
    assert config is not None
    assert config.burned_addr == ZERO_ADDRESS
    assert config.locked_addr == ZERO_ADDRESS
    assert config.custom_1_addr == ZERO_ADDRESS
    assert config.custom_2_addr == ZERO_ADDRESS
    assert config.custom_3_addr == ZERO_ADDRESS
    assert config.custom_4_addr == ZERO_ADDRESS


def test_fail_unauthorized(
    circulating_supply_client: CirculatingSupplyClient,
    asset_creator: SigningAccount,
    asset: int,
) -> None:
    mbr_payment = circulating_supply_client.algorand.create_transaction.payment(
        PaymentParams(
            sender=asset_creator.address,
            receiver=circulating_supply_client.app_address,
            amount=CONFIG_MBR,
        )
    )

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        circulating_supply_client.send.init_config(
            args=InitConfigArgs(asset=asset, mbr_payment=mbr_payment),
            params=CommonAppCallParams(sender=asset_creator.address),
        )


def test_fail_config_exists(
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
) -> None:
    mbr_payment = asset_circulating_supply_client.algorand.create_transaction.payment(
        PaymentParams(
            sender=asset_manager.address,
            receiver=asset_circulating_supply_client.app_address,
            amount=CONFIG_MBR,
        )
    )

    with pytest.raises(LogicError, match=err.CONFIG_EXISTS):
        asset_circulating_supply_client.send.init_config(
            args=InitConfigArgs(asset=asset, mbr_payment=mbr_payment),
            params=CommonAppCallParams(sender=asset_manager.address),
        )


def test_fail_invalid_mbr_receiver(
    circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
) -> None:
    mbr_payment = circulating_supply_client.algorand.create_transaction.payment(
        PaymentParams(
            sender=asset_manager.address,
            receiver=asset_manager.address,
            amount=CONFIG_MBR,
        )
    )

    with pytest.raises(LogicError, match=err.INVALID_MBR_RECEIVER):
        circulating_supply_client.send.init_config(
            args=InitConfigArgs(asset=asset, mbr_payment=mbr_payment),
            params=CommonAppCallParams(sender=asset_manager.address),
        )


def test_fail_invalid_mbr_amount(
    circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
) -> None:
    mbr_payment = circulating_supply_client.algorand.create_transaction.payment(
        PaymentParams(
            sender=asset_manager.address,
            receiver=circulating_supply_client.app_address,
            amount=AlgoAmount(micro_algo=0),
        )
    )

    with pytest.raises(LogicError, match=err.INVALID_MBR_AMOUNT):
        circulating_supply_client.send.init_config(
            args=InitConfigArgs(asset=asset, mbr_payment=mbr_payment),
            params=CommonAppCallParams(sender=asset_manager.address),
        )
