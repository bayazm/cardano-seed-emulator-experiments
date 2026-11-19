#!/usr/bin/env python3

"""
B15 — Smart-Contract-Governed Node Authorization

Independent SEED Emulator network builder.

Network:
    AS180 — Producer 1
    AS181 — Producer 2
    AS182 — Producer 3
    AS183 — Relay
    AS184 — Candidate relay

This module creates the network topology only.
It does not build Docker images or start containers.
"""

from seedemu.core import Emulator

from seedemu.layers import (
    Base,
    Routing,
    Ebgp,
    Ibgp,
    Ospf,
)

from seedemu.layers.Ebgp import PeerRelationship

from seedemu.utilities.Makers import (
    makeTransitAs,
    makeStubAsWithHosts,
)


CARDANO_ASES = [180, 181, 182, 183, 184]


def create_b15_network():

    # --------------------------------------------------
    # 1. Initialize SEED Emulator
    # --------------------------------------------------

    emu = Emulator()

    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    ibgp = Ibgp()
    ospf = Ospf()

    # --------------------------------------------------
    # 2. Create Internet Exchanges
    # --------------------------------------------------

    exchanges = {
        210: "NYC-210",
        211: "San Jose-211",
        212: "Chicago-212",
        213: "Miami-213",
        214: "Boston-214",
    }

    for ix_id, name in exchanges.items():
        ix = base.createInternetExchange(ix_id)
        ix.getPeeringLan().setDisplayName(name)

    # --------------------------------------------------
    # 3. Create transit autonomous systems
    # --------------------------------------------------

    makeTransitAs(
        base,
        20,
        [210, 211, 212],
        [(210, 211), (211, 212)],
    )

    makeTransitAs(
        base,
        30,
        [210, 213, 214],
        [(210, 213), (213, 214)],
    )

    makeTransitAs(
        base,
        40,
        [210, 212, 214],
        [(210, 214), (212, 214)],
    )

    makeTransitAs(
        base,
        120,
        [211, 214],
        [(211, 214)],
    )

    # --------------------------------------------------
    # 4. Create B15 Cardano autonomous systems
    # --------------------------------------------------

    makeStubAsWithHosts(emu, base, 180, 210, 1)
    makeStubAsWithHosts(emu, base, 181, 210, 1)

    makeStubAsWithHosts(emu, base, 182, 211, 1)
    makeStubAsWithHosts(emu, base, 183, 211, 1)

    makeStubAsWithHosts(emu, base, 184, 212, 1)

    # --------------------------------------------------
    # 5. Configure Internet Exchange peerings
    # --------------------------------------------------

    ebgp.addRsPeers(210, [20, 30, 40])
    ebgp.addRsPeers(212, [20, 40])
    ebgp.addRsPeers(214, [30, 40])

    # --------------------------------------------------
    # 6. Configure B15 BGP provider relationships
    # --------------------------------------------------

    # AS180 and AS181
    ebgp.addPrivatePeerings(
        210,
        [20],
        [180, 181],
        PeerRelationship.Provider,
    )

    # Additional provider for AS180
    ebgp.addPrivatePeerings(
        210,
        [30],
        [180],
        PeerRelationship.Provider,
    )

    # Transit connectivity
    ebgp.addPrivatePeerings(
        211,
        [20],
        [120],
        PeerRelationship.Provider,
    )

    # AS182 and AS183
    ebgp.addPrivatePeerings(
        211,
        [120],
        [182, 183],
        PeerRelationship.Provider,
    )

    # AS184
    ebgp.addPrivatePeerings(
        212,
        [20, 40],
        [184],
        PeerRelationship.Provider,
    )

    # Core transit connectivity
    ebgp.addPrivatePeerings(
        214,
        [30, 40],
        [120],
        PeerRelationship.Provider,
    )

    # --------------------------------------------------
    # 7. Register layers
    # --------------------------------------------------

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)

    return emu


# ------------------------------------------------------
# 8. Verify B15 network
# ------------------------------------------------------

if __name__ == "__main__":

    emu = create_b15_network()

    base = emu.getLayer("Base")

    print("\n" + "=" * 55)
    print("B15 — NETWORK CONFIGURATION VERIFICATION")
    print("=" * 55)

    for index, asn in enumerate(CARDANO_ASES, start=1):

        try:
            host = base.getAutonomousSystem(asn).getHost(
                "host_0"
            )

            print(
                f"AS{asn}: AVAILABLE "
                f"(Cardano Node {index})"
            )

        except Exception as error:
            print(
                f"AS{asn}: FAILED — {error}"
            )
            raise

    print("\nB15 network topology created successfully.")
    print("No Docker containers were created.")
