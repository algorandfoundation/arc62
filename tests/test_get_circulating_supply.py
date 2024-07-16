from algokit_utils import OnCompleteCallParameters
from algokit_utils.beta.account_manager import AddressAndSigner
from algokit_utils.beta.algorand_client import AlgorandClient, AssetConfigParams

from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
)
from smart_contracts.circulating_supply import config as cfg

from .conftest import (
    ASA_TOTAL,
    BURNED_BALANCE,
    GENERIC_BALANCE,
    LOCKED_BALANCE,
    RESERVE_BALANCE,
)


def test_pass_get_circulating_supply(
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: AddressAndSigner,
    asset: int,
    reserve_with_balance: AddressAndSigner,
    burning_with_balance: AddressAndSigner,
    locking_with_balance: AddressAndSigner,
    generic_not_circulating_with_balance: AddressAndSigner,
) -> None:
    not_circulating_addresses = [
        reserve_with_balance.address,
        burning_with_balance.address,
        locking_with_balance.address,
        generic_not_circulating_with_balance.address,
    ]

    circulating_supply = asset_circulating_supply_client.arc62_get_circulating_supply(
        asset_id=asset,
        transaction_parameters=OnCompleteCallParameters(
            # TODO: Foreign resources should be auto-populated
            foreign_assets=[asset],
            accounts=[reserve_with_balance.address],
        ),
    ).return_value
    assert circulating_supply == ASA_TOTAL - RESERVE_BALANCE

    asset_circulating_supply_client.set_not_circulating_address(
        address=burning_with_balance.address,
        label=cfg.BURNED,
        transaction_parameters=OnCompleteCallParameters(
            sender=asset_manager.address,
            signer=asset_manager.signer,
            # TODO: Foreign resources should be auto-populated
            foreign_assets=[asset],
            accounts=[burning_with_balance.address],
        ),
    )
    circulating_supply = asset_circulating_supply_client.arc62_get_circulating_supply(
        asset_id=asset,
        transaction_parameters=OnCompleteCallParameters(
            # TODO: Foreign resources should be auto-populated
            foreign_assets=[asset],
            accounts=not_circulating_addresses,
        ),
    ).return_value
    assert circulating_supply == ASA_TOTAL - RESERVE_BALANCE - BURNED_BALANCE

    asset_circulating_supply_client.set_not_circulating_address(
        address=locking_with_balance.address,
        label=cfg.LOCKED,
        transaction_parameters=OnCompleteCallParameters(
            sender=asset_manager.address,
            signer=asset_manager.signer,
            # TODO: Foreign resources should be auto-populated
            foreign_assets=[asset],
            accounts=[locking_with_balance.address],
        ),
    )
    circulating_supply = asset_circulating_supply_client.arc62_get_circulating_supply(
        asset_id=asset,
        transaction_parameters=OnCompleteCallParameters(
            # TODO: Foreign resources should be auto-populated
            foreign_assets=[asset],
            accounts=not_circulating_addresses,
        ),
    ).return_value
    assert (
        circulating_supply
        == ASA_TOTAL - RESERVE_BALANCE - BURNED_BALANCE - LOCKED_BALANCE
    )

    asset_circulating_supply_client.set_not_circulating_address(
        address=generic_not_circulating_with_balance.address,
        label=cfg.GENERIC,
        transaction_parameters=OnCompleteCallParameters(
            sender=asset_manager.address,
            signer=asset_manager.signer,
            # TODO: Foreign resources should be auto-populated
            foreign_assets=[asset],
            accounts=[generic_not_circulating_with_balance.address],
        ),
    )
    circulating_supply = asset_circulating_supply_client.arc62_get_circulating_supply(
        asset_id=asset,
        transaction_parameters=OnCompleteCallParameters(
            # TODO: Foreign resources should be auto-populated
            foreign_assets=[asset],
            accounts=not_circulating_addresses,
        ),
    ).return_value
    assert (
        circulating_supply
        == ASA_TOTAL
        - RESERVE_BALANCE
        - BURNED_BALANCE
        - LOCKED_BALANCE
        - GENERIC_BALANCE
    )


def test_pass_no_reserve(
    algorand_client: AlgorandClient,
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: AddressAndSigner,
    asset: int,
) -> None:
    algorand_client.send.asset_config(
        AssetConfigParams(
            sender=asset_manager.address,
            signer=asset_manager.signer,
            asset_id=asset,
            manager=asset_manager.address,
            reserve="",
        ),
    )
    circulating_supply = asset_circulating_supply_client.arc62_get_circulating_supply(
        asset_id=asset,
        transaction_parameters=OnCompleteCallParameters(
            # TODO: Foreign resources should be auto-populated
            foreign_assets=[asset],
        ),
    ).return_value
    assert circulating_supply == ASA_TOTAL
