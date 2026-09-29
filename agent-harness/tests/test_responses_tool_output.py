"""Keep multi-block observations valid when replayed to the Responses API."""

import pytest

from openhands.sdk.llm.message import ImageContent, Message, TextContent
from openhands.sdk.llm.utils import responses_serialization

from agent_harness import openhands_patches


@pytest.fixture
def serialize(monkeypatch):
    monkeypatch.setattr(openhands_patches, "_responses_tool_output_fix_installed", False)
    monkeypatch.setattr(
        responses_serialization,
        "_tool_to_responses_items",
        responses_serialization._tool_to_responses_items,
    )
    openhands_patches.install_responses_tool_output_fix()
    serializer = responses_serialization._tool_to_responses_items
    openhands_patches.install_responses_tool_output_fix()
    assert responses_serialization._tool_to_responses_items is serializer
    return serializer


def test_error_observation_emits_one_output_per_call(serialize):
    message = Message(
        role="tool",
        tool_call_id="call_error",
        content=[TextContent(text="Command rejected"), TextContent(text="Error details")],
    )
    assert serialize(message, vision_enabled=True) == [
        {
            "type": "function_call_output",
            "call_id": "call_error",
            "output": "Command rejected\nError details",
        }
    ]


@pytest.mark.parametrize("vision_enabled", [True, False])
def test_mixed_observation_preserves_text_and_supported_images(serialize, vision_enabled):
    image_url = "data:image/png;base64,fixture"
    message = Message(
        role="tool",
        tool_call_id="call_image",
        content=[TextContent(text="Chart"), ImageContent(image_urls=[image_url])],
    )
    items = serialize(message, vision_enabled=vision_enabled)
    assert len(items) == 1
    assert items[0]["call_id"] == "call_image"
    assert items[0]["output"] == (
        [
            {"type": "input_text", "text": "Chart"},
            {"type": "input_image", "image_url": image_url, "detail": "auto"},
        ]
        if vision_enabled else "Chart"
    )


def test_empty_observation_still_completes_the_tool_call(serialize):
    message = Message(role="tool", tool_call_id="call_empty", content=[])
    assert serialize(message, vision_enabled=True) == [
        {"type": "function_call_output", "call_id": "call_empty", "output": ""}
    ]
