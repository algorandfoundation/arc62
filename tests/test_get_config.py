import pytest
from algokit_utils import CommonAppCallParams, LogicError, SigningAccount
from algosdk.constants import ZERO_ADDRESS

from smart_contracts import errors as err
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
    GetConfigArgs,
    SetNotCirculatingAddressArgs,
)
from smart_contracts.circulating_supply import config as cfg


def test_pass_get_default_config(
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset: int,
) -> None:
    result = asset_circulating_supply_client.send.get_config(
        args=GetConfigArgs(asset=asset),
    )

    config = result.abi_return
    assert config.burned_addr == ZERO_ADDRESS
    assert config.locked_addr == ZERO_ADDRESS
    assert config.custom_1_addr == ZERO_ADDRESS
    assert config.custom_2_addr == ZERO_ADDRESS
    assert config.custom_3_addr == ZERO_ADDRESS
    assert config.custom_4_addr == ZERO_ADDRESS


def test_pass_get_modified_config(
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
    burned_balance: SigningAccount,
    locked_balance: SigningAccount,
    custom_balance_1: SigningAccount,
    custom_balance_2: SigningAccount,
    custom_balance_3: SigningAccount,
    custom_balance_4: SigningAccount,
) -> None:
    # Set all addresses
    asset_circulating_supply_client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(
            asset=asset,
            address=burned_balance.address,
            label=cfg.BURNED,
        ),
        params=CommonAppCallParams(sender=asset_manager.address),
    )

    asset_circulating_supply_client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(
            asset=asset,
            address=locked_balance.address,
            label=cfg.LOCKED,
        ),
        params=CommonAppCallParams(sender=asset_manager.address),
    )

    asset_circulating_supply_client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(
            asset=asset,
            address=custom_balance_1.address,
            label=cfg.CUSTOM_1,
        ),
        params=CommonAppCallParams(sender=asset_manager.address),
    )

    asset_circulating_supply_client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(
            asset=asset,
            address=custom_balance_2.address,
            label=cfg.CUSTOM_2,
        ),
        params=CommonAppCallParams(sender=asset_manager.address),
    )

    asset_circulating_supply_client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(
            asset=asset,
            address=custom_balance_3.address,
            label=cfg.CUSTOM_3,
        ),
        params=CommonAppCallParams(sender=asset_manager.address),
    )

    asset_circulating_supply_client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(
            asset=asset,
            address=custom_balance_4.address,
            label=cfg.CUSTOM_4,
        ),
        params=CommonAppCallParams(sender=asset_manager.address),
    )

    # Get the config
    result = asset_circulating_supply_client.send.get_config(
        args=GetConfigArgs(asset=asset),
    )

    config = result.abi_return
    assert config.burned_addr == burned_balance.address
    assert config.locked_addr == locked_balance.address
    assert config.custom_1_addr == custom_balance_1.address
    assert config.custom_2_addr == custom_balance_2.address
    assert config.custom_3_addr == custom_balance_3.address
    assert config.custom_4_addr == custom_balance_4.address


def test_fail_config_not_exists(
    circulating_supply_client: CirculatingSupplyClient,
    asset: int,
) -> None:
    """Test failure when trying to get config for non-existent configuration"""
    with pytest.raises(LogicError, match=err.CONFIG_NOT_EXISTS):
        circulating_supply_client.send.get_config(
            args=GetConfigArgs(asset=asset),
        )
