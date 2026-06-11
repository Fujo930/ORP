
import tempfile
from pathlib import Path
from orp.schema import (
    ExperienceRecord, TimelineEvent, Outcome, TrainingFormat, TrainingStatus,
)
from orp.storage import ORPStorage
from orp.training import TrainingPipeline


def _ok():
    return ExperienceRecord(
        agent={"id":"t"}, task={"goal":"Fix","domain":"coding"},
        timeline=[TimelineEvent(kind="observation",content="ok",source="tool")],
        outcome=Outcome(status="success"),
    )

def _fail():
    return ExperienceRecord(
        agent={"id":"t"}, task={"goal":"Fix","domain":"coding"},
        timeline=[TimelineEvent(kind="observation",content="fail",source="tool")],
        outcome=Outcome(status="failed"),
    )

def test_sft_candidate():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp)); s.save_experience(_ok())
        tc = TrainingPipeline(s).create_candidate(s.list_experiences()[0], TrainingFormat.SFT_EXAMPLE)
        assert tc is not None and tc.format==TrainingFormat.SFT_EXAMPLE and tc.status==TrainingStatus.CANDIDATE
        s.close()

def test_skip_failure():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp)); s.save_experience(_fail())
        assert TrainingPipeline(s).create_candidate(s.list_experiences()[0], TrainingFormat.SFT_EXAMPLE) is None
        s.close()

def test_approve_and_export():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp)); s.save_experience(_ok())
        pipe = TrainingPipeline(s)
        tc = pipe.create_candidate(s.list_experiences()[0], TrainingFormat.SFT_EXAMPLE)
        assert pipe.approve(tc.candidate_id)
        assert len(pipe.export_approved()) == 1
        s.close()

def test_approve_requires_all():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp)); s.save_experience(_ok())
        pipe = TrainingPipeline(s)
        tc = pipe.create_candidate(s.list_experiences()[0], TrainingFormat.SFT_EXAMPLE)
        assert not pipe.approve(tc.candidate_id, human_reviewed=True, privacy_reviewed=True, license_reviewed=False)
        assert len(pipe.export_approved()) == 0
        s.close()
