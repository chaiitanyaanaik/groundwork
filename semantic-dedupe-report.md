# Semantic dedupe report

Generated: 2026-05-23T17:42:42.715319+00:00

## Summary

- **Before:** 462 objects
- **After:** 458 objects
- **Removed:** 4 near-duplicates merged into canonical records
- **Merge clusters:** 4

## Rules applied

1. Exact normalized `pattern_name` → merge
2. `core_belief` similarity ≥ 0.85 (cross-guest requires ≥ 0.82)
3. Fingerprint Jaccard ≥ 0.62 with belief ≥ 0.7
4. `pattern_name` similarity ≥ 0.90 within same category
5. Related-only link (no merge) when Jaccard ≥ 0.48 but below merge thresholds

Canonical records retain the richest object; list fields are unioned; `merged_sources` lists absorbed duplicates.

## Merge clusters

### Complexity Trap (Aman Khan (Newsletter))

- **Canonical ID:** `rc_0020`
- **Merged:** 1 object(s)

- `rc_0312` — Complexity Trap (Lenny Rachitsky (Newsletter))

### Sparse Human Signal (Aman Khan (Newsletter))

- **Canonical ID:** `rc_0027`
- **Merged:** 1 object(s)

- `rc_0330` — Sparse Human Signal (Lenny Rachitsky (Newsletter))

### Step-Level Mapping (Aman Khan (Newsletter))

- **Canonical ID:** `rc_0028`
- **Merged:** 1 object(s)

- `rc_0332` — Step-Level Mapping (Lenny Rachitsky (Newsletter))

### Humanity-first adoption contrarianism (Evan Spiegel)

- **Canonical ID:** `rc_0175`
- **Merged:** 1 object(s)

- `rc_0143` — Societal adoption gates deployment (Dr. Fei-Fei Li)


## Notes

The starter-pack corpus was already sparse on lexical duplicates (batches used distinct `pattern_name` labels). Most merges are newsletter cross-author duplicates and cross-episode thematic overlap (e.g. societal adoption constraints in consumer AI).

Re-run: `python3 semantic_dedupe.py`

