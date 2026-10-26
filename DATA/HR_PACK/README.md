# HR Policy Assistant Starter Pack - Network India Property

All policy documents here are FICTIONAL sample data for a demo or portfolio. Do not present
them as real company policy. Replace `DATA_HR/` with approved documents before any real use.

## Contents

| Path | What it is |
|------|-----------|
| `DATA_HR/` | 8 sample policies with numbered sections (HR-POL-01 to HR-POL-08) |
| `guardrails/config.yml` | NeMo config: HR-only instructions, self-check input rail, citation output rail |
| `guardrails/hr_rails.co` | Colang 1.0 rails: greeting, 6 blocked topics, refusal messages |
| `guardrails/actions.py` | Custom action `check_has_citation` used by the output rail |
| `prompts/planner_prompt.md` | Planner prompt with 4 routes: hr_policy, greeting, sensitive, off_topic |
| `prompts/responder_prompt.md` | Responder prompt plus the low-rerank-score fallback snippet |
| `evals/hr_eval_questions.json` | 28 questions with ground truth and the exact policy section |
| `evals/offtopic_adversarial.json` | 36 guardrail tests (30 must-refuse, 6 must-fall-back) |

## How to plug it into your project

1. Ingest: `python -m app.ingestion.processor HR_PACK/DATA_HR --wipe`
2. Guardrails: copy `hr_rails.co` and `actions.py` into your `app/guardrails/` config folder and
   merge `config.yml` with your existing one (keep your own model and Portkey settings).
3. Prompts: paste the planner and responder prompts into your nodes, and add the score filter
   after reranking. Tune `MIN_RERANK_SCORE` using the eval sets.
4. Evals: point `evals/run_evals.py` at `hr_eval_questions.json` for RAGAS, and loop over
   `offtopic_adversarial.json` to measure refusal accuracy.

## Verified vs not yet verified

Verified here: policy section references in the eval set, JSON validity, Colang parses with
NeMo Guardrails 0.24.1, and the citation action (including that it lets the bot's own canned
replies through).

Not verified (needs your API keys and running backend): the `self check input` rail against a live
LLM, the planner's routing accuracy, and the right reranker threshold. Run the adversarial
set once the pieces are connected and adjust from the failures.
