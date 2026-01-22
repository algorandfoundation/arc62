# mypy: ignore-errors

import json
import logging
import os
from typing import Final

from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AppClientCompilationParams,
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
from algosdk.encoding import decode_address
from asa_metadata_registry import (
    DEFAULT_DEPLOYMENTS,
    Arc90Compliance,
    Arc90Uri,
    AsaMetadataRegistry,
    AssetMetadata,
    IrreversibleFlags,
    MetadataFlags,
    ReversibleFlags,
)
from asa_metadata_registry._generated.asa_metadata_registry_client import (
    AsaMetadataRegistryClient,
    AsaMetadataRegistryFactory,
)
from asa_metadata_registry.deployments import RegistryDeployment

from helpers.bonfire import arc54_asset_opt_in
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    Arc62GetCirculatingSupplyArgs,
    CirculatingSupplyClient,
    CirculatingSupplyFactory,
    InitConfigArgs,
    SetNotCirculatingAddressArgs,
)
from smart_contracts.circulating_supply.config import ARC2_PREFIX, BURNED, CUSTOM
from smart_contracts.template_vars import ARC54_BURN_ADDRESS

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

METADATA_FLAGS = MetadataFlags(
    reversible=ReversibleFlags(arc62=True),
    irreversible=IrreversibleFlags(
        arc3=True, arc89_native=True, reserved_2=True, immutable=False
    ),  # TODO: update reserved_2 to burned on SDK update
)

BACKWARD_METADATA_FLAGS = MetadataFlags(
    reversible=ReversibleFlags(arc62=True),
    irreversible=IrreversibleFlags(immutable=False),
)

ARC3_METADATA_JSON = {
    "name": ASA_NAME,
    "description": "ASA with ARC'62 Circulating Supply",
    "decimals": ASA_DECIMALS,
    "unitName": ASA_UNIT_NAME,
    "properties": {
        "arc-62": {"application-id": 0}  # Update after Smart ASA App deployment
    },
}

DEPRECATED_BY = 0

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
    receiver: SigningAccount | None,
) -> None:
    if receiver is not None:
        _asset_opt_in(
            algorand=algorand,
            account=receiver,
            asset_id=asset_id,
        )
        receiver_address = receiver.address
    else:
        logger.info("Opting in Bonfire on TestNet...")
        arc54_asset_opt_in(
            algorand=algorand,
            caller=sender,
            asset_id=asset_id,
        )
        receiver_address = os.environ[ARC54_BURN_ADDRESS]

    _asset_transfer(
        algorand=algorand,
        sender=sender,
        asset_id=asset_id,
        amount=amount,
        receiver=receiver_address,
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
    algorand.set_default_validity_window(100)
    deployer = algorand.account.from_environment("DEPLOYER")
    logger.info(f"Deployer address: {deployer.address}")

    circulating = algorand.account.from_environment("CIRCULATING")

    if algorand.client.is_localnet():
        registry_app_factory = algorand.client.get_typed_app_factory(
            AsaMetadataRegistryFactory,
            default_sender=deployer.address,
        )

        registry_app_client, _ = registry_app_factory.deploy(
            compilation_params=AppClientCompilationParams(
                deploy_time_params={
                    "TRUSTED_DEPLOYER": deployer.public_key,
                    "ARC90_NETAUTH": "net:" + algorand.client.network().genesis_id,
                }
            )
        )

        algorand.account.ensure_funded_from_environment(
            account_to_fund=registry_app_client.app_address,
            min_spending_balance=ACCOUNT_MBR,
        )

        registry_client = AsaMetadataRegistry.from_app_client(
            app_client=registry_app_client, algod=algorand.client.algod
        )

        registry_deployment = RegistryDeployment(
            network=algorand.client.network().genesis_id,
            genesis_hash_b64=algorand.client.network().genesis_hash,
            app_id=registry_app_client.app_id,
            arc90_uri_netauth="net:" + algorand.client.network().genesis_id,
            creator_address=deployer.address,
        )
        non_circulating = algorand.account.from_environment("NON_CIRCULATING")
        non_circulating_address = non_circulating.address
        non_circulating_label = CUSTOM
    elif algorand.client.is_testnet():
        registry_deployment = DEFAULT_DEPLOYMENTS["testnet"]
        registry_app_client = algorand.client.get_typed_app_client_by_id(
            AsaMetadataRegistryClient,
            app_id=registry_deployment.app_id,
            default_sender=deployer.address,
            default_signer=deployer.signer,
        )
        registry_client = AsaMetadataRegistry.from_app_client(
            app_client=registry_app_client, algod=algorand.client.algod
        )
        non_circulating = None
        non_circulating_address = os.environ[ARC54_BURN_ADDRESS]
        non_circulating_label = BURNED
    else:
        raise OSError("Unsupported network for deployment")
    logger.info(f"ASA Metadata Registry deployment: {registry_deployment}")

    factory = algorand.client.get_typed_app_factory(
        CirculatingSupplyFactory,
        compilation_params=AppClientCompilationParams(
            deploy_time_params={
                ARC54_BURN_ADDRESS: decode_address(os.environ[ARC54_BURN_ADDRESS]),
            }
        ),
        default_sender=deployer.address,
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

    # Update Asset Metadata
    ARC3_METADATA_JSON["properties"]["arc-62"][
        "application-id"
    ] = circulating_supply_client.app_id

    # ARC-3 Circulating Supply App discovery
    # https://dev.algorand.co/arc-standards/arc-0062/#circulating-supply-application-discovery
    arc90_uri = Arc90Uri(
        netauth=registry_deployment.arc90_uri_netauth,
        app_id=registry_deployment.app_id,
        box_name=None,
        compliance=Arc90Compliance((54, 62, 89)),  # ARC-54, ARC-62, ARC-89
    )
    assert arc90_uri.is_partial
    logger.info(f"Smart ASA Metadata Partial URI: {arc90_uri.to_uri()}")

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
            url=arc90_uri.to_uri(),
            metadata_hash=ASA_METADATA_HASH,
            default_frozen=ASA_DEFAULT_FROZEN,
        )
    ).asset_id

    logger.info("Uploading ARC-3 metadata on the ASA Metadata Registry...")
    asa_metadata = AssetMetadata.from_json(
        asset_id=arc3_asset_id,
        json_obj=ARC3_METADATA_JSON,
        flags=METADATA_FLAGS,
        deprecated_by=DEPRECATED_BY,
        arc3_compliant=METADATA_FLAGS.irreversible.arc3,
    )

    registry_client.write.create_metadata(
        metadata=asa_metadata,
        asset_manager=deployer,
    )
    metadata = registry_client.read.get_asset_metadata(asset_id=arc3_asset_id)
    logger.info(f"ARC-89 ASA Metadata: {metadata.json}")

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
        label=non_circulating_label,
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

    ARC2_DATA["application-id"] = circulating_supply_client.app_id
    arc2_note = ARC2_PREFIX + ":j" + json.dumps(ARC2_DATA)
    logger.info(
        f"Setting Circulating Supply App discovery with ARC-2 note: {arc2_note}"
    )
    algorand.send.asset_config(
        params=AssetConfigParams(
            sender=deployer.address,
            asset_id=arc2_asset_id,
            manager=deployer.address,
            note=arc2_note.encode("utf-8"),
        )
    )

    logger.info("Uploading ARC-3 metadata on the ASA Metadata Registry...")
    asa_metadata = AssetMetadata.from_json(
        asset_id=arc2_asset_id,
        json_obj=ARC3_METADATA_JSON,
        flags=BACKWARD_METADATA_FLAGS,
        deprecated_by=DEPRECATED_BY,
        arc3_compliant=METADATA_FLAGS.irreversible.arc3,
    )

    registry_client.write.create_metadata(
        metadata=asa_metadata,
        asset_manager=deployer,
    )
    metadata = registry_client.read.get_asset_metadata(asset_id=arc2_asset_id)
    logger.info(f"ARC-89 ASA Metadata: {metadata.json}")

    arc2_circulating_supply = _set_label_and_get_circulating_supply(
        circulating_supply_client=circulating_supply_client,
        asset_id=arc2_asset_id,
        non_circulating_address=non_circulating_address,
        label=non_circulating_label,
        caller=deployer,
    )
    logger.info(f"ARC-2 discovery Circulating Supply: {arc2_circulating_supply}")
