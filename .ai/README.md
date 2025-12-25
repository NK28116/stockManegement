# AI TURN (Project Scope)

This directory controls **AI turn per project**.

## turn values

- claude  : implementation (Claude Code CLI)
- gemini  : design / review (Gemini CLI or MCP)
- serena  : decision / commit judgment (Claude Desktop)

## Priority Rule

If this file exists:
- project/.ai/turn → USED

Otherwise:
- root/.ai/turn → fallback
