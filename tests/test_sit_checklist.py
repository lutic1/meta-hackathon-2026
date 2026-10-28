"""The SIT checklist records the first hosted Build on the real room: its job and room ids sit in the SIT-03 and SIT-08 rows and in the Wed Oct 28 run-log row."""

from pathlib import Path

CHECKLIST = (Path(__file__).resolve().parents[1] / "docs/implementation-artifacts/sit-checklist.md").read_text()
JOB = "job_01M61TZ74F6F3AVVEMPRAS4V1G"
ROOM = "room_01M61TZ74F0FP3X9HHTMXGTPB9"


def row(case: str) -> str:
    line = next(ln for ln in CHECKLIST.splitlines() if ln.startswith(f"| {case} |"))
    return line.rsplit("|", 2)[1]


def test_sit_03_and_sit_08_first_run_cells_record_the_hosted_build():
    for case in ("SIT-03", "SIT-08"):
        first_run = row(case)
        assert "Wed Oct 28" in first_run and JOB in first_run and ROOM in first_run and "182 s" in first_run


def test_the_wed_oct_28_run_log_row_records_the_real_room_runs():
    line = next(ln for ln in CHECKLIST.splitlines() if ln.startswith("| Wed Oct 28 |"))
    assert "SIT-01" in line and "SIT-02" in line and "c78eb85" in line
    assert JOB in line and "19 builds left" not in CHECKLIST
