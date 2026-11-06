# Judge the Agent

This is the original Friendly Data Meetup challenge brief. The completed evaluation system is documented in the [repository README](../README.md).

> Parcel Pigeon's AI support bot goes live next week.
> Your job: prove whether it's ready, with evidence instead of vibes.

## What you'll build

- A test set of customer questions
- Automatic checks and an AI judge that grade every answer
- A before/after scorecard showing that your fix worked

## Setup

You need [Docker](https://docs.docker.com/get-docker/) and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
cp .env.example .env
docker compose up -d                                   # starts local LLMs
docker compose exec ollama ollama pull llama3.2:3b     # the agent (2 GB)
docker compose exec ollama ollama pull qwen2.5:7b      # the judge (5 GB)
uv run python -m agent.agent "How much is Next Day delivery?"
```

You should see an answer mentioning £6.50.

Using a hosted model (OpenAI, Gemini, Mistral) instead? See [providers.md](providers.md).

## The challenge

| Level | Goal | Time |
|---|---|---|
| 1 | Meet the agent | 15 min |
| 2 | Write the tests | 45 min |
| 3 | Build the judge | 30 min |
| 4 | Fix it and prove it | 30 min |
| Bonus | Stretch goals | Any time left |

### Level 1: Meet the agent

1. Skim [agent/data/policies.md](../agent/data/policies.md). This is what the bot should know.
2. Ask it a few questions with `uv run python -m agent.agent "..."`.
3. Run the starter tests:

```bash
uv run python -m evals.run --label baseline
```

Done when you see a scorecard. A dash means "not scored yet".

### Level 2: Write the tests

1. In [evals/checks.py](../evals/checks.py), implement `tool_called`.
2. Add at least one check of your own (ideas in the file).
3. Add 15 or more cases to [evals/cases.jsonl](../evals/cases.jsonl). See [writing cases](writing-cases.md).

Done when there are 20 or more cases and every check returns a result.

### Level 3: Build the judge

1. Complete the judge in [evals/judge.py](../evals/judge.py). The rubric is [evals/rubric.md](../evals/rubric.md).
2. Run the full suite again.
3. Read 3 or 4 of the judge's reasons in `results/`. Do you agree?
4. Decide whether one score is enough.

Done when every case with an `expected` field gets a score.

### Level 4: Fix it and prove it

1. Pick a failure. Change one thing: the [system prompt](../agent/system_prompt.md), a [tool](../agent/tools.py), or the model.
2. Re-run and compare:

```bash
uv run python -m evals.run --label fix-1
uv run python -m evals.compare results/<baseline>.jsonl results/<fix-1>.jsonl
```

Watch for fixes that break something else. Not every fix belongs in the prompt.

Done when the comparison shows at least one fix and no regression.

### Bonus

Tracing, judge accuracy, model comparisons, red-teaming: [stretch.md](stretch.md).

## Demo

- Your scorecard before and after
- One interesting failure, and why it happened
- Do you trust your judge? Why or why not?
- Which metrics did you choose, and what did each one reveal?
