# Reply Integrity

A MaiBot SDK extension that preserves Planner instructions and recent tool observations, then sends the Replier's text as one message. It uses three public hooks and requires MaiBot 1.3.19+, SDK 2.20+, and Context Item schema v1.

- `maisaka.planner.before_request` captures up to four recent tool outputs from the selected Planner context. Reply receipts are excluded.
- `maisaka.replyer.before_model_request` adds a system policy and a separate `<planner_instruction_and_facts>` block containing the current reply reference, legacy reason, and relevant recent observations.
- `maisaka.reply.before_post_process` skips text splitting, typo injection, bracket removal, and stock overflow replies. Existing attachments and normal delivery handling remain available.

The plugin imports only the SDK and the Python standard library. It does not patch Host source files or replace Host functions. No capability grants or extra model calls are required.

Observations are kept only in memory, isolated by session, with at most 64 sessions and 12,000 characters per observation. Truncated data is marked. The cache is refreshed at each Planner request and cleared on unload. Existing history retained by MaiBot follows its own retention settings.

## Installation

Copy this directory to `plugins/reply_integrity` and load it through the plugin manager. Enable the `local.reply-integrity` extension. The Host validates the required hooks during registration.

The global response post-processing switch can stay off as an additional safeguard. Disabling or unloading this plugin removes its prompt policy and per-reply hook. Reloading the plugin clears its in-memory observation cache.

## Tests

```sh
uv run --group dev pytest -q tests/test_plugin.py
```

Run `tests/test_host_integration.py` in an isolated MaiBot source workspace with the application's dependencies. It checks actual Host Context Item deserialization and the normal reply post-processing entry point with the plugin's flags.

## Compatibility

The plugin uses the SDK Hook contract rather than private `src.*` imports. An upgrade that removes a required hook or changes Context Item schema v1 requires a plugin update. The schema check reports unsupported versions explicitly. Recent observations become available after the next Planner request; guidance supplied directly in `reply_reference` remains available immediately.

This is a private deployment package. No public distribution license is granted.
