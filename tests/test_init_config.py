import pytest
from algokit_utils import (
    AlgoAmount,
    AssetDestroyParams,
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
from tests.conftest import ARC62_CONFIG_UPDATED, CONFIG_MBR, get_arc28_events


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
    assert config.custom_1_addr == ZERO_ADDRESS
    assert config.custom_2_addr == ZERO_ADDRESS
    assert config.custom_3_addr == ZERO_ADDRESS
    assert config.custom_4_addr == ZERO_ADDRESS


def test_pass_init_config_event(
    circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
) -> None:
    mbr_payment = circulating_supply_client.algorand.create_transaction.payment(
        PaymentParams(
            sender=asset_manager.address,
            receiver=circulating_supply_client.app_address,
            amount=CONFIG_MBR,
        )
    )
    result = circulating_supply_client.send.init_config(
        args=InitConfigArgs(asset=asset, mbr_payment=mbr_payment),
        params=CommonAppCallParams(sender=asset_manager.address),
    )

    events = get_arc28_events(result, ARC62_CONFIG_UPDATED)
    assert len(events) == 1
    asset_id, event_round, timestamp, *config = events[0]
    assert asset_id == asset
    assert event_round == result.confirmation["confirmed-round"]
    assert timestamp > 0
    assert config == 5 * [ZERO_ADDRESS]


def test_fail_asa_not_exist(
    circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
) -> None:
    circulating_supply_client.algorand.send.asset_destroy(
        AssetDestroyParams(sender=asset_manager.address, asset_id=asset)
    )
    mbr_payment = circulating_supply_client.algorand.create_transaction.payment(
        PaymentParams(
            sender=asset_manager.address,
            receiver=circulating_supply_client.app_address,
            amount=CONFIG_MBR,
        )
    )

    with pytest.raises(LogicError, match=err.ASA_NOT_EXIST):
        circulating_supply_client.send.init_config(
            args=InitConfigArgs(asset=asset, mbr_payment=mbr_payment),
            params=CommonAppCallParams(sender=asset_manager.address),
        )


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

    with pytest.raises(LogicError, match=err.CONFIG_EXIST):
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

    with pytest.raises(LogicError, match=err.MBR_RECEIVER_INVALID):
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

    with pytest.raises(LogicError, match=err.MBR_AMOUNT_INVALID):
        circulating_supply_client.send.init_config(
            args=InitConfigArgs(asset=asset, mbr_payment=mbr_payment),
            params=CommonAppCallParams(sender=asset_manager.address),
        )
