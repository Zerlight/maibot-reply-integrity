"""Run with the application dependencies and an isolated MaiBot instance."""

import pytest

pytest.importorskip("src")

from plugin import create_plugin
from src.maisaka.builtin_tool.context import BuiltinToolRuntimeContext
from src.plugin_runtime.hook_payloads import deserialize_prompt_items, serialize_prompt_items
from src.llm_models.payload_content.context_item import ContextItemBuilder, RoleType, get_item_text


@pytest.mark.asyncio
@pytest.mark.parametrize("text", [
    "我已经改查 OpenAI 的 Tibo，等结果回来确认账号和帖子",
    "你说的 tibo 是 tibo_maker 吗？",
    "中" * 1200,
])
async def test_host_sends_the_exact_generated_text_in_one_segment(text):
    change = await create_plugin().preserve_generated_text(response=text)
    result = BuiltinToolRuntimeContext.post_process_reply_text(text, **change["modified_kwargs"])
    assert result == [text]


@pytest.mark.asyncio
async def test_modified_request_is_accepted_by_the_real_host_context_protocol():
    plugin = create_plugin()
    await plugin.capture_tool_facts([{
        "item_type": "FunctionCallOutputItem", "tool_name": "x_search_result", "call_id": "test-call",
        "output": "Search complete: synthetic_handle https://x.com/example/status/1", "success": True,
        "meta": {"timestamp": "2026-01-01T00:00:00+00:00"},
    }], 1, "synthetic-session")
    original = [ContextItemBuilder().set_role(RoleType.System).add_text_content("Persona").build()]
    result = await plugin.inject_planner_facts(
        serialize_prompt_items(original), 1, "synthetic-session", {"reply_reference": "Give the search summary"},
    )
    restored = deserialize_prompt_items(result["modified_kwargs"]["items"], item_schema_version=1, original_items=original)
    assert restored[0] is original[0]
    prompt = "\n".join(get_item_text(item) for item in restored)
    assert "Give the search summary" in prompt and "synthetic_handle" in prompt
    assert "https://x.com/example/status/1" in prompt
