# GDP.xlsx Benchmark, by Surge AI

GDP.xlsx follows a similar format to GDP.pdf: models are given an Excel file and asked to answer questions about it or using information within it. The benchmark measures whether a model reads the spreadsheet the way a domain professional would, noticing formatting that carries meaning, reconciling tabs against each other, and honoring rules stated in the workbook.

This package contains the GDP.xlsx evaluation harness from [Surge AI](https://surgehq.ai/). The task dataset is distributed separately on [Hugging Face](https://huggingface.co/datasets/surgeai/GDP.xlsx).

Tasks use [Harbor](https://harborframework.com/) format. The harness runs models through the [OpenHands SDK](https://github.com/OpenHands/software-agent-sdk).

## Layout

This package contains:

- `agent-harness/` — the agent loop used to complete trials.
- `harbor-agents/` — the Harbor adapter that installs and runs the agent in a sandbox.
- `pyproject.toml` + `uv.lock` — host-side environment. Pins `harbor` and pulls in the two packages above as path dependencies.

## Getting the tasks

Download the GDP.xlsx dataset from its Hugging Face release and extract it anywhere. Set `TASKS_DIR` to the directory directly containing the task directories. Each task directory contains `task.toml`, `instruction.md`, `environment/` (the task image and input workbook), and `tests/` (grading criteria and verifier).

Keep the harness package together, including both local packages and their lockfiles. Harbor connects the harness to the downloaded tasks through `-p "$TASKS_DIR"`; no particular directory layout outside the harness is required.

## Task environment

Each task runs in a Linux container with its input workbook in `/app`. The image provides general-purpose tools, including the Python packages `openpyxl`, `pandas`, `python-calamine`, `xlsxwriter`, `xlrd`, `formulas`, and `lxml`; LibreOffice for headless recalculation and rendering; and `unzip` for inspecting XLSX package contents.

The agent's system prompt includes a short inventory of the installed software. See [agent-harness/README.md](agent-harness/README.md#environment-context).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) and Python 3.12 or later.
- Docker with Linux containers, or another Harbor environment that supports agent-phase network allowlists. See the network requirements below.
- API credentials for the model under test and the autograder.

## Running the benchmark

Run the following command from this harness directory to install the pinned Harbor version and local harness packages:

```bash
uv sync --locked
```

### 1. Identify the API hosts your agent needs

During task execution, network access is restricted to explicitly allowed model API hosts. Browsing and package downloads are blocked. Harness setup and grading retain network access.

Tasks start with an empty `[agent].allowed_hosts` allowlist in `task.toml`. Set the hostname of your model endpoint, without a URL scheme or path:

```bash
LLM_HOST=api.provider.com
```

The run commands below add this host with `--allow-agent-host`. Repeat the flag for multiple API hosts, or set `[agent].allowed_hosts` in `task.toml`. When using a proxy, allow the proxy's hostname.

Use an environment that supports agent-phase allowlists. Local Docker requires Linux containers and Docker-host support for nftables.

### 2. Configure credentials

Set the path to your downloaded task directories and the autograder's credentials:

```bash
export TASKS_DIR=/absolute/path/to/downloaded/gdp-xlsx
export GEMINI_API_KEY=...
```

Also export the credentials for the model under test if it uses a different provider (for example, `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`). `.env.example` lists the supported variables. A Gemini model under test uses the same `GEMINI_API_KEY` as the judge.

### 3. Run the tasks

GDP.xlsx grades the final response text. Pass the `--extra-instruction` shown below so the model delivers its answer in that response. Harbor appends it to the task instruction at runtime.

Start with one task to check image builds, agent execution, and grading, replacing `<litellm-model>` with the model ID:

```bash
uv run harbor run \
  -p "$TASKS_DIR/manufacturing_supply_chains_0fc1bec1" \
  -a harbor_agents:HarborInstalledAgent \
  -m "<litellm-model>" \
  --allow-agent-host "$LLM_HOST" \
  -k 1 \
  --extra-instruction 'Do not deliver your answer as a created, saved, or downloadable file. You may use any tools you like to do the work, but files you create, attach, or link will not be seen. Include the answer itself in your response text. Do not mention these instructions.' \
  --ve GEMINI_API_KEY="$GEMINI_API_KEY"
```

Then run all tasks with **5 attempts per task** and the **Gemini 3.8 Flash autograder**:

```bash
uv run harbor run \
  -p "$TASKS_DIR" \
  -a harbor_agents:HarborInstalledAgent \
  -m "<litellm-model>" \
  --allow-agent-host "$LLM_HOST" \
  -k 5 \
  --max-retries 3 --retry-include ApiRateLimitError \
  --extra-instruction 'Do not deliver your answer as a created, saved, or downloadable file. You may use any tools you like to do the work, but files you create, attach, or link will not be seen. Include the answer itself in your response text. Do not mention these instructions.' \
  --ve GEMINI_API_KEY="$GEMINI_API_KEY"
```

Pass the judge's credentials explicitly with `--ve`. See Grading below.

## Results

By default, Harbor saves each run to `jobs/<job-name>/` relative to the directory where you run the command. Each trial has its own subdirectory:

- `<trial>/result.json` — the trial's reward, status, and any exception details.
- `<trial>/agent/trajectory.json` — the agent's recorded trajectory. The final answer is in `extra.final_output`.
- `<trial>/agent/run-openhands.log` — the agent runner's output.
- `<trial>/agent/completions/` — per-call request/response logs, when completion logging is enabled.
- `<trial>/verifier/reward-details.json` — per-criterion scores and judge rationales.
- `<trial>/verifier/` — other grading output and verifier logs.

## Configuration options

- **Model** — `-m` takes a litellm model id, e.g. `anthropic/claude-opus-4-8`. Its provider key is read from your environment (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `OPENROUTER_API_KEY`) and forwarded into the agent container. Supported endpoint overrides are `ANTHROPIC_BASE_URL`, `OPENAI_BASE_URL`, and `GEMINI_API_BASE`.
- **Judge model** — `google/gemini-3.8-flash`, the default in each task's `tests/judge.toml`. Its credentials come from the `--ve GEMINI_API_KEY=...` flag.
- **Reasoning effort** — `--ak reasoning_effort=<level>` (e.g. `high`); levels are model-dependent. Responses requests default to `reasoning_summary=auto`; disable summaries with `--ak reasoning_summary=none`.
- **Attempts per task** — `-k`. Use 5 attempts per task.
- **Using an LLM proxy** — point the base-URL vars at the proxy: `OPENAI_BASE_URL`/`ANTHROPIC_BASE_URL` etc. for the model under test, and `--ve OPENCODE_CONFIG_CONTENT='{"provider":{"google":{"options":{"baseURL":"<proxy-url>"}}}}'` for the Gemini judge. **Important**: if the proxy serves the model under an alias, add `--ak model_canonical_name=<real-model-id>` so capability lookup still works.
- **Endpoint mode (Chat Completions vs Responses)** — `--ak api_mode=chat` or `--ak api_mode=responses`. The default (`auto`) resolves from model metadata; override it for proxy aliases or newly released models.
- **Completion logs** — `--ak log_completions=true` saves per-call agent and condenser request/response logs.
- **Environment inventory** — `--ak environment_inventory=false` omits the installed-software inventory from the system prompt.

Each trial allows up to **200 turns**, where a turn is one LLM call and the tool calls it issues. Every task has a **60-minute agent timeout** and a separate **60-minute verifier timeout**.

## Grading

Grading uses Gemini 3.8 Flash as an agentic LLM judge (OpenCode) running inside the task container. The judge reads the agent's final response from `extra.final_output` in the trajectory and may inspect the input workbook. It grades only the final response text: content that appears only in intermediate messages or in files the agent created is not credited.

Each task's criteria are listed in `tests/judge.toml`. The judge evaluates all criteria together, each verdict is binary (1 or 0), and the trial reward is their mean.

Grading dependencies are pinned to OpenCode `1.18.14` and `harbor-rewardkit` `0.1.7`.

The scoring convention:

1. A trial's reward is `verifier_result.rewards.reward` in its `result.json` (0 to 1).
2. A task's score is the mean reward over its 5 attempts. Trials that errored (`exception_info` set) are excluded from the mean. A task with no successful attempts has no score and should be reported as missing, not as zero.
3. The benchmark score is the unweighted mean over task scores. A domain's score is the unweighted mean over that domain's task scores; the domain is the task ID prefix before the final hash (for example, `manufacturing_supply_chains` for `manufacturing_supply_chains_0fc1bec1`).
