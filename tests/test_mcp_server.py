
import tempfile
from pathlib import Path
from orp.schema import Lesson, LessonStatus
from orp.storage import ORPStorage
from orp.mcp_server import MCPServer


def _seed(s):
    l = Lesson(recommendation="Test auth paths",
               trigger={"domain":"coding","conditions":["modify auth"]},
               status=LessonStatus.ACTIVE,
               validation={"level":"regression_guarded"},
               scope={"task_domains":["coding"],"frameworks":[],"agent_versions":[]})
    s.save_lesson(l); return l

def test_tool_defs():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        names = {t["name"] for t in MCPServer(storage=s).get_tool_definitions()}
        assert "orp_retrieve_lessons" in names and "orp_acknowledge_lesson" in names and "orp_report_outcome" in names
        s.close()

def test_retrieve():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp)); lesson=_seed(s)
        r = MCPServer(storage=s).handle_call("orp_retrieve_lessons",{"task":"modify auth","limit":5})
        assert r["count"]>=1; s.close()

def test_retrieve_empty():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        r = MCPServer(storage=s).handle_call("orp_retrieve_lessons",{"task":"","limit":3})
        assert r["count"]==0; s.close()

def test_acknowledge():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp)); lesson=_seed(s)
        r = MCPServer(storage=s).handle_call("orp_acknowledge_lesson",{"lesson_id":lesson.lesson_id})
        assert r["status"]=="acknowledged"; s.close()

def test_report_outcome():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp)); lesson=_seed(s)
        r = MCPServer(storage=s).handle_call("orp_report_outcome",{"lesson_id":lesson.lesson_id,"outcome":"success","evidence_refs":["t:r"]})
        assert r["status"]=="recorded"
        assert s.get_lesson(lesson.lesson_id).metrics.get("applied",0)>=1
        s.close()

def test_unknown_tool():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        r = MCPServer(storage=s).handle_call("orp_nonexistent",{})
        assert r["status"]=="error"; s.close()
