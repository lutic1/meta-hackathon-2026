"""Story 2.1: the `ModelProvider` port declares exactly the Tier 1 signatures (AD-5)."""

import inspect

import pytest

from src.domain.schema import Polygon
from src.providers import base
from src.providers.base import (
    REASONING_EFFORTS,
    ChatResponse,
    ImageResponse,
    ModelProvider,
    check_reasoning_effort,
)

KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY


def _params(method):
    signature = inspect.signature(method, eval_str=True)
    return list(signature.parameters.values())[1:], signature.return_annotation


def test_chat_signature():
    params, returns = _params(ModelProvider.chat)
    assert [p.name for p in params] == ["messages", "images", "response_schema", "reasoning_effort", "model"]
    assert params[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert all(p.kind is KEYWORD_ONLY for p in params[1:])
    assert [p.default for p in params[1:]] == [[], None, "low", None]
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
    assert not hasattr(base, "HintPhraser")


@pytest.mark.parametrize("effort", REASONING_EFFORTS)
def test_every_allowed_effort_passes(effort):
    assert effort in ("minimal", "low", "medium", "high", "xhigh")
    check_reasoning_effort(effort)


def test_none_is_refused_like_the_api():
    with pytest.raises(ValueError, match="reasoning_effort 'none' is not one of minimal, low, medium, high, xhigh"):
        check_reasoning_effort("none")
