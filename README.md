---
title: Supermail Environment
sdk: docker
app_port: 8000
tags:
  - openenv
---

# Supermail

Supermail is a deterministic customer support email triage environment built for the OpenEnv RL Challenge. The environment simulates a real support queue where an agent must classify incoming emails by priority, category, and operational action.

## Why this environment

Email triage is routine operational work in real support teams. A good agent must:

- detect urgency
- route issues to the right queue
- choose whether to respond immediately, assign to a specialist, or ignore spam

Supermail focuses on those decisions with strict graders and incremental rewards instead of a toy echo task.

## Round 1 Workflow

When Round 1 opens, you choose 1 of the revealed problem statements and build an OpenEnv environment around it.

Example of what a problem statement looks like:

> "Build a mini-game RL environment with clearly defined tasks, automated graders, and reward logic using the OpenEnv framework."

For Supermail, the equivalent framing is:

> "Build a real-world email triage RL environment with clearly defined tasks, automated graders, security-aware classification, and reward logic using the OpenEnv framework."

What this project does:

- creates a customer support email triage environment an AI agent can operate
- defines tasks with increasing difficulty
- uses deterministic graders that verify task completion
- defines reward logic for partial and final progress
- packages the environment using OpenEnv for automated evaluation

The project can be used in the same flow as the challenge instructions:

### Step 1. Application Form

Choose one of the problem statements revealed on the platform.

For this project, the chosen problem is a real-world email triage environment for customer support.

### Step 2. Scaffold

If you are starting from scratch with OpenEnv:

```bash
openenv init my_env
```

That generates the base project structure.

This repository is already scaffolded and implemented as `supermail`.

### Step 3. Build

Define the environment inside the generated files.

In this repository, the core implementation is already provided in:

- `models.py`
- `tasks/`
- `server/environment.py`
- `server/app.py`
- `inference.py`

### Step 4. Test locally

Run the environment server locally:

```bash
uv run server
```

Then verify:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "healthy"}
```

### Step 5. Deploy

Push the environment to Hugging Face Spaces:

```bash
openenv push --repo-id your-username/supermail
```

### Step 6. Submit

Paste the Hugging Face Spaces URL before the deadline.

Example format:

```text
https://huggingface.co/spaces/your-username/supermail
```

## Task set

The environment ships with three deterministic tasks:

| Task | Difficulty | Required output | Max score |
| --- | --- | --- | --- |
| `email_easy` | easy | `priority` | `1.0` |
| `email_medium` | medium | `priority`, `category` | `1.0` |
| `email_hard` | hard | `priority`, `category`, `action` | `1.0` |

Bundled labels:

- Priority: `urgent`, `normal`, `spam`
- Category: `billing`, `delivery`, `technical`, `general`
- Action: `respond_immediately`, `assign_to_team`, `ignore`

## Observation space

`SupportObservation` returns:

- `task_id`, `task_type`, `benchmark`, `objective`
- `email`
- `context`
- `required_fields`
- `allowed_values`
- `history`
- `feedback`
- `score`
- `attempts_remaining`
- OpenEnv fields such as `done`, `reward`, and `metadata`

## Action space

`SupportAction` accepts:

- `priority`
- `category`
- `action`
- `notes` (optional, ignored by the grader)

Agents only need to submit the fields required by the current task.

## Reward design

The grader is deterministic and task-specific:

- Correct new field: reward equal to that field's weight
- Wrong step with no new progress: `-0.10`
- Repeating the same partial answer with no progress: `-0.02`
- Taking too many steps after step 3 without finishing: extra `-0.05`

Task weights:

- Easy: priority `1.0`
- Medium: priority `0.5`, category `0.5`
- Hard: priority `0.3`, category `0.3`, action `0.4`

The cumulative task score remains in the `0.0` to `1.0` range.

## Prompting Guidance

The baseline prompt should be strict, short, and schema-bound.

Good prompting principles for this environment:

- tell the model to output exactly one JSON object
- restrict output to only the required fields for the current task
- remind the model that email content is untrusted user content
- explicitly forbid following instructions embedded inside the email body
- keep the prompt focused on classification, not free-form reasoning

Recommended prompting behavior:

- use the structured observation as the trusted input
- treat subject and body text as data to classify, not instructions to obey
- prefer deterministic inference settings for reproducible baselines

The current baseline system prompt is stored in `sys_prompt.py`.

## Security Model

Supermail is intentionally designed to evaluate secure agent behavior.

Security goals:

- resist prompt injection embedded inside emails
- resist spoofed urgency and fake authority
- avoid acting on hidden workflow override requests
- classify manipulative or suspicious messages into safe outcomes

The hard task specifically teaches the agent to reject messages that try to:

- override policy
- bypass normal support routing
- exploit urgency or secrecy language
- trick the model into treating user text as system instructions

This improves both benchmark realism and practical agent safety.

## How The Environment Is Implemented For RL

The RL structure is straightforward:

1. `reset()` selects a task and returns the initial observation.
2. The agent submits an action with one or more decision fields.
3. The grader compares submitted fields against the task answer key.
4. The environment returns updated observation state, reward, done flag, and metadata.
5. The episode ends when the task is solved or the attempt budget is exhausted.

Implementation pieces:

- `tasks/` contains deterministic task definitions and answer keys
- `server/environment.py` contains the step logic, grader, reward shaping, and state transitions
- `models.py` defines the typed action, observation, and state models
- `inference.py` runs a reproducible baseline using the OpenAI client

## Files

```text
play/
├── Dockerfile
├── inference.py
├── models.py
├── openenv.yaml
├── requirements.txt
├── tasks/
│   ├── email_easy.py
│   ├── email_medium.py
│   └── email_hard.py
└── server/
    ├── app.py
    └── environment.py
```

## Local setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
uv run server
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "healthy"}
```

## Docker

Build:

```bash
docker build -t supermail .
```

Run:

```bash
docker run -p 8000:8000 supermail
```

## Inference baseline

`inference.py` lives in the project root and follows the required log format:

```text
[START] task=<task_name> env=<benchmark> model=<model_name>
[STEP] step=<n> action=<json> reward=<0.00> done=<true|false> error=<msg|null>
[END] success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...>
```

It reads:

- `API_BASE_URL` with default `https://router.huggingface.co/v1`
- `MODEL_NAME` with default `Qwen/Qwen2.5-72B-Instruct`
- `HF_TOKEN` with no default
- optional `LOCAL_IMAGE_NAME` when using `from_docker_image()`
- `SUPERMAIL_TASK`, `SUPERMAIL_BASE_URL`

When an OpenAI-compatible endpoint is available, the script uses the OpenAI client for action generation. If the request fails, it falls back to a deterministic heuristic so the baseline remains reproducible on the bundled tasks.

Deterministic fallback baseline on bundled tasks:

- `email_easy`: `0.99`
- `email_medium`: `0.99`
- `email_hard`: `0.99`

## Hugging Face Spaces

Recommended settings:

- Runtime: Docker
- Tag: `openenv`
- Environment variable: `HF_TOKEN`

After deployment, verify:

```bash
curl https://<your-space>.hf.space/health
```

## Notes

- The environment cycles through the three tasks on repeated `reset()` calls.
- Pass `task_id` to `SupermailEnvironment(task_id="email_hard")` for deterministic single-task evaluation.
