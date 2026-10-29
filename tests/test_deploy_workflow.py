"""The deploy workflow: started by hand or by a push to a deploy/ branch of a commit master carries, the Modal token from the repository's secrets, the pre-deploy ladder before `modal deploy`."""

import re
from pathlib import Path

from tests.test_ci_workflow import SETUP_UV

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github/workflows/deploy.yml"
ENVIRONMENT = "${{ inputs.environment || (github.ref_name == 'deploy/dev' && 'dev' || 'main') }}"
MIN_CONTAINERS = "${{ inputs.min_containers || (github.ref_name == 'deploy/main-warm' && '1' || '0') }}"


def _text() -> str:
    return WORKFLOW.read_text()


def _steps() -> list[tuple[str, str]]:
    return re.findall(r"^      - (?:(?:id|if): .*\n        )?(uses|run): (.*)$", _text(), re.MULTILINE)


def test_runs_when_started_by_hand_or_on_a_push_to_the_three_deploy_branches_only():
    text = _text()
    assert text.startswith("name: deploy\non:\n  workflow_dispatch:\n    inputs:\n")
    assert re.findall(r"^  (\w+):", text.split("\npermissions:", 1)[0], re.MULTILINE) == ["workflow_dispatch", "push"]
    assert '\n  push:\n    branches: ["deploy/main", "deploy/main-warm", "deploy/dev"]\npermissions:\n' in text
    assert "pull_request" not in text and "schedule" not in text and "workflow_run" not in text
    assert "options: [main, dev]\n        default: main\n" in text
    assert 'options: ["0", "1"]\n        default: "0"\n' in text
    assert "permissions:\n  contents: read\n" in text


def test_the_environment_and_min_containers_follow_the_inputs_or_the_pushed_branch():
    text = _text()
    assert f"MODAL_ENVIRONMENT: {ENVIRONMENT}\n" in text
    assert f"MIN_CONTAINERS: {MIN_CONTAINERS}\n" in text
    assert f"concurrency:\n  group: deploy-{ENVIRONMENT}\n  cancel-in-progress: false\n" in text


def test_a_push_deploys_only_a_commit_master_already_carries_before_any_other_step():
    text = _text()
    steps = _steps()
    assert steps[:2] == [("uses", "actions/checkout@v7"), ("run", "|")]
    assert "      - uses: actions/checkout@v7\n        with:\n          fetch-depth: 0\n" in text
    guard = text.split("      - if: github.event_name == 'push'\n        run: |\n", 1)[1].split("      - uses:", 1)[0]
    assert 'git merge-base --is-ancestor "$GITHUB_SHA" origin/master || {' in guard and "exit 1; }" in guard
    assert "refusing to deploy" in guard


def test_the_token_comes_from_the_repository_secrets_and_nowhere_else():
    text = _text()
    assert "MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}" in text
    assert "MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}" in text
    assert re.findall(r"secrets\.(\w+)", text) == ["MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"]
    assert re.search(r"(ak|as)-[A-Za-z0-9]{10,}", text) is None
    assert "MODEL_API_KEY" not in text and "--from-dotenv" not in text


def test_the_predeploy_ladder_runs_before_one_modal_deploy_of_the_app_module():
    text = _text()
    steps = _steps()
    assert steps[2:4] == [("uses", SETUP_UV), ("uses", "actions/setup-node@v7")]
    assert steps[4] == ("run", "bash scripts/check.sh --predeploy")
    assert text.count("modal deploy") == 1
    assert 'uv run modal deploy -e "$MODAL_ENVIRONMENT" -m src.api.modal_app' in text
    assert "--strategy recreate" not in text


def test_the_deploy_ends_with_a_smoke_test_of_the_meta_route():
    text = _text()
    assert '/api/meta" && exit 0' in text
    assert text.rstrip().endswith("exit 1")


def test_ci_still_holds_no_secret_and_no_deploy():
    ci = (REPO / ".github/workflows/ci.yml").read_text()
    assert "secrets." not in ci and "modal deploy" not in ci and "MODAL_TOKEN" not in ci
