"""Run with the application dependencies and an isolated MaiBot instance."""

import pytest

pytest.importorskip("src")

from plugin import CHAT_CUE, create_plugin
from src.chat.replyer.maisaka_generator_base import BaseMaisakaReplyGenerator
from src.llm_models.payload_content.context_item import ContextItemBuilder, RoleType, get_item_text
from src.maisaka.builtin_tool.context import BuiltinToolRuntimeContext
from src.plugin_runtime.hook_payloads import deserialize_prompt_items, serialize_prompt_items


@pytest.mark.asyncio
async def test_host_sends_exact_text_without_splitting_or_overflow_fallback():
    for text in ("我已经改查 OpenAI 的发布记录，等结果回来再确认", "你说的 demo 是 demo_maker 吗？", "中" * 1200):
        change = await create_plugin().preserve_generated_text(response=text)
        payload = change["modified_kwargs"]
        assert BuiltinToolRuntimeContext.post_process_reply_text(payload.pop("response"), **payload) == [text]


@pytest.mark.asyncio
async def test_real_host_prompt_builder_has_no_trailing_planner_draft(monkeypatch):
    plugin = create_plugin()
    history = [ContextItemBuilder().set_role(RoleType.User).add_text_content("查到了吗？").build()]
    generator = object.__new__(BaseMaisakaReplyGenerator)
    for name, value in {
        "_uses_retro_prompt": False, "_build_keyword_reaction_prompt": "",
        "_build_system_prompt": "Persona", "_build_final_user_message": "Answer the question",
        "_select_temporary_reply_style": "", "_build_history_messages": history,
    }.items():
        monkeypatch.setattr(generator, name, lambda *a, _value=value, **kw: _value)
    await plugin.capture_tool_facts([{
        "item_type": "FunctionCallOutputItem", "tool_name": "x_search_result", "call_id": "test-call",
        "output": "Found demo_handle https://example.org/post/1", "success": True,
        "meta": {"timestamp": "2026-01-01T00:00:00+00:00"},
    }], 1, "chat")
    prepared = (await plugin.isolate_planner_notes(
        {"reply_reference": "The available evidence indicates demo_handle."}, "Legacy summary",
    ))["modified_kwargs"]["reply_tool_args"]
    original = generator._build_request_messages([], None, "Legacy summary", reply_tool_args=prepared)
    assert prepared["reply_reference"] in "\n".join(get_item_text(item) for item in original)
    result = await plugin.inject_planner_facts(serialize_prompt_items(original), 1, "chat", prepared, "Legacy summary")
    restored = deserialize_prompt_items(result["modified_kwargs"]["items"], item_schema_version=1, original_items=original)
    texts = [get_item_text(item) for item in restored]
    assert restored[0] is original[0] and restored[3] is history[0]
    assert "The available evidence" in texts[2] and "Legacy summary" in texts[2]
    assert "https://example.org/post/1" in texts[2]
    assert not any("The available evidence" in t or "Legacy summary" in t for t in texts[3:])
    assert texts[-1] == CHAT_CUE and prepared["reply_reference"] not in "\n".join(texts)
