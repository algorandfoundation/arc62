---
arc: XXX
title: ASA circulating supply
description: An ARC to standardize a getter method for ASA circulating supply
author: Cosimo Bassi (@cusma)
discussion-to: XXX
status: Draft
type: XXX
category: Interface
created: 2024-06-12
requires: 4, 22

---

## Abstract

This ARC introduces a standard for the definition of circulating supply for Algorand
Standard Assets (ASA) and its client-side retrieval.

## Motivation

Algorand Standard Asset (ASA) `total` supply is _defined_ upon ASA creation.

Creating an ASA on the ledger does imply its `total` supply is immediately “minted”
or “circulating”.  In fact, the semantic of token “minting” on Algorand is slightly
different from other blockchains: it is not coincident with the token units creation
on the ledger.

The Reserve Address, one of the 4 addresses of the ASA Role-Based-Access-Control
(RBAC), is used to identify the portion of ASA `total` supply not yet in circulation.
The Reserve Address has no “privilege” over the token: it is just a “logical” label
used (client-side) to classify an existing amount of ASA as “not in circulation”.

On Algorand, “minting” an amount of ASA units is equivalent to _moving that amount
out of the Reserve Address_.

> Users may assign the Reserve Address to a Smart Contract if they want to enforce
> specific “minting” policies over the ASA.

This semantic led to a simple and unsophisticated definition of ASA circulating
supply, widely provided by clients (wallets, explorers, etc.) as standard information:

`circulating_supply = total - reserve_balance`

Where `reserve_balance` is the ASA balance hold by the Reserve Address.

However, the simplicity of such definition, who fostered adoption across the Algorand
ecosystem, poses some limitations. Complex and sophisticated use-cases of ASA, such
as regulated stable-coins and tokenized securities among the others, require more
detailed and expressive definitions of circulating supply.

Example: an ASA could have “burned”, “locked” or “pre-minted” amounts of token,
not held in the Reserve Address, which _should not_ be considered as “circulating”
supply. This is not possible with the basic protocol definition.

This ARC proposes a standard ABI _read-only_ method (getter) to provide the circulating
supply of an ASA.

## Specification

The keywords "**MUST**", "**MUST NOT**", "**REQUIRED**", "**SHALL**", "**SHALL NOT**",
"**SHOULD**", "**SHOULD NOT**", "**RECOMMENDED**", "**MAY**", and "**OPTIONAL**"
in this document are to be interpreted as described in [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).

### ABI Method

A compliant ASA, with a circulating supply definition conforming to this ARC, **MUST**
implement the following _read-only_ (ARC-0022) method on an Application (also referred
as Circulating Supply App in this specification):

```json
{
    "name": "arcXXXX_get_circulating_supply",
    "desc": "Get ASA circulating supply",
    "args": [
        {
            "name": "asset_id",
            "type": "uint64",
            "desc": "ASA ID of the circulating supply"
        }
    ],
    "returns": {
        "type": "uint64",
        "desc": "ASA circulating supply"
    }
}
```

### Usage

The `arcXXX_get_circulating_supply` is a _read-only_ method (getter),whose calls
**SHOULD** be _simulated_.

External resources used by the implementation (if any) **SHOULD** be discovered
and autopopulated by the simulated method call.

#### Example 1

Let the ASA have `total` supply and a Reserve Address (i.e. not set to `ZeroAddress`).

Let the Reserve Address be assigned to an account different from the Circulating
Supply App Account.

Let `burned` be an external Burned Address dedicated to ASA burned supply.

Let `locked` be an external Locked Address dedicated to ASA locked supply.

The ASA issuer defines the _circulating supply_ as:

`circulating_supply = total - reserve_balance - burned_balance - locked_balance`

In this case the simulated read-only method call would autopopulate 1 external
reference for the ASA and 3 external reference accounts (Reserve, Burned and Locked).

#### Example 2

Let the ASA have `total` supply and _no_ Reserve Address (i.e. set to `ZeroAddress`).

Let the Reserve Address be assigned to an account different from the Circulating
Supply App Account.

Let `non_circulating_amount` be a UInt64 Global Var defined by the implementation
of the Circulating Supply App.

The ASA issuer defines the _circulating supply_ as:

`circulating_supply = total - non_circulating_amount`

In this case the simulated read-only method call would autopopulate just 1 external
reference for the ASA.

#### Circulating Supply Application discovery

TBD

## Rationale

The definition of _circulating supply_ for sophisticated use-cases is always ASA-specific.
It could involve, for example, calculations requiring complex math or external accounts’
balances, variables stored in boxes or in global state, etc.

For this reason, the standard method’s signature does not require any reference
to external resources, a part form the `asset_id` of the ASA for which the circulating
supply is requested.

Eventual external resources can be discovered and autopopulated directly by the
simulated method call.

The rational of this design choice is avoiding integration overhead for clients (wallets,
explorers, etc.).

Clients just need to know:

1. The ASA ID;
1. The Circulating Supply App ID implementing the `arcXXX_get_circulating_supply`
method for that ASA.

## Reference Implementation

This section describes the recommendations for the reference implementation of the
Circulating Supply App.

An ASA using the reference implementation **SHOULD NOT** assign the Reserve Address
to the Application Account.

A reference implementation **SHOULD** declare, at least, the following Global State
variables:

- `asset_id` as UInt64, initialized to `0` and set _once_ by the ASA Manager Address;
- `burned` address as Bytes, initialized to the Global `Zero Address` and set by
the ASA Manager Address;
- `locke`d address as Bytes, initialized to the Global `Zero Address` and set by
the ASA Manager Address;
- `generic` address as Bytes, initialized to the Global `Zero Address` and set by
the ASA Manager Address.

A reference implementation **SHOULD** enforce that the `asset_id` Global Variable
is equal to the `asset_id` argument of the `arcXXX_get_circulating_supply` method.

> Alternatively the reference implementation could ignore the `asset_id` argument
> and use directly the `asset_id` Global Variable.

A reference implementation **SHOULD** define the ASA _circulating supply_ as:

```text
circulating_supply = total - reserve_balance - burned_balance - locked_balance - generic_balance
```

Where:

- `total` is the total supply of the ASA (`asset_id`);
- `reserve_balance` is the ASA balance hold by the Reserve Address or `0` if the
address is set to the Global `ZeroAddress`;
- `burned_balance` is the ASA balance hold by the Burned Address or `0` if the address
is set to the Global `ZeroAddress`;
- `locked_balance` is the ASA balance hold by the Locked Address or `0` if the address
is set to the Global `ZeroAddress`;
- `generic_balance` is the ASA balance hold by a Generic Address or `0` if the address
is set to the Global `ZeroAddress`;

## Security Considerations

TBD

## Copyright

Copyright and related rights waived via [CCO](https://creativecommons.org/publicdomain/zero/1.0/).
