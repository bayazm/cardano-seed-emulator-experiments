pub type Action {
  Authorize
  Revoke
}

pub type RegistryState {
  RegistryState {
    node_id: ByteArray,
    node_ip: ByteArray,
    authorized: Bool,
    revision: Int,
  }
}

// Validate a proposed authorization-state transition.
pub fn valid_transition(
  old: RegistryState,
  new: RegistryState,
  action: Action,
) -> Bool {
  let identity_unchanged =
    old.node_id == new.node_id &&
    old.node_ip == new.node_ip

  let revision_valid =
    new.revision == old.revision + 1

  let action_valid =
    when action is {
      Authorize ->
        !old.authorized && new.authorized

      Revoke ->
        old.authorized && !new.authorized
    }

  identity_unchanged &&
    revision_valid &&
    action_valid
}

test valid_authorization() {
  let old =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: False,
      revision: 0,
    }

  let new =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: True,
      revision: 1,
    }

  valid_transition(old, new, Authorize)
}

test reject_invalid_revision() {
  let old =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: False,
      revision: 0,
    }

  let new =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: True,
      revision: 0,
    }

  !valid_transition(old, new, Authorize)
}

test reject_unauthorized_identity_change() {
  let old =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: False,
      revision: 0,
    }

  let new =
    RegistryState {
      node_id: "AS155",
      node_ip: "10.155.0.71",
      authorized: True,
      revision: 1,
    }

  !valid_transition(old, new, Authorize)
}

test reject_duplicate_authorization() {
  let old =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: True,
      revision: 1,
    }

  let new =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: True,
      revision: 2,
    }

  !valid_transition(old, new, Authorize)
}

test reject_revocation_of_unauthorized_node() {
  let old =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: False,
      revision: 0,
    }

  let new =
    RegistryState {
      node_id: "AS154",
      node_ip: "10.154.0.71",
      authorized: False,
      revision: 1,
    }

  !valid_transition(old, new, Revoke)
}
