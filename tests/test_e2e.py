import tempfile
from pathlib import Path
from orp.schema import (
    ExperienceRecord, TimelineEvent, Outcome, Lesson, LessonStatus,
    DeliveryStrategy, EvaluationMethod, TrainingFormat,
)
from orp.storage import ORPStorage
from orp.reflect import ReflectionAnalyzer, Challenger
from orp.compiler import ExperienceCompiler
from orp.conflicts import ConflictDefender
from orp.delivery import DeliveryRouter
from orp.effects import EffectEvaluator
from orp.rollback import RollbackManager
from orp.training import TrainingPipeline
from orp.mcp_server import MCPServer


def test_full_loop():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        g = "Fix authentication for anonymous users"

        # 1. Failed agent run → ExperienceRecord
        exp = ExperienceRecord(
            agent={"id":"coding-agent","version":"1.0","model":"gpt-4"},
            task={"goal":g,"domain":"coding"},
            timeline=[
                TimelineEvent(kind="observation",content="pytest: 34 passed, 1 failed",source="tool",evidence_refs=["a:pytest"]),
                TimelineEvent(kind="claim",content="The fix is complete",source="agent"),
                TimelineEvent(kind="observation",content="FAILED test_anonymous_access.py",source="tool",evidence_refs=["a:pytest"]),
            ],
            outcome=Outcome(status="failed"),
        )
        s.save_experience(exp)

        # 2-3. Reflect + Challenge
        ref = ReflectionAnalyzer().analyze(exp)
        assert ref.diagnosis is not None
        challenged = Challenger().challenge(exp)
        assert any("No evidence" in c["issue"] for c in challenged)

        # 4. Compile → Lesson + Eval
        arts = ExperienceCompiler().compile(exp)
        lesson = arts["lessons"][0]
        lesson.status = LessonStatus.ACTIVE
        s.save_lesson(lesson)
        # Verify lesson is ACTIVE in DB
        reloaded = s.get_lesson(lesson.lesson_id)
        assert reloaded.status == LessonStatus.ACTIVE, f"Expected ACTIVE, got {reloaded.status}"

        # 5. Conflict check — creates another active lesson but doesn't modify lesson
        conflicting = Lesson(recommendation="Never write tests first",
                             trigger={"domain":"coding","conditions":["modify auth"]},
                             scope={"task_domains":["coding"],"frameworks":[],"agent_versions":[]},
                             status=LessonStatus.ACTIVE)
        s.save_lesson(conflicting)
        defender = ConflictDefender(s)
        defender.check_new_lesson(conflicting)

        # Verify lesson still ACTIVE after conflict check
        reloaded2 = s.get_lesson(lesson.lesson_id)
        assert reloaded2.status == LessonStatus.ACTIVE

        # 6. MCP delivery + retrieval
        router = DeliveryRouter(s)
        router.deliver(lesson, exp.experience_id, strategy=DeliveryStrategy.MCP_TOOL)
        
        # Verify lesson still ACTIVE after delivery
        reloaded3 = s.get_lesson(lesson.lesson_id)
        assert reloaded3.status == LessonStatus.ACTIVE
        
        # MCP should use the same storage
        server = MCPServer(s)
        # First, check list_lessons directly
        all_active = s.list_lessons(status=LessonStatus.ACTIVE)
        assert len(all_active) >= 1, f"No active lessons in DB (found {len(all_active)})"
        
        r = server.handle_call("orp_retrieve_lessons", {"task":g, "limit":3})
        assert r["count"] >= 1, f"MCP count=0, active in DB={len(all_active)}"

        # 7. Evaluate + Rollback
        eval_ = EffectEvaluator(s).evaluate_matched_baseline(lesson, baseline_success_rate=0.50)
        s.save_lesson_evaluation(eval_)
        RollbackManager(s).rollback(lesson.lesson_id, reason="Negative effect", new_status=LessonStatus.UNDER_REVIEW)
        assert s.get_lesson(lesson.lesson_id).status == LessonStatus.UNDER_REVIEW

        # 8. Training pipeline
        ok_exp = ExperienceRecord(
            agent={"id":"coding-agent"}, task={"goal":"Fix auth after ORP lesson","domain":"coding"},
            timeline=[TimelineEvent(kind="observation",content="35 passed, 0 failed",source="tool")],
            outcome=Outcome(status="success"),
        )
        s.save_experience(ok_exp)
        pipe = TrainingPipeline(s)
        tc = pipe.create_candidate(ok_exp, TrainingFormat.SFT_EXAMPLE)
        assert tc is not None
        assert pipe.approve(tc.candidate_id, human_reviewed=True, privacy_reviewed=True, license_reviewed=True)
        exported = pipe.export_approved()
        assert len(exported) == 1
        assert exported[0]["candidate_id"] == tc.candidate_id

        # 9. Verify storage state
        assert len(s.list_experiences()) >= 2
        assert len(s.list_lessons()) >= 2
        s.close()
