<p align="center">
  <img src="assets/logo.svg" width="112" height="112" alt="Reply Integrity logo">
</p>

# Reply Integrity

[简体中文](README.md)

**Give MaiBot's Replier the full facts—and strip away stiff "Agent-speak" so it can talk in its own natural voice.**

In a dual-agent setup (**Planner + Replier**—for example, pairing a reasoning-focused **`gpt-6.1-sol` Planner** with an expressive **`gpt-4o-2024-11-20` Replier**), reply quality frequently suffers from two cross-stage failure modes: **missing tool facts** and **background style contamination**.

Reply Integrity resolves both issues through official SDK hooks without touching MaiBot's core codebase:

- **Bridges the fact gap (fixes "brain–mouth split")**: Passes the conversational goal and recent tool observations directly to the Replier, complete with execution status, timestamps, and truncation markers.
- **Stops unidirectional style contamination (eliminates "Agent-speak" / *A言gent语*)**: Instructs the Planner to jot down concise bullet points rather than a ready-to-send script, and moves background notes ahead of chat history so **recency bias** doesn't pull the Replier into echoing stiff internal "Agent-speak."

The plugin requires **no extra model calls**, **no core source edits**, **no API keys**, and **no additional capability grants**. At runtime, it relies solely on the official MaiBot Plugin SDK and the Python standard library, with hot-reloadable settings in the MaiBot WebUI.

## Core Background: Why Persona Tuning Alone Isn't Enough

MaiBot separates **Planner (reasoning and tool execution)** from **Replier (persona and expression)**. Search results, reply references, chat history, and final outgoing text pass through distinct stages. When running capable model pairs like **`gpt-6.1-sol` (Planner) + `gpt-4o-2024-11-20` (Replier)**, problems that look like a poorly tuned persona typically stem from a cross-stage handoff dilemma:

```mermaid
flowchart TD
    planner["Planner: e.g., gpt-6.1-sol<br/>Optimized for dense logic; naturally writes in structured internal #quot;Agent-speak#quot;"]
    disconnected["[Brain–Mouth Split] Replier never sees raw tool outputs and answers #quot;I don't know#quot;"]
    draft["[Style Contamination] Notes sit after chat history; recency bias turns replies into #quot;Agent-speak#quot;"]
    replier["Replier: e.g., gpt-4o-2024-11-20<br/>Meant to chat naturally in persona, but trapped between missing facts and echoing machine notes"]

    planner -->|"If disconnected"| disconnected
    planner -->|"If naively connected"| draft
    disconnected --> replier
    draft --> replier
```

- **Brain–mouth split (missing facts between stages)**: MaiBot's standard reply path strips raw tool outputs from chat history. If the Planner's `reply_reference` omits a key detail or status, the Replier has to answer in the dark. Tweaking `Personality` or `Reply style` cannot restore facts that never reached the Replier.
- **Unidirectional style contamination ("Agent-speak" / *A言gent语*)**: Reasoning-heavy Planners naturally formulate thoughts in compressed, bureaucratic machine prose (e.g., *"Based on current findings, advise the user that…"*). Because the Host appends that reference **after** chat history, right before generation, **recency bias** causes the Replier to lazily mirror the Planner's syntax and tone—turning a casual conversation into stiff "Agent-speak."

> **Troubleshooting Note:** **Seeing *"I don't know"* in chat does not by itself pinpoint the cause**—it could be honest uncertainty from the model, missing context between stages, or a Host post-processing fallback replacement. Always cross-check tool outputs, raw generated text, and final delivery logs.

## Scenarios: Before & After

*Note: The examples below are fictional illustrations under the default settings, not raw chat logs. The "Without the plugin" column shows potential cross-stage failure modes, while "With Reply Integrity" shows the intended conversational behavior rather than fixed templates or guaranteed model outputs.*

### Scenario 1: Search found the facts, but chat sounds like "Agent-speak"

| Stage | Without the plugin | With Reply Integrity |
| :--- | :--- | :--- |
| **User question** | *"Did you find the project's update?"* | *"Did you find the project's update?"* |
| **Planner reference** | *"Based on current findings, inform the user that version 2.4 has been released and direct them to the release notes."* (Appended **after** chat history, triggering recency bias) | Tool schema requests brief notes only, e.g., `Version: v2.4`, `Goal: share update`, `Link: https://example.org/releases/v2.4` (Moved **before** chat history) |
| **Tool context** | Raw tool outputs are excluded from the Replier's chat history; the Replier relies entirely on the Planner's summary. | Up to 4 recent non-`reply` tool outputs from the active Planner context are injected before chat history, preserving status and truncation flags. |
| **Illustrative reply** | *"The project has currently released version 2.4; you may consult the release notes for further details."* (Classic "Agent-speak") | *"Found it! It's on v2.4 now. Here's what changed: https://example.org/releases/v2.4"* |

**How it helps:** Updating the tool parameter description nudges the Planner to write concise points, though prompts cannot deterministically prevent every full-sentence draft. Even when the Planner still writes a polished paragraph of "Agent-speak," the plugin moves it ahead of chat history and instructs the Replier to extract only the facts and intent while speaking in its own voice.

### Scenario 2: A search is running (or finished), but the Replier loses status or key details

Asynchronous MCP searches require distinguishing between a request that is still running and one that has already returned—and ensuring concrete details survive the handoff:

| Actual state | Potential failure without the plugin | With Reply Integrity |
| :--- | :--- | :--- |
| **Tool returns `pending`** (the Planner knows the request is still running) | The reference omits the pending state, so the Replier has no idea a search is in progress and simply replies *"I don't know."* | Passes both the `pending` status and the waiting intent to the Replier, prompting an honest update: *"Still waiting on the results—give it a moment."* |
| **Tool completed** (returned a specific version number and release link) | The Planner writes only a vague reference like *"announce the update,"* omitting the exact version and URL so the Replier cannot give a substantive answer. | Injects the raw tool output containing the exact version and URL so the Replier can answer accurately from the primary result. |

**How it helps:** The plugin synchronizes actual tool status and outputs with the Replier. It does not speed up external tools themselves; `pending` tasks still require a subsequent check.

## Installation & Upgrades

### Requirements

- **MaiBot**: `1.2.0–1.3.19`
- **maibot-plugin-sdk**: `2.7.1–2.21.0` (subject to your MaiBot version's own dependency requirements)
- **Context Item Schema**: `v1`

**Compatibility & Verification Notes:**
- **Verified coverage**: Full Host integration has been verified on MaiBot `1.3.19` with SDK `2.20.0`. Across all 26 MaiBot releases in the `1.2.0–1.3.19` range, hook contracts were verified and each release's original prompt-building function was executed in isolated test fixtures to confirm reference relocation in standard text chat. All 16 published SDK versions in range pass the 7-test unit suite. *(Note: This does not imply full end-to-end deployment testing across every possible Host/SDK permutation, nor were multimodal and retro-template paths tested per release.)*
- **Version boundaries**: MaiBot `1.1.x` uses the legacy `messages` payload and is incompatible. [`MaiBot 1.2.0`](https://github.com/Mai-with-u/MaiBot/tree/1.2.0) introduced the required Context Item v1 and `reply_reference` pipeline (and the plugin explicitly handles the combined reason/reference format used in `1.3.1–1.3.3`). Upper bounds reflect the latest verified stable releases—[`MaiBot 1.3.19`](https://github.com/Mai-with-u/MaiBot/releases/tag/v1.3.19) and [`SDK 2.21.0`](https://github.com/Mai-with-u/maibot-plugin-sdk/blob/v2.21.0/CHANGELOG.md)—rather than a guarantee for unreleased versions.

### Setup Steps

1. Copy this directory into your MaiBot instance at `plugins/reply_integrity/`.
2. Load or reload **Reply Integrity** in the plugin manager (plugin ID: `github.zerlight.reply-integrity`).
3. Check the logs for `Reply Integrity 1.3.1 hooks active`.

### Recommended: Disable Host Response Post-Processing

For the cleanest output, turn off the global **Response Post-Processing** switch in MaiBot WebUI, or set the following in the Host's `bot_config.toml`:

```toml
[response_post_process]
enable_response_post_process = false
```

In MaiBot `1.3.19`, disabling this master switch returns the Replier's generated text directly—skipping rule-based sentence splitting, typo injection, bracket stripping, and hardcoded overflow fallbacks (which can otherwise replace a valid, completed reply with stock phrases like `懒得说` or `不晓得`). Turning off only the sentence splitter sub-option is not equivalent. Because this is a global Host setting, the plugin does not modify it on your behalf. When disabled, long replies remain subject to your chat platform's maximum message length.

### Upgrading & Uninstalling

- **Upgrading to 1.3.0**: Configuration migration automatically removes the deprecated `bypass_post_processing` field while preserving your remaining settings. Response post-processing is now governed entirely by the Host; if you previously relied on the plugin's post-processing bypass, disable the Host's global switch as shown above.
- **Disabling or unloading**: Immediately stops prompt injection for future requests and clears the in-memory tool result cache without altering Host configuration files.

## Plugin Settings

Select **Reply Integrity** on MaiBot WebUI's plugin configuration page. The SDK automatically renders the settings form and hot-reloads saved changes without restarting MaiBot.

| Setting in `[plugin]` | Default | Description |
| :--- | :--- | :--- |
| `inject_tool_facts` | `true` | Capture recent tool outputs visible to the current Planner request and inject them into the Replier context. |
| `separate_reply_style` | `true` | Rewrite the Planner's `reply_reference` schema description, relocate notes before chat history, and append a conversational cue. |
| `max_results` | `4` | Number of recent tool outputs per session (**1–16**, excluding `reply` tool receipts). |
| `max_result_chars` | `12000` | Maximum characters per tool output (**1–48,000**); longer outputs are truncated and flagged. |

`inject_tool_facts` and `separate_reply_style` operate independently, while `enabled` toggles the entire plugin and `config_version` is managed by the SDK. Settings are persisted in `config.toml` inside the plugin directory. Saving configuration changes clears the in-memory tool cache so the next Planner request captures outputs under the updated limits (raising count or character limits increases prompt size, token usage, and memory footprint).

## How It Works

### 1. Hook Pipeline

| Public Hook | Stage & Responsibility |
| :--- | :--- |
| `maisaka.planner.before_request` | Captures recent non-`reply` tool outputs from the active context (when enabled) and rewrites the `reply_reference` parameter description on the `reply` tool to ask for concise bullet points and core facts. |
| `maisaka.replyer.before_request` | Stashes the original reference and reason in an internal per-call field and swaps in a one-time marker so the Host does not append the raw draft after chat history (preserving retry idempotency). |
| `maisaka.replyer.before_model_request` | Strips the temporary marker, inserts the `<planner_instruction_and_facts>` block after system rules and before chat history, and appends a brief conversational cue at the end of normal chat requests. |

### 2. Context Layout Comparison (Neutralizing Recency Bias)

Under the default settings for normal chat requests, the context sequence sent to the Replier model changes as follows (simplified to omit optional expression-style blocks):

```text
[Host Default] Persona & system rules → Chat history → Planner reference (triggers recency bias) → Current reply requirements
[With Plugin]  Persona & system rules → Planner notes & tool facts → Chat history → Current reply requirements → Brief conversational cue
```

By default, the Host places the Planner reference *after* chat history. Moving background notes and tool facts *before* chat history keeps the tail end of the prompt anchored in the actual conversation and the user's latest message—reducing the tendency to echo "Agent-speak" (though context ordering is a soft nudge rather than a hard guarantee).

### 3. Scope & Safety Boundaries

- **Chat vs. document generation**: Chat history content, roles, and relative ordering remain untouched. Conversational rephrasing rules apply only to standard `maisaka.replyer` chat requests (`request_type == "maisaka.replyer"`), leaving plugin-API document generation unaffected. Even in casual chat, explicit requests for formal writing, verbatim quotes, code blocks, names, numbers, and URLs are preserved accurately.
- **Execution vs. expression separation**: The Planner owns tool execution and scheduling; the Replier only composes reply text. Injected tool records serve strictly as factual context and grant no execution privileges to the Replier. System rules require concrete evidence before claiming an action ran or memory was saved—preventing the Replier from mistaking plans, prohibitions, or missing records for completed actions, or turning internal scheduling notes into unsolicited status reports or promises.
- **Untrusted tool output isolation**: Tool observations are treated strictly as untrusted data. Embedded `<` characters inside the JSON payload are escaped as `\u003c` within `<planner_instruction_and_facts>`, and the system policy explicitly forbids following instructions found inside tool outputs.
- **No word blacklists**: The plugin strips away "Agent-speak" through context placement and prompt policy rather than deleting specific words via regex or vocabulary blacklists.

## Caching & Limitations

- **In-memory session cache**: Tool observations are cached in memory per `session_id` (capped at **64 sessions**, defaulting to **4 observations per session** [configurable `1–16`] and **12,000 characters per observation** [configurable `1–48,000`], with an explicit `"truncated": true` flag when clipped). Each Planner request refreshes that session's cache, and config updates or plugin unload clear all cached entries.
- **Context visibility window**: Only recent tool outputs present in the Planner's current context are captured. Newly produced outputs enter the cache on the next Planner request, meaning a result produced in the same tool batch may not reach a concurrent `reply` call in that turn. If the Host has already condensed or summarized a tool output, the plugin receives that condensed content. The `truncated` flag reflects only the plugin's own character limit; clipped details are not available to the Replier.
- **Zero extra disk logging**: The plugin writes no persistent logs of its own; Host prompt traces, reasoning logs, and chat history continue to follow your Host retention settings.
- **Prompt-level constraints**: Tool schema descriptions and system prompts guide model behavior but cannot mathematically guarantee bullet-point formatting or a specific speaking style on every turn.
- **Hook execution order**: If other installed plugins modify the same prompt items or reply kwargs, the final behavior depends on hook execution order.
- **Contract compatibility**: Future changes to Host hook signatures or Context Item schema versions will require plugin updates. Because the Host skips failing hook handlers by default, check your logs after upgrading MaiBot.

## Verification & Tests

Run the standalone unit test suite (7 tests covering tool schema rewriting, prompt ordering & retry idempotency, session cache eviction & truncation bounds, invalid payload rejection, non-chat style isolation, SDK settings validation & legacy config migration, and hot reload with independent switches):

```sh
uv run --group dev pytest -q tests/test_plugin.py
```

In an isolated MaiBot source environment with full Host dependencies installed, you can also run the Host integration test (which exercises the real prompt builder and Context Item deserializer):

```sh
python -m pytest -q tests
```

*All tests use synthetic fixtures and never invoke external models or send live messages.*

## Changelog

### 1.3.1

- Clarified Planner execution and Replier expression roles, requiring evidence for execution status and discouraging promises derived from internal scheduling notes.
- Expanded compatibility to MaiBot `1.2.0–1.3.19` and SDK `2.7.1–2.21.0`; fixed trailing legacy reply reasons on MaiBot `1.3.1–1.3.3`.
- Updated the manifest author to `Zerlight` and synchronized bilingual documentation and compatibility verification limits.

### 1.3.0

- Removed the response post-processing hook and configuration toggle so reply post-processing follows Host settings; added setup guidance on disabling the Host's global response post-processing switch.
- Bumped `config_version` to `1.3.0`, automatically stripping the deprecated `bypass_post_processing` field during migration while preserving remaining settings.

## License

[MIT](LICENSE)
