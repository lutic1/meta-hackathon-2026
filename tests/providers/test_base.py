"""Stories 2.1 and 3.2: `ModelProvider` declares exactly the Tier 1 signatures and `HintPhraser` is its own port (AD-5)."""

import inspect

import pytest

from src.domain.schema import Derived, GuideModel, Polygon
from src.providers import base
from src.providers.base import (
    REASONING_EFFORTS,
    ChatResponse,
    HintPhraser,
    ImageResponse,
    ModelProvider,
    PhraserResponse,
    check_reasoning_effort,
)

KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY


def _params(method):
    signature = inspect.signature(method, eval_str=True)
    return list(signature.parameters.values())[1:], signature.return_annotation


def test_chat_signature():
    """AD-5's `chat`, plus the AD-6 `attempt` the regeneration loop passes into the cache key (Story 2.20)."""
    params, returns = _params(ModelProvider.chat)
    assert [p.name for p in params] == ["messages", "images", "response_schema", "reasoning_effort", "model", "attempt"]
    assert params[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert all(p.kind is KEYWORD_ONLY for p in params[1:])
    assert [p.default for p in params[1:]] == [[], None, "low", None, 0]
    assert returns is ChatResponse


def test_chat_dropped_the_scaffold_arguments():
    names = inspect.signature(ModelProvider.chat).parameters
    assert "max_tokens" not in names and "temperature" not in names


def test_segment_signature():
    params, returns = _params(ModelProvider.segment)
    assert [(p.name, p.annotation) for p in params] == [("label", str), ("image", bytes)]
    assert returns == list[Polygon] | None


def test_generate_image_signature():
    params, returns = _params(ModelProvider.generate_image)
    assert [(p.name, p.annotation) for p in params] == [("prompt", str)]
    assert returns is ImageResponse


def test_exactly_the_tier_1_methods_are_abstract():
    assert ModelProvider.__abstractmethods__ == {"chat", "segment", "generate_image"}


def test_later_ports_are_not_declared_yet():
    assert not hasattr(ModelProvider, "reconstruct3d")
    assert not hasattr(ModelProvider, "transcribe")
    assert not hasattr(base, "transcribe")


def test_hint_phraser_is_a_separate_port():
    assert not issubclass(HintPhraser, ModelProvider) and not issubclass(ModelProvider, HintPhraser)
    assert HintPhraser.__abstractmethods__ == {"phrase", "greet"}
    assert not hasattr(ModelProvider, "phrase") and not hasattr(ModelProvider, "greet")
    assert not hasattr(HintPhraser, "chat")


def test_phrase_signature_is_exactly_rung_text_and_derived():
    params, returns = _params(HintPhraser.phrase)
    assert [(p.name, p.annotation) for p in params] == [("rung_text", str), ("derived", Derived)]
    assert all(p.default is inspect.Parameter.empty for p in params)
    assert returns is PhraserResponse


def test_greet_signature_is_exactly_derived():
    params, returns = _params(HintPhraser.greet)
    assert [(p.name, p.annotation) for p in params] == [("derived", Derived)]
    assert returns is PhraserResponse


def test_phraser_response_carries_the_text_the_flag_and_the_latency():
    assert list(PhraserResponse.__dataclass_fields__) == ["text", "phrased", "latency_ms"]
    assert inspect.get_annotations(HintPhraser, eval_str=True)["guide_model"] == GuideModel | None
    assert HintPhraser.guide_model is None


@pytest.mark.parametrize("effort", REASONING_EFFORTS)
def test_every_allowed_effort_passes(effort):
    assert effort in ("minimal", "low", "medium", "high", "xhigh")
    check_reasoning_effort(effort)


def test_none_is_refused_like_the_api():
    with pytest.raises(ValueError, match="reasoning_effort 'none' is not one of minimal, low, medium, high, xhigh"):
        check_reasoning_effort("none")
