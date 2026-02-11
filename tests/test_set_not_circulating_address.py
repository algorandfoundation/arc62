import pytest
from algokit_utils import (
    AlgorandClient,
    AssetCreateParams,
    AssetOptInParams,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)

from smart_contracts import errors as err
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
    InitConfigArgs,
    SetNotCirculatingAddressArgs,
)
from smart_contracts.circulating_supply import config as cfg

from .conftest import CONFIG_MBR


def test_pass_set_not_circulating_address(
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

    config = asset_circulating_supply_client.state.box.circulating_supply.get_value(
        asset
    )

    assert config.burned_addr == burned_balance.address
    assert config.locked_addr == locked_balance.address
    assert config.custom_1_addr == custom_balance_1.address
    assert config.custom_2_addr == custom_balance_2.address
    assert config.custom_3_addr == custom_balance_3.address
    assert config.custom_4_addr == custom_balance_4.address


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


def test_fail_config_not_exists(
    asset_manager: SigningAccount,
    asset: int,
    burned_balance: SigningAccount,
    circulating_supply_client: CirculatingSupplyClient,
) -> None:
    with pytest.raises(LogicError, match=err.CONFIG_NOT_EXISTS):
        circulating_supply_client.send.set_not_circulating_address(
            args=SetNotCirculatingAddressArgs(
                asset=asset,
                address=burned_balance.address,
                label=cfg.BURNED,
            ),
            params=CommonAppCallParams(sender=asset_manager.address),
        )


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


def test_fail_not_arc54_compliant(
    algorand: AlgorandClient,
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_creator: SigningAccount,
    asset_manager: SigningAccount,
    burned_balance: SigningAccount,
) -> None:
    # Create an asset with a clawback address (not ARC-54 compliant)
    non_compliant_asset = algorand.send.asset_create(
        AssetCreateParams(
            sender=asset_creator.address,
            signer=asset_creator.signer,
            total=100,
            manager=asset_manager.address,
            clawback=asset_creator.address,  # This makes it non-ARC-54 compliant
        )
    ).asset_id

    # Opt in the burned_balance account to the asset
    algorand.send.asset_opt_in(
        AssetOptInParams(
            sender=burned_balance.address,
            signer=burned_balance.signer,
            asset_id=non_compliant_asset,
        )
    )

    mbr_payment = asset_circulating_supply_client.algorand.create_transaction.payment(
        PaymentParams(
            sender=asset_manager.address,
            receiver=asset_circulating_supply_client.app_address,
            amount=CONFIG_MBR,
        )
    )

    asset_circulating_supply_client.send.init_config(
        args=InitConfigArgs(asset=non_compliant_asset, mbr_payment=mbr_payment),
        params=CommonAppCallParams(sender=asset_manager.address),
    )

    # Try to set burned address - should fail because asset is not ARC-54 compliant
    with pytest.raises(LogicError, match=err.ASA_NOT_ARC54_COMPLIANT):
        asset_circulating_supply_client.send.set_not_circulating_address(
            args=SetNotCirculatingAddressArgs(
                asset=non_compliant_asset,
                address=burned_balance.address,
                label=cfg.BURNED,
            ),
            params=CommonAppCallParams(sender=asset_manager.address),
        )


def test_fail_invalid_burning_address(
    asset_manager: SigningAccount,
    asset: int,
    locked_balance: SigningAccount,
    asset_circulating_supply_client: CirculatingSupplyClient,
) -> None:
    with pytest.raises(LogicError, match=err.INVALID_BURNING_ADDRESS):
        asset_circulating_supply_client.send.set_not_circulating_address(
            args=SetNotCirculatingAddressArgs(
                asset=asset,
                address=locked_balance.address,
                label=cfg.BURNED,
            ),
            params=CommonAppCallParams(sender=asset_manager.address),
        )
