# SupportForge benchmark methodology

Laptop-only evaluation. No GB10 required. Designed so scores are reproducible in Cursor.

## Dataset

Five golden cases under `eval/goldens/` + evidence packs under `cases/`:

| Case | Failure family | Root-cause signal |
|------|----------------|-------------------|
| CASE-1042 | memory | CUDA OOM + abandoned `train_scratch.py` |
| CASE-1088 | hardware | Xid 79 / GPU fallen off bus |
| CASE-1101 | distributed | NCCL collective timeout / node connect |
| CASE-1120 | environment | CUDA driver insufficient for runtime |
| CASE-1155 | reliability | ECC / remapped rows → NaN logits |

Each case has an **incomplete** pack (customer-style gaps) and a **complete** pack (injectable evidence).

## Metrics

For each case we score:

1. **Completeness** — required evidence checklist hits 100% after inject  
2. **Hypothesis coverage** — golden term-groups present in audit/handoff/LLM reply  
3. **Citation coverage** — expected file names appear in the package  
4. **False claims** — must-not-claim terms absent (penalized)  
5. **Latency** — wall time for rule audit or live investigate  

Composite score ∈ [0, 100]. A case **passes** when completeness OK, ≥1 hypothesis group hit, ≥1 citation hit, and zero false claims.

## Modes

| Mode | What runs | Typical latency |
|------|-----------|-----------------|
| `rule` | Deterministic engine only | &lt; 1s / case |
| `llm` | Engine + local Ollama investigate | 10–40s / case |

## Reproduce

```bash
# terminal A
bash scripts/start-console.sh

# terminal B
bash scripts/run-eval.sh rule
bash scripts/run-eval.sh llm    # requires ollama + qwen2.5:7b-instruct
```

Or in the UI: **Run rule eval** / **Run live LLM eval**.

Artifacts: `workspace/outbox/eval-rule.json`, `eval-llm.json`.

## Why this is the product

Enterprise GPU support fails less often on “model quality” than on **missing evidence and uncited guesses**. SupportForge measures the handoff: completeness, cited hypotheses, and refusal of destructive actions — on a laptop, with live models.
