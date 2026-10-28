"""The README and the keyframe-devops skill describe the two workflows as the files under .github/workflows are."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CI = (REPO / ".github/workflows/ci.yml").read_text()
DEVOPS = REPO / ".claude/skills/keyframe-devops"


def test_readme_names_both_workflows_and_the_keyframe_branch_trigger():
    readme = (REPO / "README.md").read_text()
    assert "keyframe/**" in readme
    assert ".github/workflows/deploy.yml" in readme
    assert "on master and pull requests" not in readme


def test_devops_skill_describes_the_real_ci_trigger():
    skill = (DEVOPS / "SKILL.md").read_text()
    ladder = (DEVOPS / "references/check-ladder.md").read_text()
    assert "keyframe/**" in skill and "keyframe/**" in ladder
    assert "deploy.yml" in ladder


def test_templates_ci_yml_block_matches_the_real_workflow():
    templates = (DEVOPS / "references/templates.md").read_text()
    match = re.search(r"<!-- file: \.github/workflows/ci\.yml -->\n```yaml\n(.*?)```", templates, re.DOTALL)
    assert match is not None
    assert match.group(1) == CI
