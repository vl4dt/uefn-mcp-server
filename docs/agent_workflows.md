# Agent Workflows

This server is designed to complement Epic's UEFN + VS Code + Verse extension workflow.

## Mental Model

```text
VS Code / Codex / Pi + pi-mcp-adapter / local model
  -> MCP server
      -> Verse workspace tools
      -> UEFN editor HTTP bridge
          -> uefn_listener.py inside UEFN
          -> Unreal Python API
```

- Use **Verse** for gameplay rules, custom devices, NPC behavior, persistence, and runtime logic.
- Use **Python** for editor-only automation: asset workflows, level layout, viewport/editor state, and production utilities.
- Use **MCP** to coordinate the agent's view of both the project files and the live UEFN editor.

## Codex MCP

Use the Python from the project virtual environment so Codex launches the same dependency set every time:

```json
{
  "mcpServers": {
    "uefn": {
      "command": "D:/Lab/UEFN-Projects/uefn-mcp-server/.venv/Scripts/python.exe",
      "args": ["D:/Lab/UEFN-Projects/uefn-mcp-server/mcp_server.py"],
      "env": {
        "UEFN_PROJECT_ROOT": "D:/Path/To/YourUefnProject"
      }
    }
  }
}
```

## Pi with pi-mcp-adapter

Configure `pi-mcp-adapter` to launch the same stdio server command:

```json
{
  "uefn": {
    "command": "D:/Lab/UEFN-Projects/uefn-mcp-server/.venv/Scripts/python.exe",
    "args": ["D:/Lab/UEFN-Projects/uefn-mcp-server/mcp_server.py"],
    "env": {
      "UEFN_PROJECT_ROOT": "D:/Path/To/YourUefnProject"
    }
  }
}
```

Exact file location depends on your Pi adapter setup.

## VS Code and Local Models

Use the Epic Verse extension as the source of truth for Verse language support. The MCP server adds agent tools for:

- `verse_list_files`
- `verse_read_file`
- `verse_write_file`
- `verse_create_device`
- `verse_get_templates`
- `verse_get_diagnostics`
- `uefn_get_project_context`

Recommended workflow:

1. Ask the agent to inspect `uefn_get_project_context`.
2. Use `verse_create_device` or `verse_write_file` to make code changes.
3. Build/check in UEFN or through your existing VS Code workflow.
4. Use `verse_get_diagnostics` and `get_editor_log` to feed errors back to the agent.
5. Use editor tools to inspect or configure level actors/assets.

## Safety

The following MCP tools require `confirm=True`:

- `execute_python`
- `delete_asset`
- `delete_actors`
- `shutdown`

Agents should prefer structured tools before `execute_python`.

## Examples

Inspect actors and create a Verse device:

```text
1. Call get_all_actors.
2. Call verse_create_device with name "score_device".
3. Ask UEFN/VS Code to build Verse.
4. Call verse_get_diagnostics if errors appear.
```

Fix a Verse diagnostic loop:

```text
1. Call verse_get_diagnostics.
2. Call verse_read_file for the referenced file.
3. Patch with verse_write_file.
4. Rebuild in UEFN and repeat until diagnostics are clear.
```

