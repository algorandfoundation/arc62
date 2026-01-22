from typing import Final

import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetCreateParams,
    AssetOptInParams,
    AssetTransferParams,
    CommonAppCallParams,
    PaymentParams,
    SigningAccount,
)
from algokit_utils.config import config
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
    CirculatingSupplyFactory,
    InitConfigArgs,
)

INITIAL_FUNDS: Final[AlgoAmount] = AlgoAmount(algo=100)

ASA_TOTAL: Final[int] = 100
RESERVE_BALANCE: Final[int] = 4
BURNED_BALANCE: Final[int] = 3
LOCKED_BALANCE: Final[int] = 2
CUSTOM_BALANCE: Final[int] = 1

ACCOUNT_MBR = AlgoAmount(micro_algo=100_000)
CONFIG_MBR = AlgoAmount(micro_algo=44_100)

config.configure(
    debug=False,
    populate_app_call_resources=True,
    # trace_all=True,
)


@pytest.fixture(scope="session")
def algorand() -> AlgorandClient:
    client = AlgorandClient.default_localnet()
    client.set_suggested_params_cache_timeout(0)
    return client


@pytest.fixture(scope="session")
def deployer(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="function")
def circulating_supply_client(
    algorand: AlgorandClient, deployer: SigningAccount
) -> CirculatingSupplyClient:
    factory = algorand.client.get_typed_app_factory(
        CirculatingSupplyFactory,
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


@pytest.fixture(scope="session")
def asset_creator(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def asset_manager(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def asset_reserve(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def burned_supply(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def locked_supply(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def custom_supply(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="function")
def asset(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    asset_manager: SigningAccount,
    asset_reserve: SigningAccount,
    circulating_supply_client: CirculatingSupplyClient,
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
    algorand.send.asset_opt_in(
        AssetOptInParams(
            sender=asset_reserve.address,
            signer=asset_reserve.signer,
            asset_id=asset,
        )
    )
    algorand.send.asset_transfer(
        AssetTransferParams(
            sender=asset_creator.address,
            signer=asset_creator.signer,
            asset_id=asset,
            amount=RESERVE_BALANCE,
            receiver=asset_reserve.address,
        )
    )
    assert (
        algorand.asset.get_account_information(asset_reserve, asset).balance
        == RESERVE_BALANCE
    )
    return asset_reserve


@pytest.fixture(scope="function")
def burned_balance(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    burned_supply: SigningAccount,
    asset: int,
) -> SigningAccount:
    algorand.send.asset_opt_in(
        AssetOptInParams(
            sender=burned_supply.address,
            signer=burned_supply.signer,
            asset_id=asset,
        )
    )
    algorand.send.asset_transfer(
        AssetTransferParams(
            sender=asset_creator.address,
            signer=asset_creator.signer,
            asset_id=asset,
            amount=BURNED_BALANCE,
            receiver=burned_supply.address,
        )
    )
    assert (
        algorand.asset.get_account_information(burned_supply, asset).balance
        == BURNED_BALANCE
    )
    return burned_supply


@pytest.fixture(scope="function")
def locked_balance(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    locked_supply: SigningAccount,
    asset: int,
) -> SigningAccount:
    algorand.send.asset_opt_in(
        AssetOptInParams(
            sender=locked_supply.address,
            signer=locked_supply.signer,
            asset_id=asset,
        )
    )
    algorand.send.asset_transfer(
        AssetTransferParams(
            sender=asset_creator.address,
            signer=asset_creator.signer,
            asset_id=asset,
            amount=LOCKED_BALANCE,
            receiver=locked_supply.address,
        )
    )
    assert (
        algorand.asset.get_account_information(locked_supply, asset).balance
        == LOCKED_BALANCE
    )
    return locked_supply


@pytest.fixture(scope="function")
def custom_balance(
    algorand: AlgorandClient,
    asset_creator: SigningAccount,
    custom_supply: SigningAccount,
    asset: int,
) -> SigningAccount:
    algorand.send.asset_opt_in(
        AssetOptInParams(
            sender=custom_supply.address,
            signer=custom_supply.signer,
            asset_id=asset,
        )
    )
    algorand.send.asset_transfer(
        AssetTransferParams(
            sender=asset_creator.address,
            signer=asset_creator.signer,
            asset_id=asset,
            amount=CUSTOM_BALANCE,
            receiver=custom_supply.address,
        )
    )
    assert (
        algorand.asset.get_account_information(custom_supply, asset).balance
        == CUSTOM_BALANCE
    )
    return custom_supply


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
