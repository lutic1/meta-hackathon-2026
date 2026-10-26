"""The session state machine (AD-4): `apply` is the only writer of session state.

A session is an append-only event log. `SessionStateMachine(room)` holds the
session's Effective room and folds the log into a `SessionState`, so a replay
from an empty state equals live play. `apply(state, event)` returns a new
state and never mutates its input; time reaches it only as each event's
`t_ms` (AD-10), and this module imports only the standard library, pydantic
and the domain (AD-1).

Only the server opens a lock: a `find` click and a `code` input are judged
here against the Room's solutions. A Wrong attempt is counted only on a
failed input to an available Puzzle, never on a click, and an input to a
Puzzle whose `requires` are not all open opens nothing and counts nothing.
Order sequences and `use_on` pairs are judged by their own story; here
`order_start` arms the buffer, `order_stop` disarms it, and any change of
the Active puzzle disarms it with no Wrong attempt.

The Active puzzle is the most recently targeted available unsolved Puzzle,
else the earliest available unsolved one in `Room.puzzles[]` order, and null
once none is available. A target is set only by a lock input or by a
`hint_request` naming an available unsolved Puzzle; a click never sets one.
`SessionState` carries no target of its own, so `active_puzzle_id` stands for
it: a new target replaces it, and otherwise it is kept while it stays
available and unsolved.
"""

from __future__ import annotations

from collections.abc import Iterable

from .schema import (
    ClickEvent,
    CodeInput,
    Event,
    HintRequestEvent,
    LockInput,
    LockInputEvent,
    OpeningLine,
    OpeningLineEvent,
    OrderBuffer,
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
    TricksterWindow,
)


def _normalize_code(code: str) -> str:
    """A-20: codes are compared trimmed and case-folded."""
    return code.strip().casefold()


class SessionStateMachine:
    """Folds a session's event log over its Effective room; every method returns new values."""

    def __init__(self, room: Room) -> None:
        self.room = room
        self._puzzles = {puzzle.id: puzzle for puzzle in room.puzzles}

    # --- Reads ---------------------------------------------------------------

    def available(self, state: SessionState) -> list[Puzzle]:
        """The available unsolved Puzzles in Room order: closed, with every Puzzle in `requires` open."""
        open_ids = set(state.locks_open)
        return [p for p in self.room.puzzles if p.id not in open_ids and set(p.requires) <= open_ids]

    def is_complete(self, state: SessionState) -> bool:
        """Whether the exit lock has opened."""
        return any(puzzle.is_exit and puzzle.id in state.locks_open for puzzle in self.room.puzzles)

    # --- Writes --------------------------------------------------------------

    def initial(self, session_id: SessionId) -> SessionState:
        """The empty state: nothing open, `phrasing` until the opening line lands, the earliest Puzzle active."""
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
            opening_line=None,
            phrasing=True,
            rung_changes=[],
            trickster_window=TricksterWindow(state="closed"),
            trickster_calls=0,
            cards=[],
            room_revision=0,
            disclosure=[],
        )
        state.active_puzzle_id = self._active(state, None)
        return state

    def apply(self, state: SessionState, event: Event) -> SessionState:
        """The state after `event`: judged locks, counts and the recomputed Active puzzle, as a new value."""
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
                new.current_rung[event.puzzle_id] = event.rung
                new.rung_changes.append(event)
        new.rungs_used = sum(new.current_rung.values())
        new.active_puzzle_id = self._active(new, target or state.active_puzzle_id)
        if new.order_buffer.puzzle_id is not None and new.order_buffer.puzzle_id != new.active_puzzle_id:
            new.order_buffer = OrderBuffer()
        return new

    def replay(self, session_id: SessionId, events: Iterable[Event]) -> SessionState:
        """The log folded from the empty state."""
        state = self.initial(session_id)
        for event in events:
            state = self.apply(state, event)
        return state

    # --- Judging -------------------------------------------------------------

    def _available_puzzle(self, state: SessionState, puzzle_id: str) -> Puzzle | None:
        """The named Puzzle when it is in the Room, closed and available, else None."""
        puzzle = self._puzzles.get(puzzle_id)
        if puzzle is None or puzzle.id in state.locks_open or not set(puzzle.requires) <= set(state.locks_open):
            return None
        return puzzle

    def _open(self, state: SessionState, puzzle: Puzzle) -> None:
        state.locks_open.append(puzzle.id)
        solution = puzzle.solution
        if solution.lock_type == "find" and solution.target not in state.inventory:
            state.inventory.append(solution.target)

    def _click(self, state: SessionState, interactable_id: str) -> None:
        """A click opens an available `find` Puzzle whose target it hits; any other click is exploration."""
        for puzzle in self.available(state):
            solution = puzzle.solution
            if solution.lock_type == "find" and solution.target == interactable_id:
                self._open(state, puzzle)

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
            case _:
                return None  # `use_on` is resolved from its pair by its own story

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
        for event in events:
            before, state = state, self.apply(state, event)
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
