# ASA Circulating Supply

Reference implementation of a _singleton_ ASA Circulating Supply Application
providing the [ARC-62](https://github.com/algorandfoundation/ARCs/blob/main/ARCs/arc-0062.md) getter.

## Overview

A single Application serves the circulating supply of **any** ASA. Each ASA Manager
registers their ASA once, then labels the addresses whose balances must not count
as circulating. Anyone can then call `arc62_get_circulating_supply` to read the value.

The circulating supply is computed as:

```text
circulating_supply = total - reserve - burned - custom_1 - custom_2 - custom_3 - custom_4
```

| Label        | Address                                                    | Set by                                 |
|:-------------|:-----------------------------------------------------------|:---------------------------------------|
| _(reserve)_  | The ASA Reserve Address                                    | Automatic (from the ASA parameters)    |
| `burned`     | The network ARC-54 burn address (see the table below)      | ASA Manager, ARC-54 compliant ASA only |
| `custom_1-4` | Any address (e.g. treasury, vesting, locked, team wallets) | ASA Manager                            |

Unset labels (Zero Address), and addresses not opted in to the ASA, count as zero.
A labelled address that is also the current Reserve Address is counted once, as
reserve (the Reserve Address can be changed after the labels are set).
If the ASA has been destroyed, the circulating supply is `0`.

Each ASA configuration is stored in a box (keyed by the ASA ID) funded by the ASA
Manager. The MBR is **69,700 µALGO**, and it is refunded when the configuration
is deleted.

### Methods

| Method                                                        | Caller             | Description                                                                     |
|:--------------------------------------------------------------|:-------------------|:--------------------------------------------------------------------------------|
| `arc62_get_circulating_supply(uint64)uint64`                  | Anyone (read-only) | ARC-62 getter                                                                   |
| `init_config(uint64,pay)uint64`                               | ASA Manager        | Create the ASA configuration; requires an MBR payment to the App Address        |
| `set_not_circulating_address(uint64,address,string)void`      | ASA Manager        | Assign an address to a label (`burned`, `custom_1`, …, `custom_4`)              |
| `get_config(uint64)(address,address,address,address,address)` | Anyone (read-only) | Read the ASA configuration                                                      |
| `delete_config(uint64)uint64`                                 | ASA Manager¹       | Delete the ASA configuration and refund the MBR to the caller (inner payment)   |
| `extra_resources()void`                                       | Anyone             | No-op, can be grouped with the getter to make room for more resource references |

¹ If the ASA has been destroyed, anyone can delete its configuration and claim
the MBR.

`set_not_circulating_address` requires the address to be opted in to the ASA. The
`burned` label also requires the ASA to have no Clawback Address
([ARC-54](https://github.com/algorandfoundation/ARCs/blob/main/ARCs/arc-0054.md)
compliance) and only accepts the network ARC-54 burn address. An address can be
assigned to one label only, and the current Reserve Address can not be assigned
to a label. Assigning the Zero Address unsets a label.

## Reference Implementation

The trusted deployments of the _singleton_ ASA Circulating Supply App are:

| NETWORK  |            GENESIS HASH (`base64`)             |    APP ID    | CREATOR ADDRESS                                              |
|:---------|:----------------------------------------------:|:------------:|:-------------------------------------------------------------|
| Main Net | `wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=` | `3748307760` | `XODGWLOMKUPTGL3ZV53H3GZZWMCTJVQ5B2BZICFD3STSLA2LPSH6V6RW3I` |
| Test Net | `SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=` | `774613064`  | `Q3ROBYOB5QODCSNZKDYLH33NO5V4FN3YKMOHE43RPPC2LUPG56DNSU446I` |

The ARC-54 burn addresses accepted for the `burned` label are:

| NETWORK  | ARC-54 BURN ADDRESS                                          |
|:---------|:-------------------------------------------------------------|
| Main Net | `BNFIREKGRXEHCFOEQLTX3PU5SUCMRKDU7WHNBGZA4SXPW42OAHZBP7BPHY` |
| Test Net | `3TKF2GMZJ5VZ4BQVQGC72BJ63WFN4QBPU2EUD4NQYHFLC3NE5D7GXHXYOQ` |

## Usage

The examples use the generated Python client
[`circulating_supply_client.py`](smart_contracts/artifacts/circulating_supply/circulating_supply_client.py)
with [AlgoKit Utils](https://github.com/algorandfoundation/algokit-utils-py).
Clients for other languages (e.g. TypeScript) can be generated from the
[ARC-56 App Spec](smart_contracts/artifacts/circulating_supply/CirculatingSupply.arc56.json):

```shell
algokit generate client smart_contracts/artifacts/circulating_supply/CirculatingSupply.arc56.json --output client.ts
```

### Get the circulating supply

Read-only methods are simulated, so no signature or fee is required: any address
works as sender.

```python
from algokit_utils import AlgorandClient

from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    Arc62GetCirculatingSupplyArgs,
    CirculatingSupplyClient,
)

algorand = AlgorandClient.testnet()

circulating_supply_client = CirculatingSupplyClient(
    algorand=algorand,
    app_id=774613064,
    default_sender="<ANY-ADDRESS>",
)

circulating_supply = circulating_supply_client.send.arc62_get_circulating_supply(
    args=Arc62GetCirculatingSupplyArgs(asset_id=774613081),
).abi_return
```

### Configure an ASA

The following calls must be signed by the ASA Manager.

```python
from algokit_utils import AlgoAmount, CommonAppCallParams, PaymentParams

from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    CirculatingSupplyClient,
    InitConfigArgs,
    SetNotCirculatingAddressArgs,
)

asset_manager = algorand.account.from_mnemonic(mnemonic="<ASA-MANAGER-MNEMONIC>")

circulating_supply_client = CirculatingSupplyClient(
    algorand=algorand,
    app_id=774613064,
    default_sender=asset_manager.address,
    default_signer=asset_manager.signer,
)

# 1. Initialize the ASA configuration, paying the box MBR
mbr_payment = algorand.create_transaction.payment(
    PaymentParams(
        sender=asset_manager.address,
        receiver=circulating_supply_client.app_address,
        amount=AlgoAmount(micro_algo=69_700),
    )
)
circulating_supply_client.send.init_config(
    args=InitConfigArgs(asset=asset_id, mbr_payment=mbr_payment),
)

# 2. Label the non-circulating addresses (they must be opted in to the ASA)
circulating_supply_client.send.set_not_circulating_address(
    args=SetNotCirculatingAddressArgs(
        asset=asset_id,
        address="<TREASURY-ADDRESS>",
        label="custom_1",
    ),
)

# ARC-54 compliant ASAs (no Clawback Address) can also label the burn address
circulating_supply_client.send.set_not_circulating_address(
    args=SetNotCirculatingAddressArgs(
        asset=asset_id,
        address="3TKF2GMZJ5VZ4BQVQGC72BJ63WFN4QBPU2EUD4NQYHFLC3NE5D7GXHXYOQ",
        label="burned",
    ),
)
```

A label can be reassigned at any time by calling `set_not_circulating_address`
again, or unset by assigning the Zero Address
(`AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ`).

> [!NOTE]
> The ARC-54 burn address must be opted in to the ASA before it can be labelled
> as `burned`. See [`helpers/bonfire.py`](helpers/bonfire.py) for an example.

### Read the ASA configuration

```python
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    GetConfigArgs,
)

config = circulating_supply_client.send.get_config(
    args=GetConfigArgs(asset=asset_id),
).abi_return

print(config.burned_addr, config.custom_1_addr)
```

The configuration can also be read directly from box storage, without an App call:

```python
config = circulating_supply_client.state.box.circulating_supply.get_value(asset_id)
```

### Delete the ASA configuration

`delete_config` refunds the MBR with an inner payment, so the caller must cover
the extra fee:

```python
from smart_contracts.artifacts.circulating_supply.circulating_supply_client import (
    DeleteConfigArgs,
)

circulating_supply_client.send.delete_config(
    args=DeleteConfigArgs(asset=asset_id),
    params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
)
```

### Discovery

To let clients find the Circulating Supply App for an ASA, link the App ID to the
ASA as described in the ARC-62 specification. The [deploy script](smart_contracts/circulating_supply/deploy_config.py)
shows end-to-end examples of both the ARC-3 metadata (stored on the
[ARC-89](https://github.com/algorandfoundation/arc89) ASA Metadata Registry) and
the ARC-2 note (backward compatibility) discovery methods.

## Development

Requires [AlgoKit](https://github.com/algorandfoundation/algokit-cli), Python 3.12,
and Poetry.

```shell
algokit project bootstrap all   # install dependencies
algokit localnet start          # start a local network
algokit project run build       # compile the contract and generate the client
algokit project run test        # run the tests on LocalNet
algokit project deploy localnet # deploy and run the example setup on LocalNet
```
