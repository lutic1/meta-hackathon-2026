"""The session state machine (AD-4): `apply` is the only writer of session state.

A session is an append-only event log. `SessionStateMachine(room)` holds the
session's Effective room and folds the log into a `SessionState`, so a replay
from an empty state equals live play. `apply(state, event, history=...)`
returns a new state and never mutates its input; time reaches it only as
each event's `t_ms` (AD-10), and this module imports only the standard
library, pydantic and the domain (AD-1).

Only the server opens a lock: a `find` click, a `code` input, an armed
`order` sequence and a `use_on` pair are judged here against the Room's
solutions. A Wrong attempt is counted only on a failed `code` input, a
resolved `use_on` pair that does not match, or a mismatched full-length armed
order buffer, never on a click, and an input to a Puzzle whose `requires` are
not all open opens nothing and counts nothing.

`order_start` is a lock input: it makes its Puzzle the Active puzzle and arms
the buffer, which is armed only while its Puzzle is the Active puzzle. While
armed, every hotspot click fills the buffer whichever object it hits; at
solution length a match opens the lock and disarms, and a mismatch is one
Wrong attempt on the armed Puzzle and clears the buffer, which stays armed.
`order_stop` disarms and clears with no Wrong attempt, and so does any change
of the Active puzzle, in the same step that recomputes it. Clicks while
unarmed are exploration and never fill the buffer.

`use_on` carries no `puzzle_id`: the server resolves the Puzzle from the
`(item, target)` pair among the available `use_on` Puzzles, by `item`, else
by `target`. A pair whose item is not in the inventory is refused, and a pair
resolving to no Puzzle is logged; neither counts.

The Active puzzle is the most recently targeted available unsolved Puzzle,
else the earliest available unsolved one in `Room.puzzles[]` order, and null
once none is available. A target is set only by a lock input or by a
`hint_request` naming an available unsolved Puzzle; a click never sets one.
`SessionState` carries no target of its own, so `active_puzzle_id` stands for
it: a new target replaces it, and otherwise it is kept while it stays
available and unsolved.

The session start fixes two things the log does not hold: the opening line's
kind, which the empty state carries with no text while `phrasing` is true,
and the session's `Thresholds`, which every replayed state reports (AR-31).

Rungs (AD-4): after every event but a `rung_change` or a `hint_request`
(a Hint request never triggers a Rung), `apply` asks
`select_rung` (`domain/rungs.py`) whether a Rung opens on the Active puzzle,
over the session's `Thresholds` (the 1x ones of `Derived.fresh()` when the
machine was given none), and, when one does, records the `rung_change` in the
state with the triggering event's `t_ms` and the verbatim Rung text; the API
then appends it to the log right after that event. Rung selection reads the
log before the event as this machine judged it, so `apply` takes that
`history` as a required argument and `replay` and `result` keep it as they
fold; a selection never lowers a Puzzle's `current_rung`. Replaying the log
selects the same Rung on the same event, and the stored `rung_change` that
follows replaces that selection rather than repeating it, so replay equals
live and no Rung change is ever duplicated. The API words a selected Rung
through the Guide port before it appends it, so the stored `rung_change`
carries the line exactly as shown.

A `hint_request` is answered with `current_rung_text`: the text of the
current Rung of the Puzzle it resolved to, which is the Active puzzle after
it, or nothing while no Rung is open there or no Puzzle is active (the API
then answers the No-hint line).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import replace
from typing import Literal

from .rungs import RUNG_NAMES, Judged, select_rung, unscaled_thresholds
from .schema import (
    ClickEvent,
    CodeInput,
    Derived,
    Event,
    HintRequestEvent,
    LockInput,
    LockInputEvent,
    OpeningLine,
    OpeningLineEvent,
    OrderBuffer,
    OrderSolution,
    OrderStartInput,
    OrderStopInput,
    Puzzle,
    PuzzleId,
    PuzzleResult,
    Room,
    RoomResult,
    RungChangeEvent,
    SessionId,
    SessionState,
    Thresholds,
    TricksterWindow,
    UseOnInput,
    UseOnSolution,
)


def _normalize_code(code: str) -> str:
    """A-20: codes are compared trimmed and case-folded."""
    return code.strip().casefold()


class SessionStateMachine:
    """Folds a session's event log over its Effective room; every method returns new values."""

    def __init__(
        self,
        room: Room,
        *,
        opening: Literal["greeting", "welcome"] | None = None,
        thresholds: Thresholds | None = None,
    ) -> None:
        self.room = room
        self.opening = opening
        self.thresholds = thresholds
        self._rung_thresholds = thresholds or unscaled_thresholds(Derived.fresh())
        self._puzzles = {puzzle.id: puzzle for puzzle in room.puzzles}

    # --- Reads ---------------------------------------------------------------

    def available(self, state: SessionState) -> list[Puzzle]:
        """The available unsolved Puzzles in Room order: closed, with every Puzzle in `requires` open."""
        open_ids = set(state.locks_open)
        return [p for p in self.room.puzzles if p.id not in open_ids and set(p.requires) <= open_ids]

    def current_rung_text(self, state: SessionState) -> str | None:
        """The verbatim text of the Active puzzle's current Rung; None while no Rung is open there or no Puzzle is active."""
        puzzle_id = state.active_puzzle_id
        if puzzle_id is None or state.current_rung[puzzle_id] == 0:
            return None
        return self._rung_text(puzzle_id, state.current_rung[puzzle_id])

    def is_complete(self, state: SessionState) -> bool:
        """Whether the exit lock has opened."""
        return any(puzzle.is_exit and puzzle.id in state.locks_open for puzzle in self.room.puzzles)

    # --- Writes --------------------------------------------------------------

    def initial(self, session_id: SessionId) -> SessionState:
        """The empty state: nothing open, `phrasing` until the opening line lands, the earliest Puzzle active.

        The opening line's kind is known from the start, with no text until its event lands.
        """
        ids = [puzzle.id for puzzle in self.room.puzzles]
        state = SessionState(
            id=session_id,
            room_id=self.room.id,
            locks_open=[],
            inventory=[],
            current_rung=dict.fromkeys(ids, 0),
            wrong_attempts=dict.fromkeys(ids, 0),
            rungs_used=0,
            order_buffer=OrderBuffer(),
            active_puzzle_id=None,
            opening_line=None if self.opening is None else OpeningLine(kind=self.opening, text=None),
            phrasing=True,
            rung_changes=[],
            trickster_window=TricksterWindow(state="closed"),
            trickster_calls=0,
            cards=[],
            room_revision=0,
            disclosure=[],
            thresholds=self.thresholds,
        )
        state.active_puzzle_id = self._active(state, None)
        return state

    def apply(self, state: SessionState, event: Event, *, history: Sequence[Judged]) -> SessionState:
        """The state after `event`: judged locks, counts, the recomputed Active puzzle and any Rung, as a new value.

        `history` is the log before `event` as this machine judged it
        (`history(session_id, log)`), which `select_rung` reads.
        """
        return self._step(state, event, history)[0]

    def history(self, session_id: SessionId, events: Iterable[Event]) -> list[Judged]:
        """The log as this machine judges it: the `history` that `apply` takes for the event after it."""
        return [judged for _, _, _, judged in self._fold(session_id, events)]

    def replay(self, session_id: SessionId, events: Iterable[Event]) -> SessionState:
        """The log folded from the empty state."""
        state = self.initial(session_id)
        for _, _, state, _ in self._fold(session_id, events):
            pass
        return state

    def _fold(self, session_id: SessionId, events: Iterable[Event]) -> Iterator[tuple[Event, SessionState, SessionState, Judged]]:
        """Each event with the state before and after it and its judgment, applied with the history so far."""
        state = self.initial(session_id)
        history: list[Judged] = []
        for event in events:
            after, judged = self._step(state, event, history)
            history.append(judged)
            yield event, state, after, judged
            state = after

    def _step(self, state: SessionState, event: Event, history: Sequence[Judged]) -> tuple[SessionState, Judged]:
        new = state.model_copy(deep=True)
        target: PuzzleId | None = None
        match event:
            case ClickEvent():
                self._click(new, event.interactable_id)
            case LockInputEvent():
                target = self._lock_input(new, event.input)
            case HintRequestEvent():
                target = self._hint_target(new, event.puzzle_id)
            case OpeningLineEvent():
                new.opening_line = OpeningLine(kind=event.kind, text=event.text)
                new.phrasing = False
            case RungChangeEvent():
                self._record_rung(new, event)
        new.active_puzzle_id = self._active(new, target or state.active_puzzle_id)
        if new.order_buffer.puzzle_id is not None and new.order_buffer.puzzle_id != new.active_puzzle_id:
            new.order_buffer = OrderBuffer()
        judged = Judged(
            t_ms=event.t_ms,
            activity=isinstance(event, ClickEvent | LockInputEvent | HintRequestEvent),
            wrong_attempt=next((p for p, n in new.wrong_attempts.items() if n > state.wrong_attempts[p]), None),
            rung=(event.puzzle_id, event.rung) if isinstance(event, RungChangeEvent) else None,
            active_puzzle_id=new.active_puzzle_id,
        )
        if not isinstance(event, RungChangeEvent | HintRequestEvent):
            step = select_rung([*history, judged], self._rung_thresholds)
            if step is not None and step.rung > new.current_rung[step.puzzle_id]:
                self._record_rung(new, RungChangeEvent(
                    type="rung_change",
                    puzzle_id=step.puzzle_id,
                    rung=step.rung,
                    triggered_by=list(step.triggered_by),
                    phrased=False,
                    phrasing_ms=None,
                    text=self._rung_text(step.puzzle_id, step.rung),
                    t_ms=event.t_ms,
                ))
                judged = replace(judged, rung=(step.puzzle_id, step.rung))
        new.rungs_used = sum(new.current_rung.values())
        return new, judged

    # --- Judging -------------------------------------------------------------

    def _available_puzzle(self, state: SessionState, puzzle_id: str) -> Puzzle | None:
        """The named Puzzle when it is in the Room, closed and available, else None."""
        puzzle = self._puzzles.get(puzzle_id)
        if puzzle is None or puzzle.id in state.locks_open or not set(puzzle.requires) <= set(state.locks_open):
            return None
        return puzzle

    def _rung_text(self, puzzle_id: PuzzleId, rung: int) -> str:
        return getattr(self._puzzles[puzzle_id].rungs, RUNG_NAMES[rung - 1])

    @staticmethod
    def _record_rung(state: SessionState, event: RungChangeEvent) -> None:
        """Open the Rung; a stored `rung_change` right after the event that selected it replaces that selection."""
        last = state.rung_changes[-1] if state.rung_changes else None
        if last is not None and (last.puzzle_id, last.rung) == (event.puzzle_id, event.rung):
            state.rung_changes[-1] = event
        else:
            state.rung_changes.append(event)
        state.current_rung[event.puzzle_id] = event.rung

    def _open(self, state: SessionState, puzzle: Puzzle) -> None:
        state.locks_open.append(puzzle.id)
        solution = puzzle.solution
        if solution.lock_type == "find" and solution.target not in state.inventory:
            state.inventory.append(solution.target)

    def _click(self, state: SessionState, interactable_id: str) -> None:
        """A click opens an available `find` Puzzle whose target it hits and fills the armed order buffer.

        Any other click is exploration. At solution length the armed buffer
        opens its lock and disarms, or counts one Wrong attempt and clears.
        """
        for puzzle in self.available(state):
            solution = puzzle.solution
            if solution.lock_type == "find" and solution.target == interactable_id:
                self._open(state, puzzle)
        armed = self._armed(state)
        if armed is None:
            return
        puzzle, solution = armed
        buffer = state.order_buffer
        buffer.clicks.append(interactable_id)
        if len(buffer.clicks) < len(solution.interactables):
            return
        if buffer.clicks == solution.interactables:
            self._open(state, puzzle)
            state.order_buffer = OrderBuffer()
        else:
            state.wrong_attempts[puzzle.id] += 1
            buffer.clicks = []

    def _armed(self, state: SessionState) -> tuple[Puzzle, OrderSolution] | None:
        """The armed `order` Puzzle and its solution while it is still available, else None."""
        puzzle_id = state.order_buffer.puzzle_id
        puzzle = None if puzzle_id is None else self._available_puzzle(state, puzzle_id)
        if puzzle is None or not isinstance(puzzle.solution, OrderSolution):
            return None
        return puzzle, puzzle.solution

    def _resolve_use_on(self, state: SessionState, lock_input: UseOnInput) -> tuple[Puzzle, UseOnSolution] | None:
        """The available `use_on` Puzzle the pair names, by `item`, else by `target`; None when neither matches."""
        candidates = [(p, p.solution) for p in self.available(state) if isinstance(p.solution, UseOnSolution)]
        for puzzle, solution in candidates:
            if solution.item == lock_input.item:
                return puzzle, solution
        for puzzle, solution in candidates:
            if solution.target == lock_input.target:
                return puzzle, solution
        return None

    def _lock_input(self, state: SessionState, lock_input: LockInput) -> PuzzleId | None:
        """Judge a lock input; returns the Puzzle it targeted, or None when it named no available one."""
        match lock_input:
            case CodeInput():
                puzzle = self._available_puzzle(state, lock_input.puzzle_id)
                if puzzle is None or puzzle.solution.lock_type != "code":
                    return None
                if _normalize_code(lock_input.code) == _normalize_code(puzzle.solution.code):
                    self._open(state, puzzle)
                else:
                    state.wrong_attempts[puzzle.id] += 1
                return puzzle.id
            case OrderStartInput():
                puzzle = self._available_puzzle(state, lock_input.puzzle_id)
                if puzzle is None or puzzle.lock_type != "order":
                    return None
                state.order_buffer = OrderBuffer(puzzle_id=puzzle.id)
                return puzzle.id
            case OrderStopInput():
                puzzle = self._available_puzzle(state, lock_input.puzzle_id)
                if puzzle is None or puzzle.lock_type != "order":
                    return None
                state.order_buffer = OrderBuffer()
                return puzzle.id
            case UseOnInput():
                if lock_input.item not in state.inventory:
                    return None  # refused: the player does not carry the item
                resolved = self._resolve_use_on(state, lock_input)
                if resolved is None:
                    return None  # logged, counts nothing
                puzzle, solution = resolved
                if (solution.item, solution.target) == (lock_input.item, lock_input.target):
                    self._open(state, puzzle)
                else:
                    state.wrong_attempts[puzzle.id] += 1
                return puzzle.id

    def _hint_target(self, state: SessionState, puzzle_id: str | None) -> PuzzleId | None:
        """A `hint_request` targets the Puzzle it names only when that Puzzle is available and unsolved."""
        if puzzle_id is None:
            return None
        puzzle = self._available_puzzle(state, puzzle_id)
        return None if puzzle is None else puzzle.id

    def _active(self, state: SessionState, candidate: PuzzleId | None) -> PuzzleId | None:
        """`candidate` while it is available and unsolved, else the earliest available unsolved Puzzle, else None."""
        available = self.available(state)
        if any(puzzle.id == candidate for puzzle in available):
            return candidate
        return available[0].id if available else None

    # --- The Room result (AD-8) ------------------------------------------------

    def result(self, session_id: SessionId, events: Iterable[Event], *, demo: bool = False) -> RoomResult:
        """The `RoomResult` computed from the log alone.

        `elapsed_ms` is the `t_ms` of the event that opened the exit (the last
        event's before then). A Puzzle's time is counted from the event that
        made it available (session start for one with no `requires`) to the one
        that opened it, or to the end of the log while unsolved; its time to
        first hint is counted from the same start to the first `hint_request`
        resolved to it, and an Early ask is such a request made with no Rung
        open on it.
        """
        state = self.initial(session_id)
        available_at = {puzzle.id: 0 for puzzle in self.available(state)}
        opened_at: dict[str, int] = {}
        first_hint: dict[str, int] = {}
        early_asks: set[str] = set()
        t_end = 0
        for event, before, state, _ in self._fold(session_id, events):
            t_end = event.t_ms
            # After a hint request, `active_puzzle_id` is the Puzzle the request was resolved to.
            if isinstance(event, HintRequestEvent) and (hinted := state.active_puzzle_id) is not None:
                first_hint.setdefault(hinted, event.t_ms)
                if before.current_rung[hinted] == 0:
                    early_asks.add(hinted)
            for puzzle_id in state.locks_open[len(before.locks_open):]:
                opened_at[puzzle_id] = event.t_ms
            for puzzle in self.available(state):
                available_at.setdefault(puzzle.id, event.t_ms)
        exit_ids = [puzzle.id for puzzle in self.room.puzzles if puzzle.is_exit]
        elapsed = opened_at.get(exit_ids[0], t_end) if exit_ids else t_end
        puzzles = []
        for puzzle in self.room.puzzles:
            solved = puzzle.id in opened_at
            started = available_at.get(puzzle.id)
            hinted_at = first_hint.get(puzzle.id)
            wrong = state.wrong_attempts[puzzle.id]
            puzzles.append(
                PuzzleResult(
                    puzzle_id=puzzle.id,
                    lock_type=puzzle.lock_type,
                    attempts=wrong + int(solved),
                    wrong_attempts=wrong,
                    rungs_used=state.current_rung[puzzle.id],
                    time_to_first_hint=None if hinted_at is None or started is None else hinted_at - started,
                    solved=solved,
                    time_spent_ms=0 if started is None else (opened_at[puzzle.id] if solved else t_end) - started,
                    nudge_fired=state.current_rung[puzzle.id] >= 1,
                    hint_requested=hinted_at is not None,
                    early_ask=puzzle.id in early_asks,
                )
            )
        return RoomResult(
            room_id=self.room.id,
            demo=demo,
            elapsed_ms=elapsed,
            rungs_used=state.rungs_used,
            wrong_attempts=sum(state.wrong_attempts.values()),
            puzzles=puzzles,
        )
