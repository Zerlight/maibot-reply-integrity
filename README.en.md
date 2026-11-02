# Reply Integrity

[简体中文](README.md)

**Give MaiBot's Replier the full facts while letting it speak in its own natural voice.**

Reply Integrity bridges the gap between MaiBot's **Planner** (planning & tool execution) and **Replier** (conversational expression) through official SDK hooks:
- **Preserves tool facts**: Passes the conversational goal and recent tool observations directly to the Replier, complete with execution status, timestamps, and truncation markers.
- **Isolates draft phrasing**: Instructs the Planner to jot down concise bullet points rather than a ready-to-send script, and moves background notes ahead of chat history so the Replier doesn't echo stiff, report-like wording.
- **Protects generated replies**: Sends the Replier's generated text straight to delivery, bypassing rule-based sentence splitting, typo injection, bracket stripping, and stock fallback replacements.

The plugin requires **no extra model calls**, **no core source edits**, **no API keys**, and **no additional capability grants**. At runtime, it relies solely on the official MaiBot Plugin SDK and the Python standard library.

---

## Why Persona Tuning Alone Isn't Enough

MaiBot separates **Planner (planning and tools)** from **Replier (expression)**. Search results, reply references, chat history, and final outgoing text pass through distinct stages. Many issues that look like a poorly tuned persona actually originate in this handoff pipeline:

1. **Missing facts between stages**
   MaiBot's standard reply path strips raw tool outputs from chat history. If the Planner's `reply_reference` also omits a key detail or status, the Replier has to answer in the dark. Tweaking `Personality` or `Reply style` cannot bring back facts that never reached the Replier.
2. **Planner drafts leak into casual chat**
   The Planner often writes formal instructions such as *"Advise the user that…"* and the Host appends that reference *after* chat history. Because those notes sit right before generation, the Replier frequently mirrors their bureaucratic vocabulary and sentence structure—making a casual chat sound like an official status report.
3. **Post-processing alters or replaces valid replies**
   When Host post-processing is enabled, spaces between Chinese and English words can trigger unintended splits that chop one sentence into multiple chat bubbles. Worse, if character length or segment count crosses a threshold, a hardcoded fallback can discard a complete, accurate answer and replace it with stock phrases like `懒得说` (*"can't be bothered"*) or `不晓得` (*"don't know"*).

> **Troubleshooting Note:** These mechanisms have been verified against MaiBot 1.3.19's standard reply pipeline; whether they trigger depends on your configuration and input. **Seeing *"I don't know"* in chat does not by itself pinpoint the cause**—it could be honest uncertainty from the model, missing context between stages, or a post-processing fallback replacement. Always cross-check tool outputs, raw generated text, and final delivery logs.

---

## Scenarios: Before & After

*Note: The examples below are fictional illustrations, not raw chat logs. The "Without plugin" column shows potential pipeline failure modes, while "With Reply Integrity" shows the intended conversational behavior rather than fixed templates or guaranteed model outputs. Post-processing comparisons assume the corresponding Host switches are enabled.*

### Scenario 1: Search found the facts, but chat sounds like a formal report

| Stage | Without the plugin | With Reply Integrity |
| :--- | :--- | :--- |
| **User question** | *"Did you find the project's update?"* | *"Did you find the project's update?"* |
| **Planner reference** | *"Based on current findings, inform the user that version 2.4 has been released and direct them to the release notes."* (Appended **after** chat history) | Tool schema requests brief notes only, e.g., `Version: v2.4`, `Goal: share update`, `Link: https://example.org/releases/v2.4` (Moved **before** chat history) |
| **Tool context** | Raw tool outputs are excluded from the Replier's chat history; the Replier relies entirely on the Planner's summary. | Up to 4 recent non-`reply` tool outputs from the active Planner context are injected before chat history, preserving status and truncation flags. |
| **Illustrative reply** | *"The project has currently released version 2.4; you may consult the release notes for further details."* | *"Found it! It's on v2.4 now. Here's what changed: https://example.org/releases/v2.4"* |

**How it helps:** Updating the tool parameter description nudges the Planner to write concise points, though prompts cannot deterministically prevent every full-sentence draft. Even when the Planner still writes a polished paragraph, the Replier is instructed to extract only the facts and intent while speaking in its own voice.

### Scenario 2: A search is running (or finished), but the bot replies *"don't know"*

Asynchronous MCP searches require distinguishing between a request that is still running and one that has already returned:

| Actual state | Potential failure without the plugin | With Reply Integrity |
| :--- | :--- | :--- |
| **Tool returns `pending`** (the Planner knows the request is still running) | The reference omits the pending state, so the Replier has no idea a search is in progress and simply replies *"I don't know."* | Passes both the `pending` status and the waiting intent to the Replier, prompting an honest update: *"Still waiting on the results—give it a moment."* |
| **Tool completed** (the Replier generated a full answer with links) | Segment-count overflow during post-processing discards the generated answer and replaces it with `懒得说` (*"can't be bothered"*) or `不晓得` (*"don't know"*). | Bypasses the overflow fallback and hands the generated answer intact to the delivery pipeline. |

**How it helps:** The second failure mode is easy to misdiagnose as the model refusing to cooperate, even though it already wrote a complete answer that got overwritten before delivery. Reply Integrity preserves both upstream status and downstream text. (It does not speed up external tools themselves; `pending` tasks still require a subsequent check.)

### Scenario 3: A single mixed-language sentence gets chopped into multiple bubbles

Suppose the Replier generates the following sentence:

```text
我已经改查 OpenAI 的 demo，你说的 demo 是 demo_maker 吗？
```

| State | Delivered chat bubbles (illustrative) |
| :--- | :--- |
| **Without the plugin** (with rule-based splitting enabled) | **Bubble 1:** `我已经改查 OpenAI`<br>**Bubble 2:** `的 demo，你说的 demo`<br>**Bubble 3:** `是 demo_maker 吗？` |
| **With Reply Integrity** | **Bubble 1:** `我已经改查 OpenAI 的 demo，你说的 demo 是 demo_maker 吗？` |

**How it helps:** `maisaka.reply.before_post_process` skips text splitting, typo injection, and overflow replacement so the generated reply enters normal delivery as a single intact message. It does not fix errors written by the model itself, and platform message-length limits still apply.

---

## Installation & Upgrades

### Requirements

- **MaiBot**: `1.3.19+`
- **maibot-plugin-sdk**: `2.20+`
- **Context Item Schema**: `v1`

*Verified on MaiBot `1.3.19` with SDK `2.20.0`. Other versions within the supported range must preserve the hook contracts described below.*

### Setup Steps

1. Copy this directory into your MaiBot instance at `plugins/reply_integrity/`.
2. Load or reload **Reply Integrity** in the plugin manager (plugin ID: `local.reply-integrity`).
3. Check the logs for `Reply Integrity 1.1.0 hooks active`.

### Upgrading & Uninstalling

- **Upgrading from 1.0.0**: Overwrite the existing `plugins/reply_integrity/` directory and reload. The plugin ID remains `local.reply-integrity`, so your enabled state carries over without extra configuration.
- **Disabling or unloading**: Unloading or disabling the plugin immediately removes its prompt injections and per-reply post-processing overrides. MaiBot's global response post-processing toggle remains untouched in your Host configuration.

---

## How It Works

### 1. Hook Pipeline

| Public Hook | Stage & Responsibility |
| :--- | :--- |
| `maisaka.planner.before_request` | Captures up to 4 recent non-`reply` tool outputs from the active context and rewrites the `reply_reference` parameter description on the `reply` tool to ask for concise bullet points and core facts. |
| `maisaka.replyer.before_request` | Stashes the original reference and reason in an internal per-call field and swaps in a one-time marker so the Host does not append the raw draft after chat history (preserving retry idempotency). |
| `maisaka.replyer.before_model_request` | Strips the temporary marker, inserts the `<planner_instruction_and_facts>` block after system rules and before chat history, and appends a brief conversational cue at the end of normal chat requests. |
| `maisaka.reply.before_post_process` | Sets `skip_post_process=True`, `enable_splitter=False`, and `enable_chinese_typo=False` to bypass splitting, typo injection, bracket cleanup, and stock overflow fallbacks while keeping attachments and standard delivery intact. |

### 2. Context Layout Comparison

For normal chat requests, the context sequence sent to the Replier model changes as follows (simplified to omit optional expression-style blocks):

```text
[Host Default] Persona & system rules → Chat history → Planner reference → Current reply requirements
[With Plugin]  Persona & system rules → Planner notes & tool facts → Chat history → Current reply requirements → Brief conversational cue
```

By default, the Host places the Planner reference *after* chat history. Moving background notes and tool facts *before* chat history keeps the tail end of the prompt anchored in the actual conversation and the user's latest message—reducing the tendency to echo draft phrasing (though context ordering is a soft nudge rather than a hard guarantee).

### 3. Scope & Safety Boundaries

- **Chat vs. document generation**: Chat history content, roles, and relative ordering remain untouched. Conversational rephrasing rules apply only to standard `maisaka.replyer` chat requests (`request_type == "maisaka.replyer"`), leaving plugin-API document generation unaffected. Even in casual chat, explicit requests for formal writing, verbatim quotes, code blocks, names, numbers, and URLs are preserved accurately.
- **Untrusted tool output isolation**: Tool observations are treated strictly as untrusted data. Embedded `<` characters inside the JSON payload are escaped as `\u003c` within `<planner_instruction_and_facts>`, and the system policy explicitly forbids following instructions found inside tool outputs.
- **No word blacklists**: The plugin guides tone through structure and prompt policy rather than stripping specific words via regex or vocabulary blacklists.

---

## Caching & Limitations

- **In-memory session cache**: Tool observations are cached in memory per `session_id` (capped at **64 sessions**, **4 observations per session**, and **12,000 characters per observation**, with an explicit `"truncated": true` flag when clipped). Each Planner request refreshes that session's cache, and unloading the plugin clears all cached entries.
- **Context visibility window**: Only recent tool outputs present in the Planner's current context are captured. Newly produced tool outputs enter the cache on the next Planner request, and details clipped beyond 12,000 characters are not available to the Replier.
- **Zero extra disk logging**: The plugin writes no persistent logs of its own; Host prompt traces, reasoning logs, and chat history continue to follow your Host retention settings.
- **Prompt-level constraints**: Tool schema descriptions and system prompts guide model behavior but cannot mathematically guarantee bullet-point formatting or a specific speaking style on every turn.
- **Hook execution order**: If other installed plugins modify the same prompt items or reply kwargs, the final behavior depends on hook execution order.
- **Contract compatibility**: Future changes to Host hook signatures or Context Item schema versions will require plugin updates. Because the Host skips failing hook handlers by default, check your logs after upgrading MaiBot.
- **Platform message limits**: Because automatic sentence splitting is bypassed, very long replies are sent as a single message and remain subject to your chat platform's maximum message length.

---

## Verification & Tests

Run the standalone unit test suite (5 tests covering tool schema rewriting, prompt ordering & retry idempotency, session cache eviction & truncation bounds, invalid payload rejection, and non-chat style isolation):

```sh
uv run --group dev pytest -q tests/test_plugin.py
```

In an isolated MaiBot source environment with full Host dependencies installed, you can also run the 2 Host integration tests (which exercise the real prompt builder, Context Item deserializer, and text post-processing entry point):

```sh
python -m pytest -q tests
```

*All tests use synthetic fixtures and never invoke external models or send live messages.*

---

## Changelog

### 1.1.0

- Decoupled Planner draft phrasing from Replier voice via `reply_reference` schema updates, style isolation policies, and a trailing conversational cue.
- Eliminated the Host's duplicate trailing reference block while preserving retry state and custom hook kwargs.
- Added bilingual documentation in Simplified Chinese and English.

---

## License

[MIT](LICENSE)
