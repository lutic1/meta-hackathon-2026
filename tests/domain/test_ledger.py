"""Story 2.2: spend arithmetic as pure domain functions (AD-6)."""

import inspect

import pytest
from pydantic import ValidationError

from src.domain import ledger
from src.domain.ledger import (
    SEED_USD,
    LedgerEntry,
    estimate_usd,
    fold,
    image_cost_usd,
    running_total_usd,
    sam_cost_usd,
    settle,
    spark_cost_usd,
    would_exceed,
)

CALL_A = "call_01ARZ3NDEKTSV4RRFFQ69G5FAA"
CALL_B = "call_01ARZ3NDEKTSV4RRFFQ69G5FAB"
CALL_C = "call_01ARZ3NDEKTSV4RRFFQ69G5FAC"
JOB = "job_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def entry(call_id: str, kind: str, status: str, usd: float, **extra) -> LedgerEntry:
    return LedgerEntry(call_id=call_id, kind=kind, status=status, usd=usd, **extra)


# --- Pricing ---------------------------------------------------------------


def test_spark_usage_is_priced_at_the_standard_tier_rates():
    usage = {"prompt_tokens": 3000, "completion_tokens": 900, "total_tokens": 3900,
             "prompt_tokens_details": {"cached_tokens": 1000},
             "completion_tokens_details": {"reasoning_tokens": 600}}
    # 2000 fresh * 1.25 + 1000 cached * 0.15 + 900 output * 4.25, per million
    assert spark_cost_usd(usage) == pytest.approx(0.006475, abs=1e-12)


def test_spark_reasoning_tokens_bill_as_output_and_details_may_be_absent():
    without = {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}
    with_reasoning = {**without, "completion_tokens_details": {"reasoning_tokens": 999_999}}
    assert spark_cost_usd(without) == pytest.approx(1.25 + 4.25)
    assert spark_cost_usd(with_reasoning) == spark_cost_usd(without)


def test_spark_cached_input_bills_at_the_cached_rate():
    usage = {"prompt_tokens": 1_000_000, "completion_tokens": 0,
             "prompt_tokens_details": {"cached_tokens": 1_000_000}}
    assert spark_cost_usd(usage) == pytest.approx(0.15)


def test_sam_and_image_calls_are_priced_per_image():
    assert sam_cost_usd(1) == pytest.approx(0.0025)
    assert sam_cost_usd(1000) == pytest.approx(2.50)
    assert image_cost_usd(1) == pytest.approx(0.01)
    assert image_cost_usd(4) == pytest.approx(0.04)
    assert sam_cost_usd(0) == 0 and image_cost_usd(0) == 0


# --- Estimates -------------------------------------------------------------


def test_estimate_is_the_seed_before_any_observation():
    assert SEED_USD == {"vision": 0.03, "sam": 0.0025, "riddler": 0.03, "dryrun": 0.03,
                        "trickster": 0.01, "image": 0.01, "reconstruct3d": 0.02}
    for kind, seed in SEED_USD.items():
        assert estimate_usd(kind, []) == seed
    assert estimate_usd("vision", [entry(CALL_A, "riddler", "settled", 0.5)]) == 0.03


def test_estimate_is_the_last_observed_cost_of_that_kind():
    entries = [
        entry(CALL_A, "riddler", "settled", 0.021),
        entry(CALL_B, "vision", "settled", 0.4),
        entry(CALL_C, "riddler", "settled", 0.027),
    ]
    assert estimate_usd("riddler", entries) == 0.027
    assert estimate_usd("vision", entries) == 0.4
    assert estimate_usd("sam", entries) == 0.0025


def test_estimate_ignores_reserved_entries_of_that_kind():
    entries = [entry(CALL_A, "riddler", "reserved", 0.03), entry(CALL_B, "riddler", "reserved", 0.03)]
    assert estimate_usd("riddler", entries) == 0.03
    entries.append(entry(CALL_A, "riddler", "settled", 0.05))
    assert estimate_usd("riddler", entries) == 0.05


def test_a_zero_cost_settlement_never_seeds_the_estimate():
    """Decision 24: a call settled at 0 USD because it was never sent is no observed price, so it cannot zero the next reservation."""
    never_sent = [entry(CALL_B, "riddler", "reserved", 0.03), entry(CALL_B, "riddler", "settled", 0.0)]
    assert estimate_usd("riddler", never_sent) == SEED_USD["riddler"]
    assert estimate_usd("riddler", [entry(CALL_A, "riddler", "settled", 0.05), *never_sent]) == 0.05


# --- Folding, totals and the cap check -------------------------------------


def test_running_total_counts_each_call_once_with_settled_replacing_reserved():
    entries = [
        entry(CALL_A, "vision", "reserved", 0.03),
        entry(CALL_B, "riddler", "reserved", 0.03),
        entry(CALL_A, "vision", "settled", 0.025),
    ]
    assert running_total_usd(entries) == pytest.approx(0.055)
    assert running_total_usd([]) == 0


def test_folding_a_retried_then_settled_call_keeps_one_entry():
    reserved = entry(CALL_A, "riddler", "reserved", 0.03, job_id=JOB, stage="author")
    settled = settle(reserved, 0.022)
    folded = fold([reserved, settled])
    assert folded == [settled]
    assert settled.call_id == CALL_A and settled.status == "settled" and settled.usd == 0.022
    assert settled.job_id == JOB and settled.stage == "author"


def test_fold_keeps_first_seen_order_and_a_settled_entry_is_never_replaced_by_a_reserved_one():
    a_settled = entry(CALL_A, "sam", "settled", 0.0025)
    folded = fold([a_settled, entry(CALL_B, "image", "reserved", 0.01), entry(CALL_A, "sam", "reserved", 0.03)])
    assert [e.call_id for e in folded] == [CALL_A, CALL_B]
    assert folded[0] == a_settled


def test_would_exceed_exactly_when_spend_plus_estimate_passes_the_cap():
    entries = [entry(CALL_A, "vision", "settled", 0.5), entry(CALL_B, "riddler", "reserved", 0.3)]
    assert would_exceed(entries, 0.2, cap=1.0) is False  # lands exactly on the cap
    assert would_exceed(entries, 0.21, cap=1.0) is True
    assert would_exceed([], 0.03, cap=0.0) is True
    assert would_exceed([], 0.0, cap=0.0) is False


def test_a_store_at_its_allocation_refuses_while_another_below_its_own_accepts():
    local = [entry(CALL_A, "vision", "settled", 60.0)]
    hosted = [entry(CALL_B, "vision", "settled", 19.0)]
    assert would_exceed(local, estimate_usd("sam", local), cap=60) is True
    assert would_exceed(hosted, estimate_usd("sam", hosted), cap=20) is False


# --- Purity ----------------------------------------------------------------


def test_every_function_returns_new_values_and_leaves_its_inputs_unchanged():
    reserved = entry(CALL_A, "riddler", "reserved", 0.03)
    entries = [reserved, entry(CALL_B, "vision", "reserved", 0.03)]
    before = [e.model_dump() for e in entries]
    settled = settle(reserved, 0.022)
    fold(entries)
    estimate_usd("riddler", entries)
    running_total_usd(entries)
    would_exceed(entries, 0.03, cap=60)
    assert settled is not reserved and reserved.status == "reserved" and reserved.usd == 0.03
    assert [e.model_dump() for e in entries] == before
    with pytest.raises(ValidationError):
        reserved.usd = 1.0  # type: ignore[misc]


def test_entries_are_validated():
    with pytest.raises(ValueError):
        entry("call_bad", "vision", "reserved", 0.03)
    with pytest.raises(ValueError):
        entry(CALL_A, "guide", "reserved", 0.03)
    with pytest.raises(ValueError):
        entry(CALL_A, "vision", "reserved", -0.01)
    with pytest.raises(ValueError):
        settle(entry(CALL_A, "vision", "reserved", 0.03), -1.0)


def test_cap_is_a_function_argument_and_the_module_holds_no_clock():
    assert "cap" in inspect.signature(would_exceed).parameters
    source = inspect.getsource(ledger)
    assert "datetime" not in source and "import time" not in source and "clock" not in source
