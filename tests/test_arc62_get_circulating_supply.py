import pytest
from algokit_utils import (
    AlgorandClient,
    AssetConfigParams,
    AssetDestroyParams,
    AssetTransferParams,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from algosdk.constants import ZERO_ADDRESS

from smart_contracts import errors as err
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    Arc62GetCirculatingSupplyArgs,
    CirculatingSupplyClient,
    SetNotCirculatingAddressArgs,
)
from smart_contracts.circulating_supply import config as cfg

from .conftest import CUSTOM_BALANCE_1, RESERVE_BALANCE


def _get_circulating_supply(client: CirculatingSupplyClient, asset: int) -> int:
    return client.send.arc62_get_circulating_supply(
        args=Arc62GetCirculatingSupplyArgs(asset_id=asset)
    ).abi_return


def _set_not_circulating_address(
    client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
    address: str,
    label: str,
) -> None:
    client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(asset=asset, address=address, label=label),
        params=CommonAppCallParams(sender=asset_manager.address),
    )


def test_pass_get_circulating_supply(
    algorand: AlgorandClient,
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
    reserve_with_balance: SigningAccount,
    burned_balance: SigningAccount,
    custom_balance_1: SigningAccount,
    custom_balance_2: SigningAccount,
    custom_balance_3: SigningAccount,
    custom_balance_4: SigningAccount,
) -> None:
    total = algorand.asset.get_by_id(asset).total
    reserve_balance = algorand.asset.get_account_information(
        reserve_with_balance, asset
    ).balance

    def balance(acct: SigningAccount) -> int:
        return algorand.asset.get_account_information(acct, asset).balance

    nc_accounts = [
        (cfg.BURNED, burned_balance),
        (cfg.CUSTOM_1, custom_balance_1),
        (cfg.CUSTOM_2, custom_balance_2),
        (cfg.CUSTOM_3, custom_balance_3),
        (cfg.CUSTOM_4, custom_balance_4),
    ]
    nc_balances = {label: balance(acct) for label, acct in nc_accounts}

    print("\nASA Total: ", total)
    print("Reserve Balance: ", reserve_balance)
    for label, _acct in nc_accounts:
        print(f"{label.capitalize()} Balance: ", nc_balances[label])

    def get_circulating_supply() -> int:
        return asset_circulating_supply_client.send.arc62_get_circulating_supply(
            args=Arc62GetCirculatingSupplyArgs(asset_id=asset)
        ).abi_return

    def set_nc_address(label: str, acct: SigningAccount) -> None:
        asset_circulating_supply_client.send.set_not_circulating_address(
            args=SetNotCirculatingAddressArgs(
                asset=asset,
                address=acct.address,
                label=label,
            ),
            params=CommonAppCallParams(sender=asset_manager.address),
        )

    expected = total - reserve_balance

    circulating_supply = get_circulating_supply()
    assert circulating_supply == expected

    for label, acct in nc_accounts:
        set_nc_address(label, acct)
        expected -= nc_balances[label]
        circulating_supply = get_circulating_supply()
        assert circulating_supply == expected

    print("Circulating Supply: ", circulating_supply)


def test_pass_no_reserve(
    algorand: AlgorandClient,
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
) -> None:
    total = algorand.asset.get_by_id(asset).total
    algorand.send.asset_config(
        AssetConfigParams(
            sender=asset_manager.address,
            signer=asset_manager.signer,
            asset_id=asset,
            manager=asset_manager.address,
            reserve="",
        ),
    )
    circulating_supply = (
        asset_circulating_supply_client.send.arc62_get_circulating_supply(
            args=Arc62GetCirculatingSupplyArgs(asset_id=asset),
        ).abi_return
    )
    assert circulating_supply == total


def test_pass_closed_address(
    algorand: AlgorandClient,
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_creator: SigningAccount,
    asset_manager: SigningAccount,
    reserve_with_balance: SigningAccount,
    burned_balance: SigningAccount,
    asset: int,
) -> None:
    total = algorand.asset.get_by_id(asset).total

    asset_circulating_supply_client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(
            asset=asset,
            address=burned_balance.address,
            label=cfg.BURNED,
        ),
        params=CommonAppCallParams(sender=asset_manager.address),
    )

    algorand.send.asset_transfer(
        AssetTransferParams(
            sender=burned_balance.address,
            signer=burned_balance.signer,
            asset_id=asset,
            amount=0,
            receiver=asset_creator.address,
            close_asset_to=asset_creator.address,
        ),
    )

    algorand.send.asset_transfer(
        AssetTransferParams(
            sender=reserve_with_balance.address,
            signer=reserve_with_balance.signer,
            asset_id=asset,
            amount=0,
            receiver=asset_creator.address,
            close_asset_to=asset_creator.address,
        ),
    )

    circulating_supply = (
        asset_circulating_supply_client.send.arc62_get_circulating_supply(
            args=Arc62GetCirculatingSupplyArgs(asset_id=asset),
        ).abi_return
    )
    assert circulating_supply == total


def test_pass_asa_not_exists(
    algorand: AlgorandClient,
    asset_manager: SigningAccount,
    asset: int,
    asset_circulating_supply_client: CirculatingSupplyClient,
) -> None:
    algorand.send.asset_destroy(
        AssetDestroyParams(
            sender=asset_manager.address,
            asset_id=asset,
        ),
    )
    circulating_supply = (
        asset_circulating_supply_client.send.arc62_get_circulating_supply(
            args=Arc62GetCirculatingSupplyArgs(asset_id=asset),
        ).abi_return
    )
    assert circulating_supply == 0


def test_pass_unset_label(
    algorand: AlgorandClient,
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
    reserve_with_balance: SigningAccount,
    custom_balance_1: SigningAccount,
) -> None:
    client = asset_circulating_supply_client
    total = algorand.asset.get_by_id(asset).total

    _set_not_circulating_address(
        client, asset_manager, asset, custom_balance_1.address, cfg.CUSTOM_1
    )
    assert (
        _get_circulating_supply(client, asset)
        == total - RESERVE_BALANCE - CUSTOM_BALANCE_1
    )

    _set_not_circulating_address(
        client, asset_manager, asset, ZERO_ADDRESS, cfg.CUSTOM_1
    )
    assert _get_circulating_supply(client, asset) == total - RESERVE_BALANCE


@pytest.mark.parametrize(
    ("label", "labelled_fixture"),
    [
        (cfg.BURNED, "burned_balance"),
        (cfg.CUSTOM_1, "custom_balance_1"),
        (cfg.CUSTOM_2, "custom_balance_2"),
        (cfg.CUSTOM_3, "custom_balance_3"),
        (cfg.CUSTOM_4, "custom_balance_4"),
    ],
)
def test_pass_reserve_assigned_to_label(
    request: pytest.FixtureRequest,
    algorand: AlgorandClient,
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
    reserve_with_balance: SigningAccount,
    label: str,
    labelled_fixture: str,
) -> None:
    client = asset_circulating_supply_client
    total = algorand.asset.get_by_id(asset).total
    labelled: SigningAccount = request.getfixturevalue(labelled_fixture)
    labelled_balance = algorand.asset.get_account_information(labelled, asset).balance

    def set_reserve(reserve: str) -> None:
        algorand.send.asset_config(
            AssetConfigParams(
                sender=asset_manager.address,
                signer=asset_manager.signer,
                asset_id=asset,
                manager=asset_manager.address,
                reserve=reserve,
            ),
        )

    _set_not_circulating_address(client, asset_manager, asset, labelled.address, label)
    expected = total - RESERVE_BALANCE - labelled_balance
    assert _get_circulating_supply(client, asset) == expected

    # The Reserve Address is changed to the labelled address: counted once
    set_reserve(labelled.address)
    assert _get_circulating_supply(client, asset) == total - labelled_balance

    # The Reserve Address is changed back: the label counts again
    set_reserve(reserve_with_balance.address)
    assert _get_circulating_supply(client, asset) == expected


def test_fail_config_not_exists(
    circulating_supply_client: CirculatingSupplyClient,
    asset: int,
) -> None:
    with pytest.raises(LogicError, match=err.CONFIG_NOT_EXISTS):
        circulating_supply_client.send.arc62_get_circulating_supply(
            args=Arc62GetCirculatingSupplyArgs(asset_id=asset),
        )
