import json
import logging
from typing import Final

import algokit_utils
from algokit_utils.config import config

from helpers import ipfs
from smart_contracts.circulating_supply.config import ARC2_PREFIX, ARC3_SUFFIX, ARC3_URI

logger = logging.getLogger(__name__)

ASA_NAME: Final[str] = "ARC-62 Test ASA"
ASA_UNIT_NAME: Final[str] = "ARC-62"
ASA_DECIMALS: Final[int] = 0
ASA_TOTAL: Final[int] = 42


def deploy() -> None:
    from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
        Arc62GetCirculatingSupplyArgs,
        CirculatingSupplyFactory,
        SetAssetArgs,
        SetNotCirculatingAddressArgs,
    )
    from smart_contracts.circulating_supply.config import NOT_CIRCULATING_LABEL_1

    config.configure(
        debug=False,
        populate_app_call_resources=True,
    )

    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer = algorand.account.from_environment("DEPLOYER")
    non_circulating = algorand.account.from_environment("NON_CIRCULATING")
    circulating = algorand.account.from_environment("CIRCULATING")

    def get_last_round() -> int:
        return algorand.client.algod.status().get("last-round")  # type: ignore

    def asset_opt_in(account: algokit_utils.SigningAccount, asset_id: int) -> None:
        current_round = get_last_round()
        algorand.send.asset_opt_in(
            algokit_utils.AssetOptInParams(
                sender=account.address,
                signer=account.signer,
                asset_id=asset_id,
                first_valid_round=current_round,
                last_valid_round=current_round + 100,
            )
        )

    def asset_transfer(
        sender: algokit_utils.SigningAccount,
        asset_id: int,
        amount: int,
        receiver: str,
    ) -> None:
        current_round = get_last_round()
        algorand.send.asset_transfer(
            algokit_utils.AssetTransferParams(
                sender=sender.address,
                signer=sender.signer,
                asset_id=asset_id,
                amount=amount,
                receiver=receiver,
                first_valid_round=current_round,
                last_valid_round=current_round + 100,
            )
        )

    factory = algorand.client.get_typed_app_factory(
        CirculatingSupplyFactory, default_sender=deployer.address
    )

    # ARC-3 Circulating Supply App discovery
    # https://arc.algorand.foundation/ARCs/arc-0062#circulating-supply-application-discovery
    logger.info("Creating ARC-3 discovery Circulating Supply App...")
    current_round: int = algorand.client.algod.status().get("last-round")  # type: ignore
    arc3_app_client, _ = factory.send.create.bare(  # type: ignore
        params=algokit_utils.CommonAppCallCreateParams(
            first_valid_round=current_round, last_valid_round=current_round + 100
        )
    )
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
    current_round = get_last_round()
    arc3_asset_id = algorand.send.asset_create(
        algokit_utils.AssetCreateParams(
            sender=deployer.address,
            signer=deployer.signer,
            asset_name=ASA_NAME,
            unit_name=ASA_UNIT_NAME,
            total=ASA_TOTAL,
            decimals=ASA_DECIMALS,
            manager=deployer.address,
            reserve=deployer.address,
            url=ARC3_URI + arc3_data_cid + ARC3_SUFFIX,
            first_valid_round=current_round,
            last_valid_round=current_round + 100,
        )
    ).asset_id
    asset_opt_in(non_circulating, arc3_asset_id)
    asset_opt_in(circulating, arc3_asset_id)
    asset_transfer(deployer, arc3_asset_id, 1, non_circulating.address)
    asset_transfer(deployer, arc3_asset_id, 1, circulating.address)

    logger.info("Setting ARC-3 discovery Circulating Supply App...")
    current_round = get_last_round()
    arc3_app_client.send.set_asset(
        args=SetAssetArgs(asset_id=arc3_asset_id),
        params=algokit_utils.CommonAppCallParams(
            sender=deployer.address,
            first_valid_round=current_round,
            last_valid_round=current_round + 100,
        ),
    )
    arc3_app_client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(
            address=non_circulating.address,
            label=NOT_CIRCULATING_LABEL_1,
        ),
        params=algokit_utils.CommonAppCallParams(
            sender=deployer.address,
            first_valid_round=current_round,
            last_valid_round=current_round + 100,
        ),
    )

    current_round = get_last_round()
    arc3_circulating_supply = arc3_app_client.send.arc62_get_circulating_supply(
        args=Arc62GetCirculatingSupplyArgs(asset_id=arc3_asset_id),
        params=algokit_utils.CommonAppCallParams(
            sender=deployer.address,
            first_valid_round=current_round,
            last_valid_round=current_round + 100,
        ),
    ).abi_return
    logger.info(f"ARC-3 discovery Circulating Supply: {arc3_circulating_supply}")

    # ARC-2 Circulating Supply App discovery (backward compatibility)
    # https://arc.algorand.foundation/ARCs/arc-0062#backwards-compatibility
    logger.info("Creating ARC-2 discovery Circulating Supply ASA...")
    current_round = get_last_round()
    arc2_asset_id = algorand.send.asset_create(
        algokit_utils.AssetCreateParams(
            sender=deployer.address,
            signer=deployer.signer,
            asset_name=ASA_NAME,
            unit_name=ASA_UNIT_NAME,
            total=ASA_TOTAL,
            decimals=ASA_DECIMALS,
            manager=deployer.address,
            first_valid_round=current_round,
            last_valid_round=current_round + 100,
        )
    ).asset_id
    asset_opt_in(non_circulating, arc2_asset_id)
    asset_opt_in(circulating, arc2_asset_id)
    asset_transfer(deployer, arc2_asset_id, 1, non_circulating.address)
    asset_transfer(deployer, arc2_asset_id, 1, circulating.address)

    logger.info("Creating ARC-2 discovery Circulating Supply App...")
    current_round = get_last_round()
    arc2_app_client, _ = factory.send.create.bare(  # type: ignore
        params=algokit_utils.CommonAppCallCreateParams(
            first_valid_round=current_round, last_valid_round=current_round + 100
        )
    )
    logger.info(f"ARC-2 discovery Circulating Supply App ID: {arc2_app_client.app_id}")
    logger.info("Setting ARC-2 discovery Circulating Supply App...")
    current_round = get_last_round()
    arc2_app_client.send.set_asset(
        args=SetAssetArgs(asset_id=arc2_asset_id),
        params=algokit_utils.CommonAppCallParams(
            sender=deployer.address,
            first_valid_round=current_round,
            last_valid_round=current_round + 100,
        ),
    )
    arc2_data: dict[str, int] = {
        "application-id": arc2_app_client.app_id,
    }
    arc2_note = ARC2_PREFIX + ":j" + json.dumps(arc2_data)
    logger.info("Setting Circulating Supply App with ARC-2...")
    current_round = get_last_round()
    algorand.send.asset_config(
        params=algokit_utils.AssetConfigParams(
            sender=deployer.address,
            asset_id=arc2_asset_id,
            manager=deployer.address,
            note=arc2_note.encode("utf-8"),
            first_valid_round=current_round,
            last_valid_round=current_round + 100,
        )
    )
    arc2_app_client.send.set_not_circulating_address(
        args=SetNotCirculatingAddressArgs(
            address=non_circulating.address,
            label=NOT_CIRCULATING_LABEL_1,
        ),
        params=algokit_utils.CommonAppCallParams(
            sender=deployer.address,
            first_valid_round=current_round,
            last_valid_round=current_round + 100,
        ),
    )

    current_round = get_last_round()
    arc2_circulating_supply = arc2_app_client.send.arc62_get_circulating_supply(
        args=Arc62GetCirculatingSupplyArgs(asset_id=arc2_asset_id),
        params=algokit_utils.CommonAppCallParams(
            sender=deployer.address,
            first_valid_round=current_round,
            last_valid_round=current_round + 100,
        ),
    ).abi_return
    logger.info(f"ARC-2 discovery Circulating Supply: {arc2_circulating_supply}")
