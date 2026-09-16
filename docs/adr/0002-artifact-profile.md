# ADR-0002 — Small signed content-addressed records first

Status: adopted for the seed profile only.

Use CIDv1 + raw codec (0x55) + sha2-256 multihash (0x12, 32 bytes) + lowercase base32. Hash the exact canonical signed envelope. This is a real CID format but does not imply a running IPFS network, CAR support, automatic pinning or DAG-aware GC.

The JSON profile accepts null, booleans, safe integers, strings, arrays and objects; strings must be NFC and contain no lone surrogates. Keys sort by UTF-16 order. Floats are rejected; represent decimal metadata as strings with units, and add binary/numeric-array codecs in a versioned extension. This is a restricted JCS-compatible domain, not a complete RFC 8785 implementation. Content cannot silently change on read or import.

Artifact signatures attest a node key, not a human legal identity or scientific correctness. Imported signing keys must be explicitly trusted by the owner. Parent relationships form an application-level Merkle DAG; raw blocks themselves do not expose typed IPLD links.
