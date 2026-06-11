
import tempfile
from pathlib import Path
from orp.schema import ExperienceRecord, TimelineEvent, Outcome
from orp.storage import ORPStorage
from orp.viewer import HTMLReporter


def test_empty():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        h = HTMLReporter(s).render_report("Test")
        assert "Experiences" in h and "Lessons" in h
        s.close()

def test_with_exp():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        s.save_experience(ExperienceRecord(
            agent={"id":"a"}, task={"goal":"Fix login","domain":"coding"},
            timeline=[TimelineEvent(kind="observation",content="fail",source="tool")],
            outcome=Outcome(status="failed"),
        ))
        h = HTMLReporter(s).render_report()
        assert "Fix login" in h and "failed" in h
        s.close()

def test_write_file():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        p = str(Path(tmp)/"r.html")
        path = HTMLReporter(s).write_report(p)
        assert Path(path).exists()
        s.close()
