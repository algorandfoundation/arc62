# mypy: ignore-errors

import json
import os

from algokit_utils import AlgorandClient, SigningAccount
from algosdk import abi
from algosdk.atomic_transaction_composer import AtomicTransactionComposer

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
    algorand: AlgorandClient, account: SigningAccount, asset_id: int
) -> None:
    sp = algorand.get_suggested_params()
    atc = AtomicTransactionComposer()

    # ABI method call
    atc.add_method_call(
        app_id=int(os.environ["BONFIRE_APP_ID"]),
        method=iface.get_method_by_name("arc54_optIntoASA"),
        sender=account.address,
        sp=sp,
        signer=account.signer,
        method_args=[asset_id],
        foreign_assets=[asset_id],
    )
