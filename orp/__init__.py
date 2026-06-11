"""ORP — Open Reflection Protocol

Turn agent failures into regression tests, reusable lessons, and measurable improvements.

Core API:
    from orp import Experience
    with Experience(goal="fix bug") as exp:
        result = agent.run()
        exp.outcome(result)
    
    from orp import autolog
    autolog()  # auto-capture all agent runs (experimental)
"""

from orp.schema import (
    ExperienceRecord, Lesson, EvalArtifact, LessonStatus,
    TimelineEvent, EventKind, LessonDelivery, LessonEvaluation,
    LessonRollback, TrainingCandidate, Outcome,
)
from orp.storage import ORPStorage
from orp.experience import ExperienceBuilder, Redactor, EvidenceLinker
from orp.capture import capture_trace_context
from orp.lessons import LessonStore
from orp.compiler import ExperienceCompiler
from orp.reflect import ReflectionAnalyzer, Challenger
from orp.replay import CounterfactualReplayer
from orp.delivery import DeliveryRouter
from orp.conflicts import ConflictDefender
from orp.effects import EffectEvaluator
from orp.rollback import RollbackManager
from orp.training import TrainingPipeline
from orp.mcp_server import MCPServer
from orp.export import ExportEngine
from orp.viewer import HTMLReporter


def autolog():
    """Enable automatic capture (experimental)"""
    import warnings
    warnings.warn("autolog() is experimental — use `orp wrap -- python agent.py` instead")


class Experience:
    """Experience context manager — captures an agent run as an ORP experience"""
    def __init__(self, goal: str = ""):
        self.goal = goal
        self._ctx = None
        self._record = None
    
    def __enter__(self):
        self._ctx = capture_trace_context(self.goal)
        return self._ctx.__enter__()
    
    def __exit__(self, *args):
        if self._ctx:
            self._ctx.__exit__(*args)
            events = self._ctx.get_events()
            if events:
                builder = ExperienceBuilder()
                self._record = builder.from_events(events, self.goal)
                storage = ORPStorage()
                storage.save_experience(self._record)
    
    @property
    def experience_id(self) -> str:
        return self._record.experience_id if self._record else ""
