"""The manual deploy workflow: started by hand only, the Modal token from the repository's secrets, the pre-deploy ladder before `modal deploy`."""

import re
from pathlib import Path

from tests.test_ci_workflow import SETUP_UV

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github/workflows/deploy.yml"


def _text() -> str:
    return WORKFLOW.read_text()


def test_runs_only_when_started_by_hand_with_the_environment_and_min_containers_as_inputs():
    text = _text()
    assert text.startswith("name: deploy\non:\n  workflow_dispatch:\n    inputs:\n")
    assert re.search(r"^  (push|pull_request|schedule|workflow_run):", text, re.MULTILINE) is None
    assert "options: [main, dev]\n        default: main\n" in text
    assert 'options: ["0", "1"]\n        default: "0"\n' in text
    assert "permissions:\n  contents: read\n" in text


def test_the_token_comes_from_the_repository_secrets_and_nowhere_else():
    text = _text()
    assert "MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}" in text
    assert "MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}" in text
    assert re.search(r"(ak|as)-[A-Za-z0-9]{10,}", text) is None
    assert "MODEL_API_KEY" not in text and "--from-dotenv" not in text


def test_the_predeploy_ladder_runs_before_one_modal_deploy_of_the_app_module():
    text = _text()
    steps = re.findall(r"^      - (?:id: \w+\n        )?(uses|run): (.*)$", text, re.MULTILINE)
    assert steps[:3] == [("uses", "actions/checkout@v7"), ("uses", SETUP_UV), ("uses", "actions/setup-node@v7")]
    assert steps[3] == ("run", "bash scripts/check.sh --predeploy")
    assert text.count("modal deploy") == 1
    assert 'uv run modal deploy -e "$MODAL_ENVIRONMENT" -m src.api.modal_app' in text
    assert "MIN_CONTAINERS: ${{ inputs.min_containers }}" in text
    assert "--strategy recreate" not in text


def test_the_deploy_ends_with_a_smoke_test_of_the_meta_route():
    text = _text()
    assert '/api/meta" && exit 0' in text
    assert text.rstrip().endswith("exit 1")
