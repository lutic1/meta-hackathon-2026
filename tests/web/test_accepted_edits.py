"""FR-19, FR-11, UX-DR27, UX-DR39, UX-DR65: an accepted Trickster edit reshapes the room in play.

A changed `room_revision` refetches the session's Effective room and redraws the Riddle note, the chest's numbers and
the Hotspots in place (story mode: one riddle at a time; a Merge or a Shortcut moves `active_puzzle_id`, which the note
follows; under the chest a Decoy and a Loosen are refused by the Validator, tests/api/test_chest_hints.py). The client has no
test runner, so the checks read the TypeScript and the stylesheets (`npm run build` and `tsc --noEmit` prove they
compile; the criteria are checked in Chrome against the fixture rooms), and the API checks read what the client reads.
"""

import re
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.domain.schema import Room
from tests.api.test_sessions import Ticker, click, code, start
from tests.api.test_trickster_route import (
    app_client,
    open_window,
    proposals_dir,
    state_of,
    trickster,
)
from tests.fixtures.rooms import IX, PZ
from tests.web.design import WEB_SRC, source_ts
from tests.web.test_types import _interfaces, _keys


def _ts(name: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _nested(text: str, start: str) -> str:
    """The body of a function nested one level, from `start` to its closing brace."""
    return text.split(start, 1)[1].split("\n  }\n", 1)[0]


def _proposal(kind: str, target: str, **payload: str) -> dict[str, Any]:
    """A proposal on the Puzzle named `target`, its payload as given (ids already resolved)."""
    return {"type": kind, "puzzle": PZ[target], "payload": {"type": kind, **payload}}


def _decoy(puzzle: str) -> dict[str, Any]:
    return _proposal("decoy", puzzle, interactable=IX["rug"], visible_attribute="faded red")


def _merge(waiting: str, on: str) -> dict[str, Any]:
    return _proposal("merge", waiting, puzzle_a=PZ[on], puzzle_b=PZ[waiting])


def _client(tmp_path: Path, room: Room, *proposals: dict[str, Any]) -> tuple[TestClient, Ticker]:
    ticker = Ticker()
    recording = {"room_id": room.id, "proposals": list(proposals)}
    return app_client(tmp_path, ticker, room, proposals_dir=proposals_dir(tmp_path, recording)), ticker


def _room(client: TestClient, session_id: str) -> dict[str, dict[str, Any]]:
    view = client.get(f"/api/sessions/{session_id}/room").json()
    return {puzzle["id"]: puzzle for puzzle in view["puzzles"]}


# --- The refetch ---------------------------------------------------------------------------------------------------


def test_the_play_screen_draws_from_the_effective_room_and_records_the_revision_it_mounted_with():
    play, api = _ts("play.ts"), _ts("api/index.ts")
    assert "return getJson<PlayView>(`/sessions/${encodeURIComponent(sessionId)}/room`)" in api
    # The Play screen and the screen under the Completion sheet both read the Effective room, never GET /rooms/<id>;
    # under the sheet it is the one the way out showed, when the Exit opened on the Play screen in this page load.
    assert "const room: Promise<PlayView> = getEffectiveRoom(session.id)" in play and "getRoom" not in play
    assert "kept === undefined ? getEffectiveRoom(session.id) : Promise.resolve(kept.view)" in play
    assert "let fetchedRevision = session.room_revision" in play


def test_a_changed_room_revision_refetches_the_room_once_and_redraws_the_note_and_the_hotspots():
    play = _ts("play.ts")
    refetch = play.split("const refetchRoom = async (state: SessionState): Promise<void> => {", 1)[1].split("\n      }\n", 1)[0]
    # A rejected or skipped Card leaves room_revision as it was, so nothing is fetched; one request at a time.
    assert "if (refetching || state.room_revision === fetchedRevision) return" in refetch
    assert "const next = await getEffectiveRoom(session.id)" in refetch
    assert "fetchedRevision = state.room_revision" in refetch
    assert refetch.index("scene.reshape(next)") < refetch.index("note.reshape(next)") < refetch.index("chest.reshape(next)")
    assert "void refetchRoom(latest)" in refetch  # a revision that arrived meanwhile is fetched next
    assert "parts.push((state) => void refetchRoom(state))" in play
    # No page reload, and the pack, the chest and the Scene are never rebuilt for it.
    assert "location.reload" not in play and play.count("inventory(view, play.useOn, speak)") == 1
    assert play.count("mountScene(") == 2 and "announce(" not in refetch


def test_the_scene_keeps_its_photo_and_lays_changed_hotspots_again_with_focus_on_the_same_one():
    scene = _ts("scene/index.ts")
    reshape = _nested(scene, "function reshape(next: PlayView): void {")
    assert "room = next" in reshape
    assert "if (before === undefined || size === undefined || view.hidden || layer === undefined) return" in reshape
    # The shown photo's Hotspots are laid again only when its Interactables changed, so focus stays put otherwise.
    assert "if (on(before) === on(next)) return" in reshape
    assert "const focused = stack.contains(document.activeElement) ? document.activeElement?.id : undefined" in reshape
    assert "layHotspots(next, size, current)" in reshape and "laySigns(next, size, current)" in reshape
    assert "layer.elements[0].querySelector<SVGElement>(`[id=\"${focused}\"]`)?.focus()" in reshape
    # The photo, the walk and the selection stay: nothing walks, nothing is posed again (story mode).
    assert "show(" not in reshape and "walk(" not in reshape and "pose(" not in reshape and "useOn" not in reshape
    assert "reshape,\n    lastTarget: () => lastTarget," in scene


def test_rehung_hotspots_stay_focusable_buttons_that_show_all_objects_still_outlines():
    layer, play = _ts("scene/hotspots.ts"), _ts("play.ts")
    assert "hotspot.setAttribute('tabindex', '0')" in layer and "hotspot.setAttribute('role', 'button')" in layer
    assert "if (event.key === 'Enter') handlers.onActivate(interactable)" in layer
    # "Show all objects" marks the Scene column, which outlives every Hotspot laid inside it.
    assert "onToggle: (on) => sceneColumn.classList.toggle('is-showing-all', on)" in play


# --- The Riddle note -----------------------------------------------------------------------------------------------


def test_the_note_redraws_from_the_refetched_room_keeping_nothing_stale():
    note = _ts("components/riddle-note.ts")
    reshape = note.split("reshape: (view) => {", 1)[1].split("\n    },", 1)[0]
    assert "room = view" in reshape and "inputs.clear()" in reshape and "draw(latest)" in reshape
    # The riddle shown follows `active_puzzle_id`, which a Merge or a Shortcut moves on the server (AD-4).
    assert "const id = held ? shown : (state.active_puzzle_id ?? shown)" in note
    assert "announce" not in note  # nothing the reshape draws reaches the live region


def test_a_decoy_card_is_never_drawn_in_play_and_nothing_in_the_client_tells_it_apart():
    card = _ts("components/evidence-card.ts")
    # The note and the whole card are the only two drawings, chosen by `solved` alone (the landing's sample page).
    assert "element.className = 'evidence-card'" in card and card.count("className =") == 5
    assert "if (!solved) {" in card
    assert set(_keys(_interfaces()["Evidence"])) == {"interactable", "visible_attribute"}
    for path in ("components/evidence-card.ts", "components/riddle-note.ts", "scene/index.ts", "play.ts"):
        assert "decoy" not in _ts(path).lower(), path
    assert not any(re.search(r"\b(?:interface|type) (?:PlayView|PlayPuzzle|Evidence)\b", text) for text in source_ts().values())
    assert "evidence" not in _ts("components/riddle-note.ts")


# --- What the client reads from the API ----------------------------------------------------------------------------


def test_an_accepted_decoy_raises_the_revision_and_a_rejected_or_skipped_card_does_not(
    tmp_path: Path, four_lock_room: Room
):
    client, ticker = _client(tmp_path, four_lock_room, _decoy("clock_code"), _merge("clock_code", "shelf_order"))
    session_id = start(client, four_lock_room)
    before = _room(client, session_id)
    open_window(client, ticker, session_id, click("key"), 0)
    assert state_of(client, session_id)["room_revision"] == 0
    trickster(client, session_id)
    assert state_of(client, session_id)["room_revision"] == 1
    after = _room(client, session_id)
    # Story mode: the Decoy stays in the Effective room but no evidence is served before its lock opens.
    assert after[PZ["clock_code"]]["evidence_cards"] == before[PZ["clock_code"]]["evidence_cards"] == []
    # A Merge that would deadlock is rejected: the revision, and so the client's room, stay as they were.
    open_window(client, ticker, session_id, code("clock_code", "415"), 1)
    trickster(client, session_id)
    state = state_of(client, session_id)
    assert [card["accepted"] for card in state["cards"]] == [True, False] and state["room_revision"] == 1
    graph = {pid: puzzle["requires"] for pid, puzzle in _room(client, session_id).items()}
    assert graph == {pid: puzzle["requires"] for pid, puzzle in after.items()}


def test_an_accepted_merge_gates_the_visible_entry_the_card_names(tmp_path: Path, four_lock_room: Room):
    client, ticker = _client(tmp_path, four_lock_room, _merge("key_on_chest", "clock_code"))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)  # Puzzle 4 (the chest) is available
    trickster(client, session_id)
    state = state_of(client, session_id)
    (card,) = state["cards"]
    assert card["accepted"] and card["edit_type"] == "merge" and state["room_revision"] == 1
    room = _room(client, session_id)
    gated = room[card["puzzle_id"]]
    # The Card's Puzzle is the one that now waits on an unopened Puzzle, so its label and the placeholder agree.
    assert card["puzzle_id"] == PZ["key_on_chest"] and card["related_puzzle_id"] in gated["requires"]
    assert not all(required in state["locks_open"] for required in gated["requires"])
    assert state["active_puzzle_id"] != PZ["key_on_chest"]


def test_an_accepted_shortcut_frees_a_puzzle_with_no_other_unmet_prerequisite(tmp_path: Path, four_lock_room: Room):
    shortcut = _proposal("shortcut", "key_on_chest", puzzle=PZ["key_on_chest"], requires=PZ["shelf_order"])
    client, ticker = _client(tmp_path, four_lock_room, _merge("key_on_chest", "shelf_order"), shortcut)
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, code("clock_code", "415"), 0)
    trickster(client, session_id)  # the chest now waits on the shelf as well as the key
    open_window(client, ticker, session_id, click("key"), 1)
    assert _room(client, session_id)[PZ["key_on_chest"]]["requires"] == [PZ["find_key"], PZ["shelf_order"]]
    trickster(client, session_id)
    state = state_of(client, session_id)
    assert [card["accepted"] for card in state["cards"]] == [True, True] and state["room_revision"] == 2
    freed = _room(client, session_id)[PZ["key_on_chest"]]
    assert all(required in state["locks_open"] for required in freed["requires"])


def test_an_accepted_loosen_opens_its_rung_with_a_rung_change_the_card_triggered(tmp_path: Path, four_lock_room: Room):
    loosen = _proposal("loosen", "clock_code", puzzle=PZ["clock_code"], rung="nudge")
    client, ticker = _client(tmp_path, four_lock_room, loosen)
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    trickster(client, session_id)
    state = state_of(client, session_id)
    (change,) = state["rung_changes"]
    assert change["puzzle_id"] == PZ["clock_code"] and change["rung"] == 1
    (position,) = change["triggered_by"]
    assert state["trigger_events"][str(position)]["type"] == "trickster_card" and state["room_revision"] == 1


def test_a_reload_reads_the_same_effective_room_and_revision_and_the_stored_room_is_unchanged(
    tmp_path: Path, four_lock_room: Room
):
    client, ticker = _client(tmp_path, four_lock_room, _decoy("clock_code"))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    trickster(client, session_id)
    shown = _room(client, session_id)
    assert state_of(client, session_id)["room_revision"] == 1 and _room(client, session_id) == shown
    stored = {puzzle["id"]: puzzle for puzzle in client.get(f"/api/rooms/{four_lock_room.id}").json()["puzzles"]}
    assert stored[PZ["clock_code"]]["evidence_cards"] == shown[PZ["clock_code"]]["evidence_cards"] == []  # held back (story mode)
