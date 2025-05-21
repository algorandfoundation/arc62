import logging
import json
from typing import Final

import algokit_utils
from algokit_utils.config import config

from helpers import ipfs

logger = logging.getLogger(__name__)

ASA_NAME: Final[str] = "ARC-62 Test ASA"
ASA_UNIT_NAME: Final[str] = "ARC-62"
ASA_DECIMALS: Final[int] = 0
ASA_TOTAL: Final[int] = 42
APP_URI: Final[str] = "ipfs://"


def deploy() -> None:
    from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
        CirculatingSupplyFactory,
        SetAssetArgs,
    )

    config.configure(
        debug=False,
        populate_app_call_resources=True,
    )

    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer = algorand.account.from_environment("DEPLOYER")

    factory = algorand.client.get_typed_app_factory(
        CirculatingSupplyFactory, default_sender=deployer.address
    )

    # ARC-3 Circulating Supply App discovery
    # https://arc.algorand.foundation/ARCs/arc-0062#circulating-supply-application-discovery
    logger.info("Creating ARC-3 discovery Circulating Supply App...")
    arc3_app_client, _ = factory.send.create.bare(params=algokit_utils.CommonAppCallCreateParams(note="ARC-3".encode()))
    logger.info(f"ARC-3 discovery Circulating Supply App ID: {arc3_app_client.app_id}")
    arc3_data_cid = ""
    if not algorand.client.is_localnet():
        logger.info("Uploading ARC-3 metadata on IPFS")
        arc3_data = {
            "name": ASA_NAME,
            "decimals": ASA_DECIMALS,
            "description": "ASA with Circulating Supply App",
            "properties": {"arc-62": {"application-id": arc3_app_client.app_id}},
        }
        jwt = ipfs.get_pinata_jwt().strip()
        arc3_data_cid = ipfs.upload_to_pinata(arc3_data, jwt, ASA_UNIT_NAME)
        logger.info(f"Upload complete. ARC-3 metadata CID: {arc3_data_cid}")

    logger.info("Creating ARC-3 discovery Circulating Supply ASA...")
    arc3_asset_id = algorand.send.asset_create(
        algokit_utils.AssetCreateParams(
            sender=deployer.address,
            signer=deployer.signer,
            asset_name=ASA_NAME,
            unit_name=ASA_UNIT_NAME,
            total=ASA_TOTAL,
            decimals=ASA_DECIMALS,
            manager=deployer.address,
            url=APP_URI + arc3_data_cid,
        )
    ).asset_id
    logger.info("Setting ASA on ARC-3 discovery Circulating Supply App...")
    arc3_app_client.send.set_asset(args=SetAssetArgs(asset_id=arc3_asset_id))

    # ARC-2 Circulating Supply App discovery (backward compatibility)
    # https://arc.algorand.foundation/ARCs/arc-0062#backwards-compatibility
    logger.info("Creating ARC-2 discovery Circulating Supply ASA...")
    arc2_asset_id = algorand.send.asset_create(
        algokit_utils.AssetCreateParams(
            sender=deployer.address,
            signer=deployer.signer,
            asset_name=ASA_NAME,
            unit_name=ASA_UNIT_NAME,
            total=ASA_TOTAL,
            decimals=ASA_DECIMALS,
            manager=deployer.address,
        )
    ).asset_id

    logger.info("Creating ARC-2 discovery Circulating Supply App...")
    arc2_app_client, _ = factory.send.create.bare(params=algokit_utils.CommonAppCallCreateParams(note="ARC-2".encode()))
    logger.info(f"ARC-2 discovery Circulating Supply App ID: {arc2_app_client.app_id}")
    logger.info("Setting ASA on ARC-2 discovery Circulating Supply App...")
    arc2_app_client.send.set_asset(args=SetAssetArgs(asset_id=arc2_asset_id))
    arc2_data: dict[str, int] = {"application-id": arc2_app_client.app_id,}
    arc2_note = f"arc62:j" + json.dumps(arc2_data)
    logger.info("Setting Circulating Supply App with ARC-2...")
    algorand.send.asset_config(
        params=algokit_utils.AssetConfigParams(
            sender=deployer.address,
            asset_id=arc2_asset_id,
            manager=deployer.address,
            note=arc2_note.encode("utf-8"),
        )
    )
