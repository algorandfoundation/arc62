from algokit_utils import AlgorandClient, CommonAppCallParams, SigningAccount

from smart_contracts import errors as err
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
    DeleteConfigArgs,
    GetConfigArgs,
    SetNotCirculatingAddressArgs,
)

from .conftest import get_arc65_errors


def test_fail_logs_arc65_error(
    algorand: AlgorandClient,
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_creator: SigningAccount,
    asset: int,
) -> None:
    composer = (
        asset_circulating_supply_client.new_group()
        .delete_config(
            args=DeleteConfigArgs(asset=asset),
            params=CommonAppCallParams(sender=asset_creator.address),
        )
        .composer()
    )
    assert get_arc65_errors(algorand, composer) == [f"ERR:{err.UNAUTHORIZED}"]


def test_fail_readonly_logs_arc65_error(
    algorand: AlgorandClient,
    circulating_supply_client: CirculatingSupplyClient,
    asset: int,
) -> None:
    composer = (
        circulating_supply_client.new_group()
        .get_config(args=GetConfigArgs(asset=asset))
        .composer()
    )
    assert get_arc65_errors(algorand, composer) == [f"ERR:{err.CONFIG_NOT_EXIST}"]


def test_fail_logged_err_logs_arc65_error(
    algorand: AlgorandClient,
    asset_circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
    custom_balance_1: SigningAccount,
) -> None:
    composer = (
        asset_circulating_supply_client.new_group()
        .set_not_circulating_address(
            args=SetNotCirculatingAddressArgs(
                asset=asset, address=custom_balance_1.address, label="spam"
            ),
            params=CommonAppCallParams(sender=asset_manager.address),
        )
        .composer()
    )
    assert get_arc65_errors(algorand, composer) == [f"ERR:{err.LABEL_INVALID}"]
