# Local Agent Setup for UEFN, VS Code, Verse, and MCP

This guide is for UEFN developers who primarily work in VS Code and want a local agent workflow across:

```text
VS Code / Codex / Pi / local model
  -> UEFN MCP server
      -> Verse workspace tools
      -> UEFN editor HTTP bridge
          -> uefn_listener.py inside UEFN
          -> Unreal Python API
```

The MCP server does not replace Epic's VS Code Verse extension. Keep Epic's extension as the source of truth for Verse editing, syntax support, compile diagnostics, and UEFN integration. MCP gives an agent structured access to project context, Verse files, editor state, logs, and safe editor automation.

## What Each Layer Does

| Layer | Purpose |
|-------|---------|
| VS Code | Your normal editor for Verse and project files |
| Epic Verse extension | Verse language support, diagnostics, UEFN-aware editing |
| `verse-uefn` skill | Agent instructions for safe Verse/UEFN behavior |
| MCP server | Tool bridge for agents such as Codex, Pi, or local-model VS Code agents |
| Verse workspace tools | Safe project-root-limited file operations for `.verse` files |
| UEFN listener | HTTP bridge running inside the editor process |
| Unreal Python API | Editor automation only: actors, assets, levels, viewport, logs |

## Python vs Verse

Use **Verse** for runtime gameplay:

- custom devices
- NPC behavior
- player-facing rules
- scoring and round logic
- persistence and simulation

Use **Python** for editor automation:

- inspecting actors and assets
- placing, moving, or selecting actors
- reading editor logs
- validating editor/project state
- batch editor operations

Use **MCP** to coordinate both. The agent should edit Verse files through workspace tools and use UEFN editor tools only when it needs live editor state or editor-side automation.

## Prerequisites

- UEFN installed and your project opens successfully.
- Python Editor Script Plugin enabled in UEFN.
- VS Code with Epic's Verse extension installed.
- `mise` installed for host Python/tool management.
- A local clone of this repository.
- One or more MCP clients:
  - Codex
  - Pi with `pi-mcp-adapter`
  - a VS Code agent that can launch stdio MCP servers

## Install the MCP Server

From this repository:

```powershell
mise install
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

Verify the host-side server dependencies:

```powershell
.\.venv\Scripts\python.exe -c "from mcp.server.fastmcp import FastMCP; print('mcp ok')"
```

## Start the UEFN Listener

For the first run, start it manually:

1. Open your UEFN project.
2. Open **Tools > Execute Python Script**.
3. Select this repository's `uefn_listener.py`.
4. Confirm the status window says the listener is running.

Optional auto-start:

```powershell
Copy-Item .\uefn_listener.py <YourUEFNProject>\Content\Python\uefn_listener.py
Copy-Item .\init_unreal.py <YourUEFNProject>\Content\Python\init_unreal.py
```

UEFN runs `init_unreal.py` when the project opens.

## Project Root Selection

Most Verse tools need to know which UEFN project is in scope. The server resolves the project root in this order:

1. Tool argument `project_root`, when an agent passes one explicitly.
2. Environment variable `UEFN_PROJECT_ROOT`, when configured in the MCP client.
3. Current working directory discovery, looking for `.uefnproject`, `.uproject`, `Verse/`, or `Plugins/`.

For one active project, use `UEFN_PROJECT_ROOT` in the client config. For several projects, either:

- keep one MCP config per project, each with its own `UEFN_PROJECT_ROOT`; or
- omit `UEFN_PROJECT_ROOT` and make sure the MCP client launches from the UEFN project directory; or
- ask the agent to pass `project_root` explicitly when calling Verse workspace tools.

Always ask the agent to call `uefn_get_project_context` before editing. If the reported project root does not match the open UEFN project, stop and fix the config before writing files.

## Install the Verse UEFN Skill

The skill teaches Pi/Codex-style agents how to work with Verse, UEFN, VS Code, and this MCP server without confusing runtime gameplay code with editor automation.

For Pi:

```powershell
pi install git:github.com/vl4dt/verse-uefn-skill
```

If you are installing from a local clone:

```powershell
git clone https://github.com/vl4dt/verse-uefn-skill.git
Set-Location .\verse-uefn-skill
pi install .
```

After installing it, use prompts such as:

```text
Use the verse-uefn skill. Connect to the UEFN MCP server, inspect project context, and help me create a Verse device for a timed scoring mechanic.
```

For Codex or another agent with local skill support, install the same repository into that agent's skill directory. The important file is:

```text
skills/verse-uefn/SKILL.md
```

## Codex MCP Configuration

Example project-level config:

```json
{
  "mcpServers": {
    "uefn": {
      "command": "D:/Lab/UEFN-Projects/uefn-mcp-server/.venv/Scripts/python.exe",
      "args": ["D:/Lab/UEFN-Projects/uefn-mcp-server/mcp_server.py"],
      "env": {
        "UEFN_PROJECT_ROOT": "D:/Lab/UEFN-Projects/MyIsland"
      }
    }
  }
}
```

If you prefer project discovery, remove the `env` block and launch Codex from the UEFN project root.

## Pi with pi-mcp-adapter

Configure `pi-mcp-adapter` to launch the same stdio server command:

```json
{
  "uefn": {
    "command": "D:/Lab/UEFN-Projects/uefn-mcp-server/.venv/Scripts/python.exe",
    "args": ["D:/Lab/UEFN-Projects/uefn-mcp-server/mcp_server.py"],
    "env": {
      "UEFN_PROJECT_ROOT": "D:/Lab/UEFN-Projects/MyIsland"
    }
  }
}
```

Then install the `verse-uefn` skill and tell Pi to use it when working on Verse or UEFN tasks.

## VS Code and Local Models

Recommended VS Code setup:

1. Open the UEFN project folder in VS Code.
2. Use Epic's Verse extension for language support.
3. Configure your VS Code agent to launch this MCP server over stdio.
4. Keep the UEFN editor open with `uefn_listener.py` running.
5. Ask the agent to call `uefn_get_project_context` before making Verse edits.

If your VS Code agent supports MCP tools and local models, give it the same command and arguments shown above. The model should use MCP tools for project context and file changes, while the Epic extension remains responsible for Verse language intelligence.

## Core Tool Workflow

Start every non-trivial task with:

```text
1. ping
2. uefn_get_project_context
3. validate_project_state
4. verse_list_files
```

Then choose the right path:

| Task | Preferred tools |
|------|-----------------|
| Read existing Verse | `verse_list_files`, `verse_read_file` |
| Create a Verse device | `verse_get_templates`, `verse_create_device` |
| Edit Verse | `verse_read_file`, `verse_write_file` |
| Debug Verse | `verse_get_diagnostics`, `get_editor_log` |
| Inspect level state | `get_all_actors`, `get_selected_actors`, `get_level_info` |
| Editor automation | `spawn_actor`, `set_actor_transform`, `select_actors`, `focus_selected` |
| Project validation | `validate_project_state`, `get_project_info` |

Dangerous tools require `confirm=True`:

- `execute_python`
- `delete_asset`
- `delete_actors`
- `shutdown`

Agents should prefer structured tools over `execute_python`.

## Example Use Case: Inspect Actors and Create a Verse Device

Prompt:

```text
Use the verse-uefn skill and the UEFN MCP server. Inspect the current level, then create a basic Verse device named match_timer_device. Do not use execute_python.
```

Expected agent flow:

```text
1. ping
2. validate_project_state
3. get_all_actors
4. uefn_get_project_context
5. verse_get_templates
6. verse_create_device(name="match_timer_device", template="basic_device")
7. verse_get_diagnostics
```

Then compile/check Verse in UEFN or VS Code and feed any diagnostics back to the agent.

## Example Use Case: Fix a Verse Diagnostic Loop

Prompt:

```text
Use the verse-uefn skill. Read the current Verse diagnostics, inspect the referenced file, patch the smallest safe fix, and wait for me to rebuild.
```

Expected agent flow:

```text
1. uefn_get_project_context
2. verse_get_diagnostics
3. verse_read_file(path="<diagnostic file>")
4. verse_write_file(path="<diagnostic file>", content="<patched content>")
5. verse_get_diagnostics
```

Keep each iteration small. Do not rewrite broad gameplay systems unless the diagnostics require it.

## Example Use Case: Place Editor Objects for a Verse Device

Prompt:

```text
Use UEFN MCP to create a simple test setup for my Verse device. Place the needed editor objects, select them, and tell me what needs to be wired in UEFN.
```

Expected agent flow:

```text
1. validate_project_state
2. get_project_info
3. get_level_info
4. spawn_actor or list_assets, depending on available assets
5. set_actor_transform
6. select_actors
7. get_editor_log
```

This is editor automation, so Python-backed UEFN tools are appropriate. The gameplay behavior still belongs in Verse.

## Example Use Case: Multi-Project Work

When switching projects, do one of these:

```text
Option A: update the client's UEFN_PROJECT_ROOT and restart the client.
Option B: launch the client from the UEFN project root and omit UEFN_PROJECT_ROOT.
Option C: ask the agent to pass project_root explicitly to Verse tools.
```

For safety, ask:

```text
Call uefn_get_project_context and confirm the project root before editing.
```

## Troubleshooting Checklist

- `ping` fails: make sure `uefn_listener.py` is running inside UEFN and the port matches.
- Verse tools see the wrong project: check `UEFN_PROJECT_ROOT` or launch directory.
- VS Code shows diagnostics but MCP does not: rebuild/check Verse in UEFN and inspect `get_editor_log`.
- Agent wants `execute_python`: ask it to use a structured MCP tool first.
- Several projects are open: only one UEFN listener should own the configured port.
