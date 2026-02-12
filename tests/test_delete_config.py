import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetDestroyParams,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError

from smart_contracts import errors as err
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
    DeleteConfigArgs,
)

from .conftest import CONFIG_MBR


def test_pass_delete_config(
    asset_manager: SigningAccount,
    asset: int,
    asset_circulating_supply_client: CirculatingSupplyClient,
) -> None:
    # Verify config exists before deletion
    config = asset_circulating_supply_client.state.box.circulating_supply.get_value(
        asset
    )
    assert config is not None

    # Delete the config (with extra fee to cover inner transaction)
    min_fee = asset_circulating_supply_client.algorand.get_suggested_params().min_fee
    result = asset_circulating_supply_client.send.delete_config(
        args=DeleteConfigArgs(asset=asset),
        params=CommonAppCallParams(
            sender=asset_manager.address,
            extra_fee=AlgoAmount(micro_algo=min_fee),
        ),
    )

    # Verify MBR was returned
    assert result.abi_return == CONFIG_MBR

    with pytest.raises(AlgodHTTPError, match="box not found"):
        asset_circulating_supply_client.state.box.circulating_supply.get_value(asset)


def test_pass_delete_config_for_deleted_asset(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    asset_manager: SigningAccount,
    asset: int,
    asset_circulating_supply_client: CirculatingSupplyClient,
) -> None:
    # Delete the ASA - all balance is currently held by creator, need manager to delete
    algorand.send.asset_destroy(
        AssetDestroyParams(
            sender=asset_manager.address,
            signer=asset_manager.signer,
            asset_id=asset,
        )
    )

    # Delete config should succeed even though ASA is deleted (no auth check)
    # Any account can delete config for deleted ASA
    min_fee = asset_circulating_supply_client.algorand.get_suggested_params().min_fee
    result = asset_circulating_supply_client.send.delete_config(
        args=DeleteConfigArgs(asset=asset),
        params=CommonAppCallParams(
            sender=asset_creator.address,
            extra_fee=AlgoAmount(micro_algo=min_fee),
        ),
    )

    assert result.abi_return == CONFIG_MBR


def test_fail_unauthorized(
    asset_creator: SigningAccount,
    asset: int,
    asset_circulating_supply_client: CirculatingSupplyClient,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        asset_circulating_supply_client.send.delete_config(
            args=DeleteConfigArgs(asset=asset),
            params=CommonAppCallParams(sender=asset_creator.address),
        )


def test_fail_config_not_exists(
    asset_manager: SigningAccount,
    asset: int,
    circulating_supply_client: CirculatingSupplyClient,
) -> None:
    with pytest.raises(LogicError, match=err.CONFIG_NOT_EXISTS):
        circulating_supply_client.send.delete_config(
            args=DeleteConfigArgs(asset=asset),
            params=CommonAppCallParams(sender=asset_manager.address),
        )
