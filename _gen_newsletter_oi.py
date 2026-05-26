#!/usr/bin/env python3
"""Generate operational-intelligence-newsletters.json"""
import json
from pathlib import Path

def o(name, ep, guest, quote, cat, belief, op, arch, h, pres, fail, con, sig, emo, adapt, ai):
    return dict(pattern_name=name, source_episode=ep, source_guest=guest,
        source_quote_or_context=quote, category=cat, core_belief=belief,
        operational_pattern=op, organizational_archetype=arch, hidden_assumptions=h,
        pressure_scenarios=pres, failure_modes=fail, contradictions=con,
        behavioral_signals=sig, emotional_political_dynamics=emo,
        operational_adaptations=adapt, ai_era_implications=ai)

P = []
# Load extended patterns from companion module
from _newsletter_oi_data import DATA  # noqa: E402

for row in DATA:
    P.append(o(*row))

out = Path(__file__).parent / "operational-intelligence-newsletters.json"
out.write_text(json.dumps(P, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
from collections import Counter
c = Counter(p["source_episode"] for p in P)
print(f"Wrote {len(P)} objects to {out}")
for ep, n in sorted(c.items()):
    assert 3 <= n <= 10, (ep, n)
print("OK")
