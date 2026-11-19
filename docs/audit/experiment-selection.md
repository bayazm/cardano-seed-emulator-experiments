# Experiment selection

Retain B11, B12, B13 interoperability v2, B13 same magic, B13 same time, B13 node join, B14, B15 v2 and B16. The B13 variants isolate different questions about magic, time and membership. B11 through B12 and B14 through B16 expose distinct changes in architecture or experimental scope.

| Earlier experiment | Comparison | Disposition |
|---|---|---|
| B13 interoperability | Topology compiler has the same core as v2. The older runtime uses magic 4242/5555 and the successor uses 5555/6666. v2 also changes database/capture namespaces and corrects the startup summary. | Preserve the older run as historical evidence. The distinct-magic question is covered by v2. |
| B15 v1 | The Aiken sources are byte-identical to v2. V1 contains registry initialization and protocol-upgrade artifacts plus B14 revocation evidence. V2 adds admission and revocation controllers and transition artifacts. | Publish v2 source and describe v1's deployment history here. Preserve v1 privately for provenance. |
| B13 same time and node join | Both have byte-identical corresponding Shelley files in the historical source. They differ in database reuse and the point at which a node is introduced. | Retain as separate procedures and document that historical comparisons reuse existing chain state. |

Original directories and existing workspace artifacts are preserved. The reviewed tree uses original sources, with individual file choices documented in the change report.
