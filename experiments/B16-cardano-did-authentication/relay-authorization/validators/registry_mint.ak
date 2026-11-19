use aiken/collection/dict
use aiken/collection/list

use cardano/address
use cardano/assets
use cardano/assets.{PolicyId}

use cardano/transaction
use cardano/transaction.{
  Input,
  InlineDatum,
  Output,
  OutputReference,
  Transaction,
}

// ============================================================
// B15 — One-Shot Registry NFT Minting Policy
//
// Purpose:
// Create exactly one B15_REGISTRY token.
//
// Security requirements:
// 1. The specified UTxO must be consumed.
// 2. Exactly one registry token must be minted.
// 3. No other tokens may be minted under this policy.
// 4. The UTxO can only be consumed once.
//
// Experimental implementation.
// ============================================================

validator registry_mint(
  required_ref: OutputReference,
) {
  mint(
    _redeemer: Int,
    policy_id: PolicyId,
    tx: Transaction,
  ) {

    // Verify that the unique UTxO is consumed.

    let reference_consumed =
      list.any(
        tx.inputs,
        fn(input) {
          input.output_reference == required_ref
        },
      )

    // Retrieve all tokens minted under this policy.

    let minted_tokens =
      tx.mint
        |> assets.tokens(policy_id)
        |> dict.to_pairs()

    // Only one B15_REGISTRY token is permitted.
    // No additional assets under this policy are allowed.

    let correct_mint =
      minted_tokens == [Pair("B15_REGISTRY", 1)]

    reference_consumed && correct_mint
  }

  else(_) {
    fail
  }
}

// ============================================================
// B15-E1 — Phase 9B
// One-shot NFT minting policy tests
// ============================================================

// Illustrative minting policy identifier.

fn test_policy_id() -> PolicyId {
  #"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}


// Unique UTxO reference required by our minting policy.

fn test_required_ref() -> OutputReference {
  OutputReference {
    transaction_id: "",
    output_index: 0,
  }
}


// Construct a simulated NFT minting transaction.
//
// Parameters:
//
// consume_required:
//   True  -> Include the required UTxO.
//   False -> Omit the required UTxO.
//
// token_name:
//   Name of the asset being minted.
//
// quantity:
//   Positive -> Mint tokens.
//   Negative -> Burn tokens.
//

fn mint_transaction(
  consume_required: Bool,
  token_name: ByteArray,
  quantity: Int,
) -> Bool {

  // ----------------------------------------------------------
  // A. Test configuration
  // ----------------------------------------------------------

  let policy_id = test_policy_id()

  let required_ref = test_required_ref()


  // ----------------------------------------------------------
  // B. Construct the required input UTxO
  // ----------------------------------------------------------

  let test_address =
    address.from_script(
      #"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )

  let input_output =
    Output {
      address: test_address,
      value: assets.zero,
      datum: InlineDatum(as_data(0)),
      reference_script: None,
    }

  let required_input =
    Input {
      output_reference: required_ref,
      output: input_output,
    }


  // ----------------------------------------------------------
  // C. Construct minted assets
  // ----------------------------------------------------------

  let minted_assets =
    assets.from_asset(
      policy_id,
      token_name,
      quantity,
    )


  // ----------------------------------------------------------
  // D. Construct simulated transaction
  // ----------------------------------------------------------

  let tx =
    Transaction {
      ..transaction.placeholder,
      inputs:
        if consume_required {
          [required_input]
        } else {
          []
        },
      mint: minted_assets,
    }


  // ----------------------------------------------------------
  // E. Execute minting validator
  // ----------------------------------------------------------

  registry_mint.mint(
    required_ref,
    0,
    policy_id,
    tx,
  )
}


// ============================================================
// Test 19 — Accept valid one-shot minting
// ============================================================

test accept_valid_registry_mint() {

  mint_transaction(
    True,
    "B15_REGISTRY",
    1,
  )
}


// ============================================================
// Test 20 — Reject missing required UTxO
// ============================================================

test reject_mint_without_required_utxo() {

  !mint_transaction(
    False,
    "B15_REGISTRY",
    1,
  )
}


// ============================================================
// Test 21 — Reject minting multiple registry NFTs
// ============================================================

test reject_multiple_registry_mint() {

  !mint_transaction(
    True,
    "B15_REGISTRY",
    2,
  )
}


// ============================================================
// Test 22 — Reject incorrect token name
// ============================================================

test reject_wrong_registry_token_name() {

  !mint_transaction(
    True,
    "FAKE_REGISTRY",
    1,
  )
}


// ============================================================
// Test 23 — Reject burning the registry NFT
// ============================================================

test reject_registry_token_burning() {

  !mint_transaction(
    True,
    "B15_REGISTRY",
    -1,
  )
}
