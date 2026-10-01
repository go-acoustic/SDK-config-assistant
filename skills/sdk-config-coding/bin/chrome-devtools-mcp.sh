#!/usr/bin/env bash
#
# sdk-config-coding: launcher for the Chrome DevTools MCP server.
#
# Not bundled as a plugin MCP: sdk-config-assistant is shared with other
# skills, and a plugin-level server would start for all of their users. The
# setup wizard copies this file to ~/.claude/sdk-config-coding/ and
# registers it as the user-scoped MCP server "sdk-chrome-devtools".
#
# How the MCP reaches Chrome depends on the Chrome mode the user picked in
# setup, recorded as "chromeMode" in the per-machine marker
# (~/.claude/sdk-config-coding/setup-state.json):
#
#   dedicated (default) — connect to the ~/.chrome-acoustic-profile instance the
#                         plugin launches with --remote-debugging-port=9222.
#   default             — attach to the user's everyday Chrome via --autoConnect
#                         (Chrome 144+, remote debugging enabled at
#                         chrome://inspect/#remote-debugging). Chrome 136+ ignores
#                         --remote-debugging-port on the default profile, so
#                         --browser-url can't be used there.
#
# A missing marker, a v1 marker with no chromeMode, or an unreadable value all
# mean "dedicated", so installs set up before chromeMode existed are unchanged.
# The mode is read at MCP startup — after changing it, reconnect via /mcp or
# start a new session. The launcher has no plugin environment (it runs as a
# user-scoped server), so it must not rely on CLAUDE_PLUGIN_ROOT/DATA.

set -uo pipefail

state_file=""
if [ -f "$HOME/.claude/sdk-config-coding/setup-state.json" ]; then
  state_file="$HOME/.claude/sdk-config-coding/setup-state.json"
fi

mode="dedicated"
if [ -n "$state_file" ]; then
  parsed="$(sed -n 's/.*"chromeMode"[[:space:]]*:[[:space:]]*"\([a-z]*\)".*/\1/p' "$state_file" | head -n 1)"
  [ "$parsed" = "default" ] && mode="default"
fi

echo "[sdk-config-coding] chrome-devtools MCP: chromeMode=$mode (marker: ${state_file:-none})" >&2

if [ "$mode" = "default" ]; then
  exec npx chrome-devtools-mcp@latest --autoConnect
else
  exec npx chrome-devtools-mcp@latest --browser-url=http://127.0.0.1:9222
fi
