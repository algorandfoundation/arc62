import pytest
from algokit_utils import CommonAppCallParams, LogicError, SigningAccount

from smart_contracts import errors as err
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
    SetNotCirculatingAddressArgs,
)
from smart_contracts.circulating_supply import config as cfg


def test_pass_set_not_circulating_address(
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
    burned_balance: SigningAccount,
    locked_balance: SigningAccount,
    custom_balance: SigningAccount,
) -> None:
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
            address=custom_balance.address,
            label=cfg.CUSTOM,
        ),
        params=CommonAppCallParams(sender=asset_manager.address),
    )

    config = asset_circulating_supply_client.state.box.circulating_supply.get_value(
        asset
    )

    assert config.burned_addr == burned_balance.address
    assert config.locked_addr == locked_balance.address
    assert config.custom_addr == custom_balance.address


def test_fail_unauthorized(
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_creator: SigningAccount,
    asset: int,
    burned_balance: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        asset_circulating_supply_client.send.set_not_circulating_address(
            args=SetNotCirculatingAddressArgs(
                asset=asset,
                address=burned_balance.address,
                label=cfg.BURNED,
            ),
            params=CommonAppCallParams(sender=asset_creator.address),
        )


def test_fail_config_not_exists() -> None:
    pass  # TODO


def test_fail_not_opted_in(
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
) -> None:
    with pytest.raises(LogicError, match=err.NOT_OPTED_IN):
        asset_circulating_supply_client.send.set_not_circulating_address(
            args=SetNotCirculatingAddressArgs(
                asset=asset,
                address=asset_manager.address,
                label=cfg.BURNED,
            ),
            params=CommonAppCallParams(sender=asset_manager.address),
        )


def test_fail_invalid_label(
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
    burned_balance: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.INVALID_LABEL):
        asset_circulating_supply_client.send.set_not_circulating_address(
            args=SetNotCirculatingAddressArgs(
                asset=asset,
                address=burned_balance.address,
                label=cfg.BURNED + "spam",
            ),
            params=CommonAppCallParams(sender=asset_manager.address),
        )
