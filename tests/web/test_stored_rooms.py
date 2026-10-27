"""UX-DR8, UX-DR19, UX-DR21, UX-DR62, AR-13: the Stored Rooms list on Local `#/`, read from its source.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile.
"""

import json
import re

from src.domain.schema import Derived
from tests.web.design import WEB_SRC, css_rules, design_text, source_ts


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _rules() -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / "components/stored-room-row.css").read_text())


def test_the_list_comes_only_from_get_rooms_read_afresh_on_every_visit():
    api, shell = _ts("api/index.ts"), _ts("shell.ts")
    assert "return getJson<RoomSummary[]>('/rooms')" in api
    render = shell.split("async function render()", 1)[1].split("\n  }\n", 1)[0]
    assert "} else if (place.route.name === 'home' && meta.mode === 'local') {" in render
    assert render.index("await answered(mine, listRooms)") < render.index("show(")
    assert "content = { name: 'rooms', rooms, profile: place.profile, mode: meta.mode, retention: meta.retention }" in render
    # No room list of the browser's own: nothing cached across visits, and no browser storage anywhere but the
    # Capture Timer's one run (2.17), the per-session mark that "Begin" was pressed (1.22) and the Player profile's
    # IndexedDB, which holds Room results only (5.2).
    assert "listRooms" not in shell.split("async function render()", 1)[0].split("export function startShell", 1)[1]
    for path, text in source_ts().items():
        if path.endswith(("web/src/capture-timer.ts", "web/src/welcome.ts", "web/src/profile/index.ts")):
            continue
        assert not re.search(r"localStorage|sessionStorage|indexedDB", text), path


def test_rows_follow_the_served_order_and_the_empty_list_reads_no_rooms_yet():
    ts = _ts("stored-rooms.ts")
    assert "list.append(...rooms.map((room) => storedRoomRow(room, profile, () => void start(room))))" in ts
    assert not re.search(r"\.sort\(|\.reverse\(|\.filter\(", ts), "newest build first is the server's order"
    assert "if (rooms.length === 0)" in ts and "empty.textContent = strings.noRooms" in ts
    assert "empty.className = 'stored-room-empty body-sm'" in ts


def test_a_row_shows_the_cover_thumbnail_the_title_the_puzzle_count_and_play():
    row = _ts("components/stored-room-row.ts")
    assert "cover.src = photoUrl(room.room_id, room.cover_photo)" in row and "cover.alt = ''" in row
    assert "cover.width = 96" in row and "cover.height = 72" in row
    assert "return room.name || BUILT_AT.format(new Date(room.built_at))" in row
    assert "new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })" in row
    assert "count.textContent = fill(strings.puzzleCount, { n: room.puzzle_count })" in row
    assert "count.className = 'stored-room-meta body-sm'" in row
    assert "secondaryButton({ label: strings.play, onActivate: onPlay })" in row
    assert row.count("secondaryButton(") == 1  # Play only; "How this room was built" joins in 2.31
    assert "`/api/rooms/${encodeURIComponent(roomId)}/photos/${index}`" in _ts("api/index.ts")


def test_play_posts_the_profiles_session_start_and_routes_to_the_play_screen():
    ts, api = _ts("stored-rooms.ts"), _ts("api/index.ts")
    assert "await startSession(await sessionStart(room.room_id, profile, mode))" in ts
    assert "location.hash = placeHref({ route: { name: 'play', sessionId: session.id }, profile })" in ts
    assert "return postJson<SessionState>('/sessions', body)" in api
    assert "method: 'POST'" in api and "body: JSON.stringify(body)" in api
    assert "if (starting) return" in ts  # one start at a time


def test_the_client_fresh_block_is_the_server_derived_fresh():
    derive = _ts("profile/derive.ts")
    literal = re.search(r"export function freshDerived\(\): Derived \{\n  return (\{.*?\})\n\}", derive).group(1)
    as_json = re.sub(r"(\w+):", r'"\1":', literal)
    assert json.loads(as_json) == Derived.fresh().model_dump(mode="json")


def test_a_refused_start_shows_the_session_start_refused_banner_whose_try_again_starts_again():
    ts = _ts("stored-rooms.ts")
    refused = ts.split("} catch {", 1)[1].split("} finally {", 1)[0]
    assert "showBanner(banners, {" in refused and "variant: 'error'" in refused
    assert "heading: strings.sessionStartRefused" in refused and "sentence: strings.sessionStartRefusedBody" in refused
    assert "actions: [{ label: strings.tryAgain, onActivate: () => void start(room) }]" in refused
    # The banner slot sits at the top of the left area, above the list; showBanner moves focus to the banner.
    capture = _ts("capture.ts")
    assert "left.append(banners, controls)" in capture
    assert "storedRooms(rooms, profile, mode, banners))" in capture
    assert "const banners = bannerSlot()" in capture


def test_the_row_is_chrome_with_a_hairline_rule_and_a_lamp_ring_on_hover():
    rules = _rules()
    row = rules[".stored-room-row"]
    assert row["background"] == "var(--chrome)" and row["border-radius"] == "var(--rounded-md)"
    assert row["outline"] == "2px solid transparent"
    assert row["transition"] == "outline-color var(--motion-hover) var(--motion-ease)"
    assert rules[".stored-room-row:hover"] == {"outline-color": "var(--lamp)"}
    assert rules[".stored-room-row + .stored-room-row"] == {"border-top": "1px solid var(--hairline)"}
    cover = rules[".stored-room-cover"]
    assert (cover["width"], cover["height"], cover["object-fit"]) == ("96px", "72px", "cover")
    assert rules[".stored-room-title"]["color"] == "var(--text)"
    assert rules[".stored-room-meta"]["color"] == "var(--text-muted)"
    assert rules[".stored-room-empty"]["color"] == "var(--text-muted)"
    # Play is a native button: Tab reaches it, Enter starts it, and it keeps the global two-tone focus ring.
    assert "tabIndex" not in _ts("components/stored-room-row.ts")


def test_every_stored_room_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("text", "chrome"), ("text-muted", "chrome"), ("lamp", "chrome"), ("text-muted", "canvas"),
             ("error-text", "error-surface"), ("text", "error-surface"), ("lamp", "error-surface")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
