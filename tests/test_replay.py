
import tempfile
from pathlib import Path
from orp.replay import CounterfactualReplayer
from orp.storage import ORPStorage


def test_replay_predicted():
    r = CounterfactualReplayer().replay("exp_test","A","B")
    assert r.verification_mode in ("predicted","sandbox_replay")

def test_replay_empty_alt():
    r = CounterfactualReplayer().replay("exp_test","A","")
    assert r.result["status"] in ("predicted",)

def test_replay_storage():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        r = CounterfactualReplayer().replay("exp_test","A","B")
        s.save_replay(r)
        assert s.conn.execute("SELECT 1 FROM replays WHERE replay_id=?",(r.replay_id,)).fetchone()
        s.close()
