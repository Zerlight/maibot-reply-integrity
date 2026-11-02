# Reply Integrity

[简体中文](README.md)

Give MaiBot's Replier the facts while letting it speak in its own voice.

Reply Integrity connects Planner and Replier through public SDK hooks. It preserves the conversational goal and recent tool observations, places those notes before chat history, and asks the Planner for points instead of a ready-to-send script. Generated text passes directly to normal delivery without splitting, typo injection, or stock overflow replies.

## When it helps

### Why changing the persona may not fix it

MaiBot separates **Planner (planning and tools)** from **Replier (expression)**. Tool results, reply references, chat history and delivered text pass through different stages. Some apparent persona problems originate in that pipeline:

- **Missing facts between stages.** The normal reply path filters raw tool results out of chat history. If the Planner's reference also omits a key fact, the Replier may give an irrelevant answer. Changing `Personality` or `Reply style` cannot restore missing information.
- **Planner wording leaks into chat.** A reference such as “advise the user that…” appears after chat history. The Replier may copy its vocabulary and structure, making a casual conversation sound like a report.
- **Post-processing changes a valid answer.** When the corresponding processing is enabled, spaces at Chinese/English boundaries can become split points. Length or segment-count overflow can also replace a valid answer with stock phrases such as `懒得说` (“can't be bothered”) or `不晓得` (“don't know”). Inspect the text before delivery to identify this case.

These mechanisms were checked in MaiBot 1.3.19's normal reply path; activation depends on configuration and input. **“I don't know” alone does not identify the cause.** It may express genuine uncertainty, missing context or a post-processing replacement. Compare tool results, generated text and delivery records.

No extra model calls, core source edits, API keys, or capability grants are needed. Runtime code uses only the SDK and Python standard library.

## Before / after examples

These are fictional examples, not chat logs. The before column illustrates possible failures; suggested replies illustrate intended behavior, not fixed templates or guaranteed output. Post-processing comparisons assume the corresponding Host processing is enabled.

### Scenario 1: Search found the facts, but chat sounds like a report

| Stage | Without the plugin | With Reply Integrity |
| --- | --- | --- |
| Question | “Did you find the project's update?” | “Did you find the project's update?” |
| Example Planner reference | “Based on the available findings, inform the user that version 2.4 has been released and direct them to the release notes.” Placed after history. | The tool description requests points such as `Version: v2.4`, `Goal: share the update`, and `Link: https://example.org/releases/v2.4`. Notes move before history. |
| Tool context | Raw results are excluded from the Replier's chat history; facts depend on the Planner's reference. | Up to four recent non-reply tool outputs from the selected Planner context are inserted before history, with status and truncation markers. |
| Illustrative reply | “The project has currently released version 2.4; you may consult the release notes for further details.” | “Found it! It's on v2.4 now. Here's what's changed: https://example.org/releases/v2.4” |

The schema description requests points; it does not deterministically convert every draft into them. Even if the Planner supplies full sentences, the Replier receives a policy to extract facts and intent without adopting the background wording.

### Scenario 2: Search is running, but the reply says “don't know”

An asynchronous MCP search may still be pending or may already have completed. Those states need different replies.

| Actual state | Possible failure without the plugin | With Reply Integrity |
| --- | --- | --- |
| The tool returns `pending`; the Planner knows the request is running. | The reference omits that state, and the Replier says “I don't know” instead of explaining progress. | The Replier receives the pending state and waiting intent, with a policy to explain it honestly: “Still waiting for it to come back.” |
| The tool completed, and the Replier generated a full answer with links. | Segment overflow before delivery replaces that answer with `懒得说` (“can't be bothered”) or `不晓得` (“don't know”). | The plugin bypasses the stock fallback and passes the generated answer intact to delivery. |

The second failure can look like a model refusing to help even though it already wrote the answer. The plugin preserves facts, status and generated text. It does not speed up external searches; pending requests still need a later check.

### Scenario 3: One mixed-language sentence becomes several bubbles

Generated text:

```text
我已经改查 OpenAI 的 demo，你说的 demo 是 demo_maker 吗？
```

**Possible fragments with rule-based splitting enabled and no plugin:**

> Bubble 1: `我已经改查 OpenAI`
>
> Bubble 2: `的 demo，你说的 demo`
>
> Bubble 3: `是 demo_maker 吗？`

These fragments illustrate the symptom; exact boundaries depend on configuration.

**With the plugin:**

> Bubble 1: `我已经改查 OpenAI 的 demo，你说的 demo 是 demo_maker 吗？`

`maisaka.reply.before_post_process` bypasses text splitting, typo injection and overflow replacement, so the original text enters normal delivery as one segment. It does not correct mistakes already generated by the model. Platform message-length limits still apply.

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

Normal chat context order, simplified to omit optional expression-style blocks:

```text
[Host]   Persona and rules → Chat history → Planner reference → Current requirements
[Plugin] Persona and rules → Planner points and tool facts → Chat history → Current requirements → Short conversational cue
```

The original reference follows history but is not necessarily the last request item. Moving background notes earlier puts the actual conversation and current question later in context, aiming to reduce copied draft wording. Reordering alone cannot guarantee a natural voice.

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
