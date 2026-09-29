# agent-harness

The GDP.xlsx agent loop, built on the OpenHands SDK. It runs the model with
terminal, file-editor, and task-tracker tools, plus any configured MCP tools,
and records the trial as an ATIF trajectory.

Responses requests default to `reasoning_summary=auto`; pass
`--ak reasoning_summary=none` to disable summaries.

Completion logging is opt-in with `--ak log_completions=true`. The runner
requires `model`, `instruction`, and `maxTurns`; the adapter supplies a
200-turn budget. Native SDK state lives in `/tmp/openhands_state` inside
the container. See the [benchmark README](../README.md) for retained traces,
upstream provenance, and the local Responses tool-output compatibility fix.

## Environment context

The runner reads the checked-in
[environment_context.md](src/agent_harness/environment_context.md) and appends
it via `AgentContext.system_message_suffix`. It preserves the default OpenHands
base prompt (or the configured `systemPrompt`). The overview lists explicit
Python package pins and import names, system packages, and command names. It
contains no skills, usage examples, or task strategies.

Update `environment_context.md` whenever the task images' base image or installed
dependencies change. Keep package versions, import names, and system command names
consistent with those images.

The Markdown is bundled with the runner in both staged images and self-install
archives. Trials only load the file; they perform no environment discovery.
ATIF's system step records the base prompt and appended context. Rebuild baked
runner images after changing the runner or the Markdown.

Set `environmentInventory: false` in the runner config, or use Harbor's
`--ak environment_inventory=false`, to run without this context. For custom
images, update the overview for that task set or disable it. MCP tool
definitions continue to come from the server.

## Development

```bash
uv run --locked --extra test pytest tests/ -q
```
