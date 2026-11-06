# 18/25 redaction snapshot

This directory is the privacy-redaction code that scored 18/25. It is not the current agent.

`tools.py` removes name, address, phone, and email from `get_order`, and it still returns `identity_verified: false`. That field was removed later because a scored answer offered a verification step that does not exist. `system_prompt.md` is the short starter prompt used for that run. `cases.jsonl` is the 25-case file at the time of the run.

The matching scorecard is `results/20261104-191551-fix-redact-only.jsonl`. The original, pre-redaction agent is git tag `original-agent` (commit `de264e0`). Current behaviour is the repository root, scored in `results/20261104-195638-assurance-v1.jsonl`.

`tracked.patch` is a local generated diff and is not part of the snapshot.
