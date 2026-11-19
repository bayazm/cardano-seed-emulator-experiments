#!/usr/bin/env python3
"""B16: admission policy tests using simulated registry states."""

from registry_policy import authorize_relay


def main():

    authorized_registry = {
        "node": "AS184",
        "ip": "10.184.0.71",
        "authorized": True,
        "revision": 3,
    }

    revoked_registry = {
        "node": "AS184",
        "ip": "10.184.0.71",
        "authorized": False,
        "revision": 4,
    }

    def check(name, expected, **kwargs):
        result = authorize_relay(**kwargs)

        assert result[0] is expected, (
            f"{name}: unexpected result {result}"
        )

        print(f"{name}: PASS — {result[1]}")

    print("===== B16 REGISTRY POLICY TESTS =====")

    # E14: All three security conditions satisfied.
    check(
        "E14 Authorized relay",
        True,
        authenticated=True,
        enrollment_valid=True,
        node="AS184",
        ip="10.184.0.71",
        registry=authorized_registry,
    )

    # E15: Correct identity but revoked on Cardano.
    check(
        "E15 Revoked relay",
        False,
        authenticated=True,
        enrollment_valid=True,
        node="AS184",
        ip="10.184.0.71",
        registry=revoked_registry,
    )

    # E16: Invalid DID authentication.
    check(
        "E16 Invalid identity",
        False,
        authenticated=False,
        enrollment_valid=True,
        node="AS184",
        ip="10.184.0.71",
        registry=authorized_registry,
    )

    # E17: Invalid administrator enrollment.
    check(
        "E17 Invalid enrollment",
        False,
        authenticated=True,
        enrollment_valid=False,
        node="AS184",
        ip="10.184.0.71",
        registry=authorized_registry,
    )

    # E18: Registry contains a different node identity.
    check(
        "E18 Wrong node",
        False,
        authenticated=True,
        enrollment_valid=True,
        node="AS185",
        ip="10.184.0.71",
        registry=authorized_registry,
    )

    # E19: No registry information available.
    check(
        "E19 Missing registry",
        False,
        authenticated=True,
        enrollment_valid=True,
        node="AS184",
        ip="10.184.0.71",
        registry=None,
    )

    # E20: Invalid registry revision.
    invalid_registry = dict(authorized_registry)
    invalid_registry["revision"] = -1

    check(
        "E20 Invalid revision",
        False,
        authenticated=True,
        enrollment_valid=True,
        node="AS184",
        ip="10.184.0.71",
        registry=invalid_registry,
    )

    print()
    print("RESULT: 7/7 registry policy tests passed")
    print("NOTE: Registry states are simulated, not queried from Cardano.")


if __name__ == "__main__":
    main()
