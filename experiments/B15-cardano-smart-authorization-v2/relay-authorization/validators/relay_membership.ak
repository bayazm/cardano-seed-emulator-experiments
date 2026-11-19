use aiken/collection/list
use aiken/crypto.{VerificationKeyHash}

use cardano/address
use cardano/assets
use cardano/assets.{PolicyId}

use cardano/transaction
use cardano/transaction.{
  Input,
  Output,
  InlineDatum,
  OutputReference,
  Transaction,
}

use b15/authorization.{
  Action,
  Authorize,
  RegistryState,
  valid_transition,
}

use b15/authentication.{authorized_signer}
use b15/registry_token.{has_registry_token}


// ============================================================
// B15 — Smart-Contract-Governed Node Authorization
//
// Membership validator with registry NFT preservation.
//
// Current functionality:
//   1. Administrator authentication
//   2. Membership state-transition validation
//   3. Registry successor verification
//   4. Registry NFT verification
//   5. Transaction-level security tests
//
// Status: Experimental — not deployment-ready.
// ============================================================


// ------------------------------------------------------------
// 1. Membership update
// ------------------------------------------------------------

pub type MembershipUpdate {
  MembershipUpdate {
    action: Action,
    proposed_state: RegistryState,
  }
}


// ------------------------------------------------------------
// 2. Membership spending validator
// ------------------------------------------------------------

validator relay_membership(
  administrator: VerificationKeyHash,
  registry_policy: PolicyId,
  registry_name: ByteArray,
) {

  spend(
    datum: Option<RegistryState>,
    redeemer: MembershipUpdate,
    own_ref: OutputReference,
    tx: Transaction,
  ) {

    // --------------------------------------------------------
    // A. Verify existing registry datum
    // --------------------------------------------------------

    expect Some(current_state) = datum


    // --------------------------------------------------------
    // B. Locate the registry UTxO being spent
    // --------------------------------------------------------

    expect Some(own_input) =
      list.find(
        tx.inputs,
        fn(input) {
          input.output_reference == own_ref
        },
      )


    // --------------------------------------------------------
    // C. Locate continuing outputs
    // --------------------------------------------------------

    let continuing_outputs =
      list.filter(
        tx.outputs,
        fn(output) {
          output.address == own_input.output.address
        },
      )


    // Require exactly one continuing output.

    expect [successor] = continuing_outputs


    // --------------------------------------------------------
    // D. Verify successor datum
    // --------------------------------------------------------

    expect InlineDatum(output_datum) = successor.datum

    expect next_state: RegistryState = output_datum


    // --------------------------------------------------------
    // E. Verify registry NFT preservation
    // --------------------------------------------------------

    // The consumed registry UTxO must contain exactly
    // one designated registry NFT.

    let input_token_valid =
      has_registry_token(
        own_input.output.value,
        registry_policy,
        registry_name,
      )


    // The successor registry UTxO must contain exactly
    // one designated registry NFT.

    let output_token_valid =
      has_registry_token(
        successor.value,
        registry_policy,
        registry_name,
      )


    // --------------------------------------------------------
    // F. Verify administrator authentication
    // --------------------------------------------------------

    let administrator_signed =
      authorized_signer(
        tx.extra_signatories,
        administrator,
      )


    // --------------------------------------------------------
    // G. Verify membership state transition
    // --------------------------------------------------------

    let transition_valid =
      valid_transition(
        current_state,
        next_state,
        redeemer.action,
      )


    // --------------------------------------------------------
    // H. Verify proposed state matches actual successor
    // --------------------------------------------------------

    let state_matches =
      next_state == redeemer.proposed_state


    // --------------------------------------------------------
    // I. Final authorization decision
    // --------------------------------------------------------

    administrator_signed &&
      transition_valid &&
      state_matches &&
      input_token_valid &&
      output_token_valid
  }

  else(_) {
    fail
  }
}


// ============================================================
// 3. TEST CONFIGURATION
// ============================================================

// Illustrative administrator verification-key hash.

fn test_administrator() -> VerificationKeyHash {
  #"11111111111111111111111111111111111111111111111111111111"
}


// Illustrative registry policy identifier.

fn test_registry_policy() -> PolicyId {
  #"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}


// Registry NFT name.

fn test_registry_name() -> ByteArray {
  "B15_REGISTRY"
}


// ============================================================
// 4. TEST — Missing registry datum
// ============================================================

test reject_missing_registry_datum() fail {

  let admin = test_administrator()

  let registry_policy = test_registry_policy()

  let registry_name = test_registry_name()

  let proposed =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: True,
      revision: 1,
    }

  let redeemer =
    MembershipUpdate {
      action: Authorize,
      proposed_state: proposed,
    }

  let own_ref =
    OutputReference {
      transaction_id: "",
      output_index: 0,
    }

  relay_membership.spend(
    admin,
    registry_policy,
    registry_name,
    None,
    redeemer,
    own_ref,
    Transaction {
      ..transaction.placeholder,
      extra_signatories: [admin],
    },
  )
}


// ============================================================
// 5. CONFIGURABLE TRANSACTION TEST HELPER
// ============================================================

// This helper constructs simulated Cardano transactions.
//
// Parameters:
//
// signatories:
//   Transaction signatories.
//
// include_successor:
//   True  -> Create successor registry output.
//   False -> Omit successor registry output.
//
// change_identity:
//   True  -> Change AS154 to AS155.
//   False -> Preserve AS154 identity.
//
// input_has_token:
//   True  -> Include NFT in consumed registry UTxO.
//   False -> Remove NFT from consumed registry UTxO.
//
// output_has_token:
//   True  -> Include NFT in successor registry UTxO.
//   False -> Remove NFT from successor registry UTxO.
//

fn admission_transaction_with_token_options(
  signatories: List<VerificationKeyHash>,
  include_successor: Bool,
  change_identity: Bool,
  input_has_token: Bool,
  output_has_token: Bool,
) -> Bool {

  // ----------------------------------------------------------
  // A. Test configuration
  // ----------------------------------------------------------

  let admin = test_administrator()

  let registry_policy = test_registry_policy()

  let registry_name = test_registry_name()


  // ----------------------------------------------------------
  // B. Existing membership state
  // ----------------------------------------------------------

  let old_state =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: False,
      revision: 0,
    }


  // ----------------------------------------------------------
  // C. Proposed membership state
  // ----------------------------------------------------------

  let new_state =
    RegistryState {
      node_id:
        if change_identity {
          "AS155"
        } else {
          "AS154"
        },
      node_ip: "10.154.0.71",
      authorized: True,
      revision: 1,
    }


  // ----------------------------------------------------------
  // D. Authorization redeemer
  // ----------------------------------------------------------

  let redeemer =
    MembershipUpdate {
      action: Authorize,
      proposed_state: new_state,
    }


  // ----------------------------------------------------------
  // E. Registry input reference
  // ----------------------------------------------------------

  let own_ref =
    OutputReference {
      transaction_id: "",
      output_index: 0,
    }


  // ----------------------------------------------------------
  // F. Illustrative script address
  // ----------------------------------------------------------

  let script_address =
    address.from_script(
      #"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )


  // ----------------------------------------------------------
  // G. Input NFT configuration
  // ----------------------------------------------------------

  let input_value =
    if input_has_token {
      assets.from_asset(
        registry_policy,
        registry_name,
        1,
      )
    } else {
      assets.zero
    }


  // ----------------------------------------------------------
  // H. Output NFT configuration
  // ----------------------------------------------------------

  let output_value =
    if output_has_token {
      assets.from_asset(
        registry_policy,
        registry_name,
        1,
      )
    } else {
      assets.zero
    }


  // ----------------------------------------------------------
  // I. Existing registry UTxO
  // ----------------------------------------------------------

  let old_output =
    Output {
      address: script_address,
      value: input_value,
      datum: InlineDatum(as_data(old_state)),
      reference_script: None,
    }


  let own_input =
    Input {
      output_reference: own_ref,
      output: old_output,
    }


  // ----------------------------------------------------------
  // J. Successor registry UTxO
  // ----------------------------------------------------------

  let new_output =
    Output {
      address: script_address,
      value: output_value,
      datum: InlineDatum(as_data(new_state)),
      reference_script: None,
    }


  // ----------------------------------------------------------
  // K. Construct simulated transaction
  // ----------------------------------------------------------

  let tx =
    Transaction {
      ..transaction.placeholder,
      inputs: [own_input],
      outputs:
        if include_successor {
          [new_output]
        } else {
          []
        },
      extra_signatories: signatories,
    }


  // ----------------------------------------------------------
  // L. Execute spending validator
  // ----------------------------------------------------------

  relay_membership.spend(
    admin,
    registry_policy,
    registry_name,
    Some(old_state),
    redeemer,
    own_ref,
    tx,
  )
}


// ============================================================
// 6. COMPATIBILITY WRAPPERS
// ============================================================

// Preserve existing three-parameter test helper.

fn admission_transaction_with_options(
  signatories: List<VerificationKeyHash>,
  include_successor: Bool,
  change_identity: Bool,
) -> Bool {

  admission_transaction_with_token_options(
    signatories,
    include_successor,
    change_identity,
    True,
    True,
  )
}


// Preserve original authorized-admission helper.

fn admission_transaction(
  signatories: List<VerificationKeyHash>,
) -> Bool {

  admission_transaction_with_options(
    signatories,
    True,
    False,
  )
}


// ============================================================
// 7. EXISTING VALIDATOR TESTS
// ============================================================


// ------------------------------------------------------------
// Test 9 — Missing registry datum
// Defined in Section 4.
// ------------------------------------------------------------


// ------------------------------------------------------------
// Test 10 — Accept authorized admission
// ------------------------------------------------------------

test accept_authorized_admission() {

  let admin = test_administrator()

  admission_transaction([admin])
}


// ------------------------------------------------------------
// Test 11 — Reject missing administrator signature
// ------------------------------------------------------------

test reject_admission_without_admin_signature() {

  admission_transaction([]) == False
}


// ------------------------------------------------------------
// Test 12 — Reject missing successor registry output
// ------------------------------------------------------------

test reject_missing_successor_output() fail {

  let admin = test_administrator()

  admission_transaction_with_options(
    [admin],
    False,
    False,
  )
}


// ------------------------------------------------------------
// Test 13 — Reject modified successor identity
// ------------------------------------------------------------

test reject_modified_successor_identity() {

  let admin = test_administrator()

  !admission_transaction_with_options(
    [admin],
    True,
    True,
  )
}


// ============================================================
// 8. NEW REGISTRY NFT ENFORCEMENT TESTS
// ============================================================


// ------------------------------------------------------------
// Test 17 — Reject missing input registry NFT
// ------------------------------------------------------------

test reject_missing_input_registry_nft() {

  let admin = test_administrator()

  !admission_transaction_with_token_options(
    [admin],
    True,
    False,
    False,
    True,
  )
}


// ------------------------------------------------------------
// Test 18 — Reject missing output registry NFT
// ------------------------------------------------------------

test reject_missing_output_registry_nft() {

  let admin = test_administrator()

  !admission_transaction_with_token_options(
    [admin],
    True,
    False,
    True,
    False,
  )
}
