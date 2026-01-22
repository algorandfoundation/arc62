from algokit_utils import (
    AlgorandClient,
    AssetConfigParams,
    AssetTransferParams,
    CommonAppCallParams,
    SigningAccount,
)

from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    Arc62GetCirculatingSupplyArgs,
    CirculatingSupplyClient,
    SetNotCirculatingAddressArgs,
)
from smart_contracts.circulating_supply import config as cfg


def test_pass_get_circulating_supply(
    algorand: AlgorandClient,
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
    reserve_with_balance: SigningAccount,
    burned_balance: SigningAccount,
    locked_balance: SigningAccount,
    custom_balance: SigningAccount,
) -> None:
    total = algorand.asset.get_by_id(asset).total
    reserve_balance = algorand.asset.get_account_information(
        reserve_with_balance, asset
    ).balance

    def balance(acct: SigningAccount) -> int:
        return algorand.asset.get_account_information(acct, asset).balance

    nc_accounts = [
        (cfg.BURNED, burned_balance),
        (cfg.LOCKED, locked_balance),
        (cfg.CUSTOM, custom_balance),
    ]
    nc_balances = {label: balance(acct) for label, acct in nc_accounts}

    print("\nASA Total: ", total)
    print("Reserve Balance: ", reserve_balance)
    for label, _acct in nc_accounts:
        print(f"{label.capitalize()} Balance: ", nc_balances[label])

    def get_circulating_supply() -> int:
        return (
            asset_circulating_supply_client.send.arc62_get_circulating_supply(
                args=Arc62GetCirculatingSupplyArgs(asset_id=asset)
            ).abi_return
        )

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


def test_pass_asa_not_exists() -> None:
    pass  # TODO


def test_fail_config_not_exists() -> None:
    pass  # TODO
