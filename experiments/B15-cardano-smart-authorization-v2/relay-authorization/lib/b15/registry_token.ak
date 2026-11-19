use cardano/assets
use cardano/assets.{Assets, PolicyId}

pub fn has_registry_token(
  value: Assets,
  policy_id: PolicyId,
  token_name: ByteArray,
) -> Bool {
  assets.has_nft(value, policy_id, token_name)
}

test valid_registry_token() {
  let policy =
    #"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

  let token_name = "B15_REGISTRY"

  let value =
    assets.from_asset(policy, token_name, 1)

  has_registry_token(value, policy, token_name)
}

test reject_missing_registry_token() {
  let policy =
    #"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

  let token_name = "B15_REGISTRY"

  !has_registry_token(
    assets.zero,
    policy,
    token_name,
  )
}

test reject_multiple_registry_tokens() {
  let policy =
    #"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

  let token_name = "B15_REGISTRY"

  let value =
    assets.from_asset(policy, token_name, 2)

  !has_registry_token(value, policy, token_name)
}
