"""The manual ops workflow: started by hand only, the Modal token from the repository's secrets, one guarded step per runbook action and no deploy."""

import re
from pathlib import Path

from tests.test_ci_workflow import SETUP_UV

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github/workflows/ops.yml"
ACTIONS = ("ledger-export", "purge-dry-run", "purge", "warm", "cool", "autoscaler-settings", "promote")
UPLOAD_ARTIFACT = "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2"


def _text() -> str:
    return WORKFLOW.read_text()


def _steps() -> list[tuple[str, str]]:
    return re.findall(r"^      - (?:if: inputs\.action == '[a-z-]+'\n        )?(?:env:\n(?:          .*\n)+        )?(uses|run): (.*)$", _text(), re.MULTILINE)


def test_runs_only_when_started_by_hand_with_the_action_environment_confirm_and_room_inputs():
    text = _text()
    assert text.startswith("name: ops\non:\n  workflow_dispatch:\n    inputs:\n")
    assert re.search(r"^  (push|pull_request|schedule|workflow_run):", text, re.MULTILINE) is None
    assert f"options: [{', '.join(ACTIONS)}]\n" in text
    assert "options: [main, dev]\n        default: main\n" in text
    for name in ("confirm", "room_id", "room_name"):
        assert re.search(rf'^      {name}:\n        description: .*\n        type: string\n        default: ""\n', text, re.MULTILINE), name
    assert "permissions:\n  contents: read\n" in text


def test_the_token_comes_from_the_repository_secrets_and_nowhere_else():
    text = _text()
    assert "MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}" in text
    assert "MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}" in text
    assert re.findall(r"secrets\.(\w+)", text) == ["MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"]
    assert re.search(r"(ak|as)-[A-Za-z0-9]{10,}", text) is None
    assert "--token" not in text and "MODEL_API_KEY" not in text and "--from-dotenv" not in text


def test_checkout_uv_and_sync_run_before_the_guarded_action_steps():
    steps = _steps()
    assert steps[:3] == [("uses", "actions/checkout@v7"), ("uses", SETUP_UV), ("run", "uv sync --locked")]
    assert len(steps) == 3 + len(ACTIONS) + 1  # the ledger export has a second step, the upload
    assert re.findall(r"^      - if: inputs\.action == '([a-z-]+)'$", _text(), re.MULTILINE) == [
        "ledger-export", "ledger-export", "purge-dry-run", "purge", "warm", "cool", "autoscaler-settings", "promote",
    ]


def test_every_runbook_command_is_present_once_with_the_environment_input():
    text = _text()
    commands = (
        'uv run scripts/ledger.py export --env "$MODAL_ENVIRONMENT"',
        'uv run scripts/purge_judge_rooms.py --env "$MODAL_ENVIRONMENT" --dry-run',
        'uv run scripts/purge_judge_rooms.py --env "$MODAL_ENVIRONMENT"\n',
        'uv run modal function autoscaler update -e "$MODAL_ENVIRONMENT" keyframe/web --min-containers 1',
        'uv run modal function autoscaler update -e "$MODAL_ENVIRONMENT" keyframe/web --min-containers 0',
        'uv run scripts/promote_room.py --env "$MODAL_ENVIRONMENT" --room "$ROOM_ID" "$ROOM_NAME"\n',
    )
    for command in commands:
        assert text.count(command) == 1, command
    assert text.count('uv run modal function autoscaler settings -e "$MODAL_ENVIRONMENT" keyframe/web') == 3
    assert "MODAL_ENVIRONMENT: ${{ inputs.environment }}" in text


def test_the_ledger_export_is_uploaded_as_an_artifact_and_never_committed():
    text = _text()
    assert f"uses: {UPLOAD_ARTIFACT}\n" in text
    assert "path: spend/exports/\n" in text and "if-no-files-found: error\n" in text
    assert "git commit" not in text and "git push" not in text and "contents: write" not in text


def test_the_real_purge_runs_only_when_the_confirm_input_is_the_word_purge():
    text = _text()
    purge = text.split("- if: inputs.action == 'purge'\n", 1)[1].split("- if: inputs.action == 'warm'", 1)[0]
    assert "CONFIRM: ${{ inputs.confirm }}" in purge
    assert '[ "$CONFIRM" = purge ] || {' in purge and "exit 1; }" in purge
    assert purge.index('[ "$CONFIRM" = purge ]') < purge.index("uv run scripts/purge_judge_rooms.py")
    assert "--dry-run" not in purge


def test_the_promotion_runs_only_when_both_room_inputs_are_given():
    text = _text()
    promote = text.split("- if: inputs.action == 'promote'\n", 1)[1]
    assert "ROOM_ID: ${{ inputs.room_id }}" in promote and "ROOM_NAME: ${{ inputs.room_name }}" in promote
    assert '[ -n "$ROOM_ID" ] && [ -n "$ROOM_NAME" ] || {' in promote and "exit 1; }" in promote
    assert promote.index('[ -n "$ROOM_ID" ]') < promote.index("uv run scripts/promote_room.py")
    assert "seed_rooms.py" not in text  # the Demo room comes from the Volume, never from a checkout


def test_no_deploy_and_no_unpinned_third_party_action():
    text = _text()
    assert "modal deploy" not in text and "modal serve" not in text and "modal run" not in text
    for action in re.findall(r"uses: (.*)$", text, re.MULTILINE):
        assert action.startswith("actions/") or re.fullmatch(r"\S+@[0-9a-f]{40} # v\d+\.\d+\.\d+", action), action
