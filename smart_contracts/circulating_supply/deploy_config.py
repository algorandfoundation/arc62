import logging
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

    app_client, _ = factory.deploy(
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
        on_update=algokit_utils.OnUpdate.AppendApp,
    )

    if not app_client.state.global_state.asset_id:
        arc3_data_cid = ""
        if not algorand.client.is_localnet():
            logger.info("Uploading AppSpec on IPFS")
            arc3_data = {
                "name": ASA_NAME,
                "decimals": ASA_DECIMALS,
                "description": "ASA with Circulating Supply App",
                "properties": {"arc-62": {"application-id": app_client.app_id}},
            }
            jwt = ipfs.get_pinata_jwt().strip()
            arc3_data_cid = ipfs.upload_to_pinata(arc3_data, jwt)

        asset_id = algorand.send.asset_create(
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

        app_client.send.set_asset(args=SetAssetArgs(asset_id=asset_id))
