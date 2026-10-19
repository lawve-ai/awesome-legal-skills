# Connect the LibreJustice MCP server

Every tool this skill uses (`search_decisions`, `get_decision`, `search_norms`, `get_norm`) is served by the LibreJustice remote MCP server: the skill does nothing without it.

- Endpoint: `https://librejustice.fr/mcp`
- Transport: streamable HTTP
- Auth: OAuth 2.1, auto-discovered by the client. The browser flow creates a free account if the user does not have one.

## Agent CLIs

Claude Code: the plugin installs the connector and the skills together:

```
/plugin marketplace add librejustice/librejustice
/plugin install librejustice@librejustice
```

or connector only:

```
claude mcp add --transport http librejustice https://librejustice.fr/mcp
```

Codex CLI:

```
codex plugin marketplace add librejustice/librejustice
codex plugin add librejustice@librejustice
```

Any client that reads a JSON MCP config:

```json
{"mcpServers": {"librejustice": {"type": "http", "url": "https://librejustice.fr/mcp"}}}
```

## Chat apps

claude.ai, ChatGPT (Developer mode), Le Chat (Mistral), Perplexity: add a custom connector pointing at `https://librejustice.fr/mcp` and authorize via OAuth. Step-by-step per client: <https://librejustice.fr/mcp-guide>
