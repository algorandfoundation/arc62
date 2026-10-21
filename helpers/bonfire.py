# mypy: ignore-errors

import json
import os

from algokit_utils import AlgorandClient, SigningAccount
from algosdk import abi
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.logic import get_application_address
from algosdk.transaction import PaymentTxn

ASA_OPT_IN_MBR = 100_000  # microALGO

ARC54_INTERFACE = {
    "name": "ARC54",
    "desc": "Standardized application for burning ASAs",
    "methods": [
        {
            "name": "arc54_optIntoASA",
            "args": [
                {
                    "name": "asa",
                    "type": "asset",
                    "desc": "The asset to which the contract will opt in",
                }
            ],
            "desc": "A method to opt the contract into an ASA",
            "returns": {"type": "void", "desc": ""},
        },
        {
            "name": "createApplication",
            "desc": "",
            "returns": {"type": "void", "desc": ""},
            "args": [],
        },
    ],
}

# Parse ARC-4 interface + fetch method
iface = abi.Interface.from_json(json.dumps(ARC54_INTERFACE))


def arc54_asset_opt_in(
    algorand: AlgorandClient, caller: SigningAccount, asset_id: int
) -> None:
    bonfire_app_id = int(os.environ["BONFIRE_APP_ID"])
    bonfire_address = get_application_address(bonfire_app_id)
    atc = AtomicTransactionComposer()

    # ARC-54: callers fund the opt-in MBR not already covered by Bonfire spare balance
    bonfire_info = algorand.client.algod.account_info(bonfire_address)
    spare_balance = bonfire_info["amount"] - bonfire_info["min-balance"]
    mbr_shortfall = max(0, ASA_OPT_IN_MBR - spare_balance)
    if mbr_shortfall:
        atc.add_transaction(
            TransactionWithSigner(
                PaymentTxn(
                    sender=caller.address,
                    sp=algorand.get_suggested_params(),
                    receiver=bonfire_address,
                    amt=mbr_shortfall,
                ),
                caller.signer,
            )
        )

    # ABI method call (the fee covers the opt-in inner transaction)
    sp = algorand.get_suggested_params()
    sp.flat_fee = True
    sp.fee = 2 * sp.min_fee
    atc.add_method_call(
        app_id=bonfire_app_id,
        method=iface.get_method_by_name("arc54_optIntoASA"),
        sender=caller.address,
        sp=sp,
        signer=caller.signer,
        method_args=[asset_id],
        foreign_assets=[asset_id],
    )
    atc.execute(algorand.client.algod, wait_rounds=4)
