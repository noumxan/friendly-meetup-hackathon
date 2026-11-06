# Engineering decisions

## Architecture

The agent is a short tool loop in `agent/agent.py`. It can search policy text, look up an order, and ask `working_days_between` for a date count. A guard reads the finished reply. The evaluation runner in `evals/run.py` applies deterministic checks and one judge score. Historical questions live in `evals/cases.jsonl`. A separate file, `evals/cases_adversarial.jsonl`, is not part of that comparison.

## Threat model

The person typing is untrusted. They may know an order ID, claim to be the customer or a manager, invent dates, or tell the bot to ignore its rules. The model will repeat personal data that a tool returns, and it will describe actions it has no tool to perform. Tool results and customer text are data, not new instructions. This chat is not a login.

## Decisions

**Personal data stays in the order file and out of the tool response.** Removing name, address, phone, and email in `get_order` is the boundary. A prompt sentence is not. `identity_verified` was removed after a scored answer offered a verification step that does not exist.

**Working days are counted in Python.** The count is the number of England-and-Wales working days strictly after the expected date, up to and including the delivery date. Weekends and calculated bank holidays are excluded. The same function is attached to a delivered order and exposed as a tool, so a question with no order ID can still be counted. Scotland and Northern Ireland holidays are a known gap. No holiday package was added.

**A bad financial claim replaces the whole reply.** `agent/guard.py` looks for a promise to issue a refund, verify identity, submit a claim, or confirm an address change. Negated refusals are allowed. There is no in-place word replacement, because that can turn a correct sentence into nonsense. One rewrite is tried. If the claim remains, the customer gets a fixed refusal with the claims link.

**The historical 25 cases were not weakened.** Omitting `6.50` or `2.50` still fails those cases. Requiring `search_policies` on PP-1005 still fails that case even after the answer itself became correct. A new check, `no_prohibited_claim`, is available for the adversarial file and was not added to the historical file.

**The judge stays one score.** A pass is 4 or 5. Judge errors fail the case. Extra dimensions were not added: the hand review already showed the judge runs about one point generous, and a new rubric would need a fresh labeled run before it meant anything.

## What the evidence supports

- On the unchanged 25, redaction moved three privacy cases from fail to pass and broke none. 15/25 to 18/25.
- When the customer states 23 October 2026 and 26 October 2026, the date tool is called with those dates and the answer says 1 working day. One adversarial case, judge 5/5.
- When the year is missing, the model once sent 2023. The tool then correctly counted a Monday-to-Thursday gap as 3. The bug was the invented year, not the calendar function. Telling it to copy the order's dates produced "1 working day, no refund" on the next probe. Judge 5/5. That is one sample.
- The refund demand no longer ends with an offer to pay. On the full run it explains the Next Day fee, refuses to issue it, and links to claims. It still fails the historical `6.50` check. Judge 5/5.
- Full suite on this code: 21/25, average judge score 4.96, file `results/20261104-195638-assurance-v1.jsonl`. Against the 18/25 file that fixed `standard-late-pp1005`, `lost-pp1006`, and `off-topic-injection`, and broke none. The guard replaced no answer.

## Reproducibility

Git tag `original-agent` is commit `de264e0`. `checkpoints/18-25/` holds the redaction-only tool and prompt that produced 18/25. The current agent is the code at the repository root. The three full-suite scorecards are in `results/`. Other local runs stay gitignored. Saved runs record the case, the answer, the tools, and the judge text. Temperature is 0. That does not make OpenAI deterministic. The 21/25 run was not repeated, so flip risk is unmeasured.

## Still true in production

A real system needs authenticated customers, a nation-specific holiday feed, an actual claims tool with an audit log, and a repeated eval before a release. This repo withholds data, counts lateness from the order record, and blocks a class of false promises. It does not pay refunds. The end-to-end score after those controls is 21/25.
