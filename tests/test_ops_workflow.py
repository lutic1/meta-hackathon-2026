"""The ops workflow: started by hand or by a push of one request file on top of master to an ops/ branch, the Modal token from the repository's secrets, one guarded step per runbook action and no deploy."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from tests.test_ci_workflow import SETUP_UV

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github/workflows/ops.yml"
REQUEST = ".github/ops/request.json"
ACTIONS = ("ledger-export", "purge-dry-run", "purge", "warm", "cool", "autoscaler-settings", "promote", "quota-probe", "patch-demo-room")
UPLOAD_ARTIFACT = "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2"
VARIABLES = ("ACTION", "MODAL_ENVIRONMENT", "ROOM_ID", "ROOM_NAME", "CONFIRM")


def _text() -> str:
    return WORKFLOW.read_text()


def _job(name: str) -> str:
    body = _text().split("\njobs:\n", 1)[1]
    return re.split(r"^  (?=[\w-]+:$)", body, flags=re.MULTILINE)[["", "request", "ops"].index(name)]


def _steps() -> list[tuple[str, str]]:
    return re.findall(r"^      - (?:if: env\.ACTION == '[a-z-]+'\n        )?(uses|run): (.*)$", _job("ops"), re.MULTILINE)


def _request_script() -> str:
    return _job("request").split("python3 - <<'EOF'\n", 1)[1].split("          EOF\n", 1)[0].replace("\n          ", "\n").removeprefix("          ")


def _run_request(tmp_path: Path, event: str, request: dict[str, object] | None = None, inputs: dict[str, str] | None = None) -> tuple[int, str, dict[str, str]]:
    if request is not None:
        (tmp_path / ".github/ops").mkdir(parents=True)
        (tmp_path / REQUEST).write_text(json.dumps(request))
    output = tmp_path / "output"
    output.write_text("")
    env = {"PATH": os.environ["PATH"], "EVENT": event, "INPUTS": json.dumps(inputs or {}), "GITHUB_OUTPUT": str(output)}
    result = subprocess.run(["python3", "-"], input=_request_script(), cwd=tmp_path, env=env, capture_output=True, text=True, check=False)
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
    return result.returncode, result.stderr, outputs


def test_runs_when_started_by_hand_or_on_a_push_to_an_ops_branch_only():
    text = _text()
    assert text.startswith("name: ops\non:\n  workflow_dispatch:\n    inputs:\n")
    assert re.findall(r"^  (\w+):", text.split("\npermissions:", 1)[0], re.MULTILINE) == ["workflow_dispatch", "push"]
    assert '\n  push:\n    branches: ["ops/**"]\npermissions:\n' in text
    assert "pull_request" not in text and "schedule" not in text and "workflow_run" not in text
    assert f"options: [{', '.join(ACTIONS)}]\n" in text
    assert "options: [main, dev]\n        default: main\n" in text
    for name in ("confirm", "room_id", "room_name"):
        assert re.search(rf'^      {name}:\n        description: .*\n        type: string\n        default: ""\n', text, re.MULTILINE), name
    assert "permissions:\n  contents: read\n" in text


def test_the_request_job_holds_no_secret_and_guards_a_push_to_one_request_file_on_top_of_master():
    request = _job("request")
    assert "secrets." not in request
    assert "      - if: github.event_name == 'push'\n        uses: actions/checkout@v7\n        with:\n          fetch-depth: 0\n" in request
    assert 'git merge-base --is-ancestor "$GITHUB_SHA^" origin/master || {' in request
    assert 'changed=$(git diff --name-only "$GITHUB_SHA^" "$GITHUB_SHA")' in request
    assert f'[ "$changed" = {REQUEST} ] || {{' in request
    assert request.index("merge-base") < request.index("python3 - <<'EOF'")


def test_the_ops_job_waits_for_the_request_and_serialises_per_modal_environment():
    ops = _job("ops")
    assert "    needs: request\n" in ops
    assert "    concurrency:\n      group: ops-${{ needs.request.outputs.environment }}\n      cancel-in-progress: false\n" in ops
    assert "\nconcurrency:" not in _text().split("\njobs:\n", 1)[0]
    for variable, output in zip(VARIABLES, ("action", "environment", "room_id", "room_name", "confirm"), strict=True):
        assert f"      {variable}: ${{{{ needs.request.outputs.{output} }}}}\n" in ops, variable
    assert "inputs." not in ops


def test_a_dispatch_takes_the_inputs_and_a_push_the_request_file_with_the_same_defaults(tmp_path: Path):
    (tmp_path / "dispatch").mkdir()
    inputs = {"action": "purge", "environment": "dev", "confirm": "purge", "room_id": "", "room_name": ""}
    code, _, outputs = _run_request(tmp_path / "dispatch", "workflow_dispatch", inputs=inputs)
    assert code == 0 and outputs == {"action": "purge", "environment": "dev", "room_id": "", "room_name": "", "confirm": "purge"}
    (tmp_path / "push").mkdir()
    code, _, outputs = _run_request(tmp_path / "push", "push", request={"action": "promote", "room_id": "room_1", "room_name": "The Study"})
    assert code == 0 and outputs == {"action": "promote", "environment": "main", "room_id": "room_1", "room_name": "The Study", "confirm": ""}


@pytest.mark.parametrize(
    ("request_body", "message"),
    [
        (None, "has no .github/ops/request.json"),
        ({"action": "deploy"}, "unknown action 'deploy'"),
        ({"action": "warm", "environment": "prod"}, "unknown environment 'prod'"),
        ({"action": "warm", "extra": "x"}, "unknown key"),
        ({"action": "promote", "room_id": "a", "room_name": "b\nc=d"}, "one line"),
        ({"action": "warm", "confirm": 1}, "must be a string"),
        ({"action": "patch-demo-room"}, "needs a room_id"),
        ({"action": "patch-demo-room", "room_id": "../x"}, "needs a room_id"),
    ],
)
def test_a_bad_or_missing_request_file_fails_clearly(tmp_path: Path, request_body: dict[str, object] | None, message: str):
    code, stderr, outputs = _run_request(tmp_path, "push", request=request_body)
    assert code != 0 and message in stderr and outputs == {}


def test_checkout_uv_and_sync_run_before_the_env_guarded_action_steps():
    steps = _steps()
    assert steps[:3] == [("uses", "actions/checkout@v7"), ("uses", SETUP_UV), ("run", "uv sync --locked")]
    assert len(steps) == 3 + len(ACTIONS) + 1  # the ledger export has a second step, the upload
    assert re.findall(r"^      - if: env\.ACTION == '([a-z-]+)'$", _job("ops"), re.MULTILINE) == [
        "ledger-export", "ledger-export", "purge-dry-run", "purge", "warm", "cool", "autoscaler-settings", "promote", "patch-demo-room",
        "quota-probe",
    ]


def test_the_token_comes_from_the_repository_secrets_and_nowhere_else():
    text = _text()
    assert "MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}" in text
    assert "MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}" in text
    assert re.findall(r"secrets\.(\w+)", text) == ["MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"]
    assert re.search(r"(ak|as)-[A-Za-z0-9]{10,}", text) is None
    assert "--token" not in text and "MODEL_API_KEY" not in text and "--from-dotenv" not in text


def test_every_runbook_command_is_present_once_with_the_environment_variable():
    text = _text()
    commands = (
        'uv run scripts/ledger.py export --env "$MODAL_ENVIRONMENT"',
        'uv run scripts/purge_judge_rooms.py --env "$MODAL_ENVIRONMENT" --dry-run',
        'uv run scripts/purge_judge_rooms.py --env "$MODAL_ENVIRONMENT"\n',
        'uv run modal function autoscaler update -e "$MODAL_ENVIRONMENT" keyframe/web --min-containers 1',
        'uv run modal function autoscaler update -e "$MODAL_ENVIRONMENT" keyframe/web --min-containers 0',
        'uv run scripts/promote_room.py --env "$MODAL_ENVIRONMENT" --room "$ROOM_ID" "$ROOM_NAME"\n',
        'uv run scripts/quota_probe.py --env "$MODAL_ENVIRONMENT"\n',
    )
    for command in commands:
        assert text.count(command) == 1, command
    assert text.count('uv run modal function autoscaler settings -e "$MODAL_ENVIRONMENT" keyframe/web') == 3


def test_the_ledger_export_is_uploaded_as_an_artifact_and_never_committed():
    text = _text()
    assert f"uses: {UPLOAD_ARTIFACT}\n" in text
    assert "name: ledger-export-${{ env.MODAL_ENVIRONMENT }}\n" in text
    assert "path: spend/exports/\n" in text and "if-no-files-found: error\n" in text
    assert "git commit" not in text and "git push" not in text and "contents: write" not in text


def test_the_real_purge_runs_only_when_confirm_is_the_word_purge():
    ops = _job("ops")
    purge = ops.split("- if: env.ACTION == 'purge'\n", 1)[1].split("- if: env.ACTION == 'warm'", 1)[0]
    assert '[ "$CONFIRM" = purge ] || {' in purge and "exit 1; }" in purge
    assert purge.index('[ "$CONFIRM" = purge ]') < purge.index("uv run scripts/purge_judge_rooms.py")
    assert "--dry-run" not in purge


def test_the_promotion_runs_only_when_both_room_values_are_given():
    text = _text()
    promote = _job("ops").split("- if: env.ACTION == 'promote'\n", 1)[1]
    assert '[ -n "$ROOM_ID" ] && [ -n "$ROOM_NAME" ] || {' in promote and "exit 1; }" in promote
    assert promote.index('[ -n "$ROOM_ID" ]') < promote.index("uv run scripts/promote_room.py")
    assert "seed_rooms.py" not in text  # the Demo room comes from the Volume, never from a checkout


def test_the_quota_probe_runs_from_a_dispatch_or_a_request_file_on_an_ephemeral_dict_only(tmp_path: Path):
    probe = _job("ops").split("- if: env.ACTION == 'quota-probe'\n", 1)[1]
    assert probe == '        run: uv run scripts/quota_probe.py --env "$MODAL_ENVIRONMENT"\n'
    assert "quota-probe runs" in _text().split("options:", 1)[0]  # the action's description says what it does
    (tmp_path / "dispatch").mkdir()
    inputs = {"action": "quota-probe", "environment": "dev", "confirm": "", "room_id": "", "room_name": ""}
    code, _, outputs = _run_request(tmp_path / "dispatch", "workflow_dispatch", inputs=inputs)
    assert code == 0 and outputs["action"] == "quota-probe" and outputs["environment"] == "dev"
    (tmp_path / "push").mkdir()
    code, _, outputs = _run_request(tmp_path / "push", "push", request={"action": "quota-probe", "environment": "dev"})
    assert code == 0 and outputs == {"action": "quota-probe", "environment": "dev", "room_id": "", "room_name": "", "confirm": ""}


PATCH = '"ops/patches/$ROOM_ID.json"'


def test_the_demo_room_patch_is_a_dry_run_unless_confirm_is_the_word_patch_and_reads_its_file_from_the_checkout():
    patch = _job("ops").split("- if: env.ACTION == 'patch-demo-room'\n", 1)[1]
    command = f'uv run scripts/patch_demo_room.py --env "$MODAL_ENVIRONMENT" --room "$ROOM_ID" --patch {PATCH}'
    assert patch.count(command + " --dry-run\n") == 1 and patch.count(command + "\n") == 1
    assert 'if [ "$CONFIRM" = patch ]; then' in patch
    assert patch.index('[ "$CONFIRM" = patch ]') < patch.index(command + "\n") < patch.index("else") < patch.index("--dry-run")
    assert "patch-demo-room" in _text().split("options:", 1)[0]  # the action's description says what it does


def test_the_request_validator_accepts_patch_demo_room_with_a_room_id(tmp_path: Path):
    request = {"action": "patch-demo-room", "room_id": "room_01M61TZ74F0FP3X9HHTMXGTPB9", "confirm": "patch"}
    code, _, outputs = _run_request(tmp_path, "push", request=request)
    assert code == 0 and outputs == {**request, "environment": "main", "room_name": ""}


def test_no_deploy_and_no_unpinned_third_party_action():
    text = _text()
    assert "modal deploy" not in text and "modal serve" not in text and "modal run" not in text
    for action in re.findall(r"uses: (.*)$", text, re.MULTILINE):
        assert action.startswith("actions/") or re.fullmatch(r"\S+@[0-9a-f]{40} # v\d+\.\d+\.\d+", action), action


def test_the_request_file_lives_only_on_request_branches():
    tracked = subprocess.run(["git", "ls-files", REQUEST], cwd=REPO, capture_output=True, text=True, check=True).stdout
    assert tracked == ""
