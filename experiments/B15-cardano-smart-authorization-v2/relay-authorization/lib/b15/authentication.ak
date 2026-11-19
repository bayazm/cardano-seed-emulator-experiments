use aiken/collection/list
use aiken/crypto.{VerificationKeyHash}

// Check whether the administrator is an authorized
// signatory of the transaction.
pub fn authorized_signer(
  signatories: List<VerificationKeyHash>,
  administrator: VerificationKeyHash,
) -> Bool {
  list.has(signatories, administrator)
}

test administrator_is_authorized() {
  let admin =
    #"11111111111111111111111111111111111111111111111111111111"

  authorized_signer([admin], admin)
}

test unauthorized_signer_is_rejected() {
  let admin =
    #"11111111111111111111111111111111111111111111111111111111"

  let attacker =
    #"22222222222222222222222222222222222222222222222222222222"

  !authorized_signer([attacker], admin)
}

test missing_signature_is_rejected() {
  let admin =
    #"11111111111111111111111111111111111111111111111111111111"

  !authorized_signer([], admin)
}
