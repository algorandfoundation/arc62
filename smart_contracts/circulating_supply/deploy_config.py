# mypy: ignore-errors

import json
import logging
from typing import Final

from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetConfigParams,
    AssetCreateParams,
    AssetOptInParams,
    AssetTransferParams,
    CommonAppCallParams,
    OnSchemaBreak,
    OnUpdate,
    OperationPerformed,
    PaymentParams,
    SigningAccount,
)
from algokit_utils.config import config

from helpers import ipfs
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    Arc62GetCirculatingSupplyArgs,
    CirculatingSupplyClient,
    CirculatingSupplyFactory,
    InitConfigArgs,
    SetNotCirculatingAddressArgs,
)
from smart_contracts.circulating_supply.config import ARC2_PREFIX, BURNED, IPFS_URI

logger = logging.getLogger(__name__)

ACCOUNT_MBR = AlgoAmount(micro_algo=100_000)
CONFIG_MBR = AlgoAmount(micro_algo=44_100)

# ==============================================================================
# ASSET CREATION PARAMETERS
# ==============================================================================

ASA_TOTAL: Final[int] = 42
ASA_DECIMALS: Final[int] = 0
ASA_DEFAULT_FROZEN: Final[bool] = False
ASA_UNIT_NAME: Final[str] = "ARC-62"
ASA_NAME: Final[str] = "ARC-62 Circulating Supply"
ASA_METADATA_HASH: Final[bytes] = 32 * b"\x00"  # Mutable metadata

# ==============================================================================
# ASSET METADATA
# ==============================================================================

ARC3_METADATA_JSON = {
    "name": ASA_NAME,
    "description": "ASA with ARC'62 Circulating Supply",
    "decimals": ASA_DECIMALS,
    "unitName": ASA_UNIT_NAME,
    "properties": {
        "arc-62": {"application-id": 0}  # Update after Smart ASA App deployment
    },
}

# ==============================================================================
# ARC-2 NOTE
# ==============================================================================
ARC2_DATA: dict[str, int] = {
    "application-id": 0
}  # Update after Smart ASA App deployment


def _asset_opt_in(
    *, algorand: AlgorandClient, account: SigningAccount, asset_id: int
) -> None:
    algorand.send.asset_opt_in(
        AssetOptInParams(sender=account.address, asset_id=asset_id)
    )


def _asset_transfer(
    *,
    algorand: AlgorandClient,
    sender: SigningAccount,
    asset_id: int,
    amount: int,
    receiver: str,
) -> None:
    algorand.send.asset_transfer(
        AssetTransferParams(
            sender=sender.address,
            asset_id=asset_id,
            amount=amount,
            receiver=receiver,
        )
    )


def _opt_in_and_transfer(
    *,
    algorand: AlgorandClient,
    asset_id: int,
    sender: SigningAccount,
    amount: int,
    receiver: SigningAccount,
) -> None:
    _asset_opt_in(
        algorand=algorand,
        account=receiver,
        asset_id=asset_id,
    )
    _asset_transfer(
        algorand=algorand,
        sender=sender,
        asset_id=asset_id,
        amount=amount,
        receiver=receiver.address,
    )


def _set_label_and_get_circulating_supply(
    *,
    circulating_supply_client: CirculatingSupplyClient,
    asset_id: int,
    non_circulating_address: str,
    label: str,
    caller: SigningAccount,
) -> int | None:
    circulating_supply_client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(
            asset=asset_id,
            address=non_circulating_address,
            label=label,
        ),
        params=CommonAppCallParams(sender=caller.address),
    )
    return circulating_supply_client.send.arc62_get_circulating_supply(
        args=Arc62GetCirculatingSupplyArgs(asset_id=asset_id),
        params=CommonAppCallParams(sender=caller.address),
    ).abi_return


def deploy() -> None:
    config.configure(
        debug=False,
        populate_app_call_resources=True,
    )

    algorand = AlgorandClient.from_environment()
    algorand.set_default_validity_window(20)
    deployer = algorand.account.from_environment("DEPLOYER")
    logger.info(f"Deployer address: {deployer.address}")

    non_circulating = algorand.account.from_environment("NON_CIRCULATING")
    circulating = algorand.account.from_environment("CIRCULATING")
    non_circulating_address = non_circulating.address

    factory = algorand.client.get_typed_app_factory(
        CirculatingSupplyFactory, default_sender=deployer.address
    )

    circulating_supply_client, deploy_result = factory.deploy(
        on_schema_break=OnSchemaBreak.AppendApp,
        on_update=OnUpdate.AppendApp,
    )
    logger.info(
        f"Circulating Supply Application ID: {circulating_supply_client.app_id}"
    )
    if deploy_result.operation_performed.name == OperationPerformed.Create.name:
        algorand.send.payment(
            PaymentParams(
                amount=ACCOUNT_MBR,
                sender=deployer.address,
                receiver=circulating_supply_client.app_address,
            )
        )

    # ARC-3 Circulating Supply App discovery
    # https://dev.algorand.co/arc-standards/arc-0062/#circulating-supply-application-discovery
    arc3_data_cid = ""
    if algorand.client.is_testnet():
        logger.info("Uploading ARC-3 metadata on IPFS")
        jwt = ipfs.get_pinata_jwt().strip()
        # Update Asset Metadata
        ARC3_METADATA_JSON["properties"]["arc-62"][
            "application-id"
        ] = circulating_supply_client.app_id
        arc3_data_cid = ipfs.upload_to_pinata(ARC3_METADATA_JSON, jwt, ASA_UNIT_NAME)
        logger.info(f"Upload complete. ARC-3 metadata CID: {arc3_data_cid}")

    logger.info("Creating ARC-3 discovery Circulating Supply ASA...")
    arc3_asset_id = algorand.send.asset_create(
        AssetCreateParams(
            sender=deployer.address,
            signer=deployer.signer,
            asset_name=ASA_NAME + "@arc3",
            unit_name=ASA_UNIT_NAME,
            total=ASA_TOTAL,
            decimals=ASA_DECIMALS,
            manager=deployer.address,
            reserve=deployer.address,
            url=IPFS_URI + arc3_data_cid,
            metadata_hash=ASA_METADATA_HASH,
            default_frozen=ASA_DEFAULT_FROZEN,
        )
    ).asset_id

    _opt_in_and_transfer(
        algorand=algorand,
        asset_id=arc3_asset_id,
        sender=deployer,
        amount=1,
        receiver=non_circulating,
    )
    _opt_in_and_transfer(
        algorand=algorand,
        asset_id=arc3_asset_id,
        sender=deployer,
        amount=1,
        receiver=circulating,
    )

    logger.info("Setting ARC-3 discovery Circulating Supply App...")
    mbr_payment = algorand.create_transaction.payment(
        PaymentParams(
            sender=deployer.address,
            receiver=circulating_supply_client.app_address,
            amount=CONFIG_MBR,
        )
    )
    circulating_supply_client.send.init_config(
        args=InitConfigArgs(asset=arc3_asset_id, mbr_payment=mbr_payment),
        params=CommonAppCallParams(sender=deployer.address),
    )
    arc3_circulating_supply = _set_label_and_get_circulating_supply(
        circulating_supply_client=circulating_supply_client,
        asset_id=arc3_asset_id,
        non_circulating_address=non_circulating_address,
        label=BURNED,
        caller=deployer,
    )
    logger.info(f"ARC-3 discovery Circulating Supply: {arc3_circulating_supply}")

    # ARC-2 Circulating Supply App discovery (backward compatibility)
    # https://dev.algorand.co/arc-standards/arc-0062/#backwards-compatibility
    logger.info("Creating ARC-2 discovery Circulating Supply ASA...")
    arc2_asset_id = algorand.send.asset_create(
        AssetCreateParams(
            sender=deployer.address,
            signer=deployer.signer,
            asset_name=ASA_NAME,
            unit_name=ASA_UNIT_NAME,
            total=ASA_TOTAL,
            decimals=ASA_DECIMALS,
            manager=deployer.address,
            metadata_hash=ASA_METADATA_HASH,
            default_frozen=ASA_DEFAULT_FROZEN,
        )
    ).asset_id

    _opt_in_and_transfer(
        algorand=algorand,
        asset_id=arc2_asset_id,
        sender=deployer,
        amount=1,
        receiver=non_circulating,
    )
    _opt_in_and_transfer(
        algorand=algorand,
        asset_id=arc2_asset_id,
        sender=deployer,
        amount=1,
        receiver=circulating,
    )

    logger.info("Setting ARC-2 discovery Circulating Supply App...")
    mbr_payment = algorand.create_transaction.payment(
        PaymentParams(
            sender=deployer.address,
            receiver=circulating_supply_client.app_address,
            amount=CONFIG_MBR,
        )
    )
    circulating_supply_client.send.init_config(
        args=InitConfigArgs(asset=arc2_asset_id, mbr_payment=mbr_payment),
        params=CommonAppCallParams(sender=deployer.address),
    )

    logger.info("Setting Circulating Supply App with ARC-2...")
    ARC2_DATA["application-id"] = circulating_supply_client.app_id
    arc2_note = ARC2_PREFIX + ":j" + json.dumps(ARC2_DATA)
    algorand.send.asset_config(
        params=AssetConfigParams(
            sender=deployer.address,
            asset_id=arc2_asset_id,
            manager=deployer.address,
            note=arc2_note.encode("utf-8"),
        )
    )

    arc2_circulating_supply = _set_label_and_get_circulating_supply(
        circulating_supply_client=circulating_supply_client,
        asset_id=arc2_asset_id,
        non_circulating_address=non_circulating_address,
        label=BURNED,
        caller=deployer,
    )
    logger.info(f"ARC-2 discovery Circulating Supply: {arc2_circulating_supply}")
