# SDK Config Assistant

A Claude skill from Acoustic that inspects your live website and generates a ready-to-test Acoustic Connect JavaScript SDK signal configuration.

## Install

Requires **Claude Desktop, Cowork tab**, plus the Claude in Chrome extension (this skill inspects your site live in the browser — it isn't supported in Claude Code or the Claude Desktop Chat tab).

**Add the marketplace:**
1. Open Claude Desktop and go to Cowork
2. Click **Customize**
3. Click **Plugins > Add > Add marketplace**
4. Enter as a URL: `go-acoustic/SDK-config-assistant`

**Install the plugin:**
1. Still under **Customize** in Cowork
2. Click **Plugins > Search**
3. Enter the plugin name **sdk-config-assistant**
4. Install it
5. Restart Claude Desktop to activate

Menu names occasionally change — if these steps look out of date, follow Anthropic's own guide instead: [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude) (Claude Help Center).

Then, in a Cowork conversation, start the skill:

```
/sdk-config-assistant
```

See [skills/SDK-config-assistant/README.md](skills/SDK-config-assistant/README.md) for the full quick guide — requirements, what the skill produces, and how to validate results.

## Need help?

Log in to the Acoustic Support Portal and submit a case. If your session hit an issue, attach the `<slug>.json` and `<slug>.analytics.json` files the skill saves locally at session close.

---

Copyright © 2026 Acoustic, L.P. All rights reserved.
