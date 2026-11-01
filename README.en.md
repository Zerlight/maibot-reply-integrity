# Reply Integrity

[简体中文](README.md)

Give MaiBot's Replier the facts while letting it speak in its own voice.

Reply Integrity connects Planner and Replier through public SDK hooks. It preserves the conversational goal and recent tool observations, places those notes before chat history, and asks the Planner for points instead of a ready-to-send script. Generated text passes directly to normal delivery without splitting, typo injection, or stock overflow replies.

## When it helps

- Search returned useful facts, but the Replier lacks the tool observations.
- A formal Planner draft makes the final chat reply sound like a report.
- Spaces break mixed-language sentences into bubbles, or a valid long reply becomes a stock fallback.

No extra model calls, core source edits, API keys, or capability grants are needed. Runtime code uses only the SDK and Python standard library.

## Examples

These are fictional scenarios. Suggested replies illustrate the intended behavior, not fixed templates or guaranteed output.

**Search results without the report voice**

Chat: “Did you find the project's update?”

A Planner draft might say: “Based on the available findings, inform the user that version 2.4 has been released and direct them to the release notes.” The tool description instead asks for points:

```text
- Goal: share the update
- Version: v2.4
- Link: https://example.org/releases/v2.4
```

The Replier can say: “Found it! It's on v2.4 now. Here's what's changed: https://example.org/releases/v2.4”.

**Honest pending results**

A tool result of `pending` stays pending. The policy asks the Replier to explain that it is still waiting, rather than treating it as an empty search or inventing an answer.

**Intact mixed-language text**

`你说的 demo 是 demo_maker 吗？` enters normal delivery as one exact text segment. Spaces around `demo` do not split it. Platform message-length limits still apply.

## Installation and upgrades

Requires MaiBot **1.3.19+**, `maibot-plugin-sdk` **2.20+**, and Context Item schema **v1**. Verified with MaiBot 1.3.19 / SDK 2.20.0. Other versions must retain the hook contracts below.

1. Copy this directory to the instance's `plugins/reply_integrity/`.
2. Load or reload **Reply Integrity** in the plugin manager. Its stable ID is `local.reply-integrity`.
3. Look for `Reply Integrity 1.1.0 hooks active` in the log.

Replace the same directory when upgrading from 1.0.0. No additional configuration is required. Disabling or unloading the plugin removes its prompt and per-reply behavior. MaiBot's global response post-processing switch is independent; this plugin does not change it.

## How it works

| Public hook | Behavior |
| --- | --- |
| `maisaka.planner.before_request` | Captures four recent non-reply tool outputs and changes only the `reply_reference` parameter description to request concise points and facts. |
| `maisaka.replyer.before_request` | Carries the original notes in a per-call field. A temporary marker prevents the Host from appending the raw draft after history, including on retries. |
| `maisaka.replyer.before_model_request` | Removes the marker, places notes after system rules and before chat history, and appends a short conversational cue for normal chat. |
| `maisaka.reply.before_post_process` | Bypasses splitting, typo injection, bracket cleanup and stock overflow replies. Attachments and normal delivery remain available. |

Normal chat request order:

```text
Persona and system rules → Planner goal and facts → Chat history → Current requirements → Conversational cue
```

History content, roles and relative order are preserved. Conversational rules apply only to normal `maisaka.replyer` requests, not document generation through the plugin API. Explicit formal-writing requests, quotations, code, names, numbers and URLs should retain their intended form.

Tool observations remain untrusted source data. Embedded `<` characters are escaped, and the system policy rejects instructions from tool content. No vocabulary blacklist deletes words from the response.

## Data and limits

- Observations are held in memory per session: 64 sessions, four observations each, 12,000 characters per observation. Truncation is explicit. Each Planner request refreshes its session cache; unload clears it.
- Only recent results present in the Planner's selected context are available. Fresh results enter the cache at the next Planner request. Truncated details may be absent.
- The plugin adds no persistent content log. Host prompt traces and chat history still follow the Host's retention settings.
- Tool descriptions and prompts cannot guarantee model compliance or a particular speaking style.
- Other plugins modifying the same request or response can affect the result according to hook order.
- Hook or Context Item changes require adaptation. The Host normally skips failing hook handlers; inspect its logs.
- Long replies are no longer split automatically. Platform length limits can still cause delivery failures.

## Minimal checks

```sh
uv run --group dev pytest -q tests/test_plugin.py
```

Five unit tests cover the tool schema, prompt order and retries, cache boundaries, invalid payloads, and the document-style boundary.

Two Host integration tests require an isolated MaiBot source workspace with its application dependencies:

```sh
python -m pytest -q tests
```

They exercise the actual prompt builder, Context Item deserializer and text post-processing entry point. All inputs are synthetic; tests do not call a model or send messages.

## 1.1.0

Separates Planner wording from Replier voice, updates the tool description and adds a conversational cue. Removes the Host's duplicate reference block while preserving retry state and other hook arguments. Includes Chinese and English documentation.

## License

[MIT](LICENSE)
