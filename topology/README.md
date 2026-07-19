# Benchmark topologies

This directory contains the topology and traffic fixtures used by GART. Run
`python3 tools/build_topologies.py` to regenerate every fixture.

`Topology.txt` stores physical links as:

```text
source destination delay capacity loss
```

The loader expands each physical link into two directed links. `TM.txt` is a
square row-major traffic matrix. See each `metadata.json` for source and
normalization details.
