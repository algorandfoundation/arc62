from typing import Final

import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AppClientCompilationParams,
    AssetCreateParams,
    AssetOptInParams,
    AssetTransferParams,
    CommonAppCallParams,
    PaymentParams,
    SigningAccount,
)
from algokit_utils.config import config
from algosdk.encoding import decode_address

from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
    CirculatingSupplyFactory,
    InitConfigArgs,
)
from smart_contracts.circulating_supply.deploy_config import ACCOUNT_MBR, CONFIG_MBR
from smart_contracts.template_vars import ARC54_BURN_ADDRESS

INITIAL_FUNDS: Final[AlgoAmount] = AlgoAmount(algo=100)

ASA_TOTAL: Final[int] = 100
RESERVE_BALANCE: Final[int] = 1
BURNED_BALANCE: Final[int] = 2
CUSTOM_BALANCE_1: Final[int] = 3
CUSTOM_BALANCE_2: Final[int] = 4
CUSTOM_BALANCE_3: Final[int] = 5
CUSTOM_BALANCE_4: Final[int] = 6

config.configure(
    debug=False,
    populate_app_call_resources=True,
    # trace_all=True,
)


def _create_funded_account(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


def _create_account_with_asset_balance(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    receiver: SigningAccount,
    asset: int,
    amount: int,
) -> SigningAccount:
    algorand.send.asset_opt_in(
        AssetOptInParams(
            sender=receiver.address,
            signer=receiver.signer,
            asset_id=asset,
        )
    )
    algorand.send.asset_transfer(
        AssetTransferParams(
            sender=asset_creator.address,
            signer=asset_creator.signer,
            asset_id=asset,
            amount=amount,
            receiver=receiver.address,
        )
    )
    assert algorand.asset.get_account_information(receiver, asset).balance == amount
    return receiver


@pytest.fixture(scope="session")
def algorand() -> AlgorandClient:
    client = AlgorandClient.default_localnet()
    client.set_suggested_params_cache_timeout(0)
    return client


@pytest.fixture(scope="session")
def deployer(algorand: AlgorandClient) -> SigningAccount:
    return _create_funded_account(algorand)


@pytest.fixture(scope="session")
def asset_creator(algorand: AlgorandClient) -> SigningAccount:
    return _create_funded_account(algorand)


@pytest.fixture(scope="session")
def asset_manager(algorand: AlgorandClient) -> SigningAccount:
    return _create_funded_account(algorand)


@pytest.fixture(scope="session")
def asset_reserve(algorand: AlgorandClient) -> SigningAccount:
    return _create_funded_account(algorand)


@pytest.fixture(scope="session")
def burned_supply(algorand: AlgorandClient) -> SigningAccount:
    return _create_funded_account(algorand)


@pytest.fixture(scope="session")
def custom_supply_1(algorand: AlgorandClient) -> SigningAccount:
    return _create_funded_account(algorand)


@pytest.fixture(scope="session")
def custom_supply_2(algorand: AlgorandClient) -> SigningAccount:
    return _create_funded_account(algorand)


@pytest.fixture(scope="session")
def custom_supply_3(algorand: AlgorandClient) -> SigningAccount:
    return _create_funded_account(algorand)


@pytest.fixture(scope="session")
def custom_supply_4(algorand: AlgorandClient) -> SigningAccount:
    return _create_funded_account(algorand)


@pytest.fixture(scope="function")
def asset(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    asset_manager: SigningAccount,
    asset_reserve: SigningAccount,
) -> int:
    return algorand.send.asset_create(
        AssetCreateParams(
            sender=asset_creator.address,
            signer=asset_creator.signer,
            total=ASA_TOTAL,
            manager=asset_manager.address,
            reserve=asset_reserve.address,
            url="<asa-metadata-uri>",
        )
    ).asset_id


@pytest.fixture(scope="function")
def reserve_with_balance(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    asset_reserve: SigningAccount,
    asset: int,
) -> SigningAccount:
    return _create_account_with_asset_balance(
        algorand, asset_creator, asset_reserve, asset, RESERVE_BALANCE
    )


@pytest.fixture(scope="function")
def burned_balance(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    burned_supply: SigningAccount,
    asset: int,
) -> SigningAccount:
    return _create_account_with_asset_balance(
        algorand, asset_creator, burned_supply, asset, BURNED_BALANCE
    )


@pytest.fixture(scope="function")
def custom_balance_1(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    custom_supply_1: SigningAccount,
    asset: int,
) -> SigningAccount:
    return _create_account_with_asset_balance(
        algorand, asset_creator, custom_supply_1, asset, CUSTOM_BALANCE_1
    )


@pytest.fixture(scope="function")
def custom_balance_2(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    custom_supply_2: SigningAccount,
    asset: int,
) -> SigningAccount:
    return _create_account_with_asset_balance(
        algorand, asset_creator, custom_supply_2, asset, CUSTOM_BALANCE_2
    )


@pytest.fixture(scope="function")
def custom_balance_3(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    custom_supply_3: SigningAccount,
    asset: int,
) -> SigningAccount:
    return _create_account_with_asset_balance(
        algorand, asset_creator, custom_supply_3, asset, CUSTOM_BALANCE_3
    )


@pytest.fixture(scope="function")
def custom_balance_4(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    custom_supply_4: SigningAccount,
    asset: int,
) -> SigningAccount:
    return _create_account_with_asset_balance(
        algorand, asset_creator, custom_supply_4, asset, CUSTOM_BALANCE_4
    )


@pytest.fixture(scope="function")
def circulating_supply_client(
    algorand: AlgorandClient, deployer: SigningAccount, burned_supply: SigningAccount
) -> CirculatingSupplyClient:
    factory = algorand.client.get_typed_app_factory(
        CirculatingSupplyFactory,
        compilation_params=AppClientCompilationParams(
            deploy_time_params={
                ARC54_BURN_ADDRESS: decode_address(burned_supply.address),
            }
        ),
        default_sender=deployer.address,
        default_signer=deployer.signer,
    )
    client, _ = factory.send.create.bare()
    algorand.send.payment(
        params=PaymentParams(
            sender=deployer.address,
            receiver=client.app_address,
            amount=ACCOUNT_MBR,
        )
    )
    return client


@pytest.fixture(scope="function")
def asset_circulating_supply_client(
    circulating_supply_client: CirculatingSupplyClient,
    asset_manager: SigningAccount,
    asset: int,
) -> CirculatingSupplyClient:
    mbr_payment = circulating_supply_client.algorand.create_transaction.payment(
        PaymentParams(
            sender=asset_manager.address,
            receiver=circulating_supply_client.app_address,
            amount=CONFIG_MBR,
        )
    )

    circulating_supply_client.send.init_config(
        args=InitConfigArgs(asset=asset, mbr_payment=mbr_payment),
        params=CommonAppCallParams(sender=asset_manager.address),
    )
    return circulating_supply_client
