"""存储层 — SQLite + artifact directory"""

import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from orp.schema import (
    ExperienceRecord, Lesson, EvalArtifact, CounterfactualReplay,
    LessonDelivery, LessonEvaluation, LessonRollback, TrainingCandidate,
    TimelineEvent, Outcome, ReflectionAnalysis, Feedback,
    LessonStatus, TrustLevel, TrainingStatus, TrainingFormat, DeliveryStrategy,
)


DEFAULT_ORP_DIR = Path.home() / ".orp"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


class ORPStorage:
    """ORP 本地存储 — SQLite + artifact directory"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base = Path(base_dir) if base_dir else DEFAULT_ORP_DIR
        self.db_path = self.base / "orp.db"
        self.artifact_dir = _ensure_dir(self.base / "artifacts")
        self.eval_dir = _ensure_dir(self.base / "evals")
        self.report_dir = _ensure_dir(self.base / "reports")
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), timeout=5)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        """初始化数据库 schema"""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS experiences (
                experience_id TEXT PRIMARY KEY,
                orp_version TEXT NOT NULL DEFAULT '0.3',
                trace_ref TEXT,
                agent_json TEXT NOT NULL,
                task_json TEXT NOT NULL,
                outcome_json TEXT NOT NULL,
                reflection_json TEXT,
                artifacts_json TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS timeline_events (
                event_id TEXT PRIMARY KEY,
                experience_id TEXT NOT NULL REFERENCES experiences(experience_id),
                kind TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'agent',
                content TEXT NOT NULL,
                evidence_refs_json TEXT,
                parent_event TEXT,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lessons (
                lesson_id TEXT PRIMARY KEY,
                trigger_json TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                provenance_json TEXT,
                scope_json TEXT,
                relationships_json TEXT,
                validation_json TEXT,
                metrics_json TEXT,
                status TEXT NOT NULL DEFAULT 'candidate',
                expires_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evals (
                eval_id TEXT PRIMARY KEY,
                origin_experience TEXT NOT NULL,
                runner TEXT NOT NULL DEFAULT 'pytest',
                command TEXT NOT NULL,
                expected_json TEXT,
                generated_by TEXT DEFAULT 'agent',
                review_json TEXT,
                last_result_json TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS replays (
                replay_id TEXT PRIMARY KEY,
                experience_id TEXT NOT NULL,
                original_strategy TEXT NOT NULL,
                alternative_strategy TEXT NOT NULL,
                verification_mode TEXT DEFAULT 'sandbox_replay',
                result_json TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS deliveries (
                delivery_id TEXT PRIMARY KEY,
                lesson_id TEXT NOT NULL,
                experience_id TEXT NOT NULL,
                strategy TEXT NOT NULL,
                delivered_at TEXT NOT NULL,
                delivery_context TEXT,
                acknowledged INTEGER DEFAULT 0,
                applied INTEGER DEFAULT 0,
                application_evidence_json TEXT
            );
            CREATE TABLE IF NOT EXISTS lesson_evals (
                evaluation_id TEXT PRIMARY KEY,
                lesson_id TEXT NOT NULL,
                method TEXT NOT NULL,
                population_json TEXT,
                results_json TEXT,
                decision TEXT DEFAULT 'keep_active',
                evidence_refs_json TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rollbacks (
                rollback_id TEXT PRIMARY KEY,
                lesson_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                previous_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                affected_deliveries_json TEXT,
                replacement_lesson_id TEXT,
                evidence_refs_json TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS training_candidates (
                candidate_id TEXT PRIMARY KEY,
                source_experience_ids_json TEXT,
                format TEXT NOT NULL,
                validation_json TEXT,
                status TEXT NOT NULL DEFAULT 'candidate',
                artifact_ref TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_timeline_exp ON timeline_events(experience_id);
            CREATE INDEX IF NOT EXISTS idx_lessons_status ON lessons(status);
            CREATE INDEX IF NOT EXISTS idx_deliveries_lesson ON deliveries(lesson_id);
            CREATE INDEX IF NOT EXISTS idx_lesson_evals_lesson ON lesson_evals(lesson_id);
        """)

    # ─── Experience ───

    def save_experience(self, exp: ExperienceRecord) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO experiences
                (experience_id, orp_version, trace_ref, agent_json, task_json,
                 outcome_json, reflection_json, artifacts_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exp.experience_id, exp.orp_version, exp.trace_ref,
            json.dumps(exp.agent), json.dumps(exp.task),
            exp.outcome.model_dump_json(),
            json.dumps(exp.reflection.model_dump()) if exp.reflection else None,
            json.dumps(exp.artifacts), exp.created_at.isoformat(),
        ))
        self.conn.commit()
        for evt in exp.timeline:
            self.conn.execute("""
                INSERT OR REPLACE INTO timeline_events
                    (event_id, experience_id, kind, source, content,
                     evidence_refs_json, parent_event, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evt.id, exp.experience_id, evt.kind.value, evt.source,
                evt.content, json.dumps(evt.evidence_refs),
                evt.parent_event, evt.timestamp.isoformat(),
            ))
        # Save feedback
        for fb in exp.feedback:
            self._save_feedback(exp.experience_id, fb)

    def get_experience(self, experience_id: str) -> Optional[ExperienceRecord]:
        row = self.conn.execute(
            "SELECT * FROM experiences WHERE experience_id = ?",
            (experience_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_experience(row)

    def list_experiences(self, limit: int = 20, offset: int = 0) -> list[ExperienceRecord]:
        rows = self.conn.execute(
            "SELECT * FROM experiences ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [self._row_to_experience(r) for r in rows]

    def _row_to_experience(self, row: sqlite3.Row) -> ExperienceRecord:
        events = self.conn.execute(
            "SELECT * FROM timeline_events WHERE experience_id = ? ORDER BY timestamp",
            (row["experience_id"],)
        ).fetchall()
        return ExperienceRecord(
            orp_version=row["orp_version"],
            experience_id=row["experience_id"],
            trace_ref=row["trace_ref"],
            agent=json.loads(row["agent_json"]),
            task=json.loads(row["task_json"]),
            timeline=[TimelineEvent(**{
                "id": e["event_id"],
                "kind": e["kind"],
                "source": e["source"],
                "content": e["content"],
                "evidence_refs": json.loads(e["evidence_refs_json"]) if e["evidence_refs_json"] else [],
                "parent_event": e["parent_event"],
                "timestamp": e["timestamp"],
            }) for e in events],
            outcome=Outcome(**json.loads(row["outcome_json"])),
            reflection=ReflectionAnalysis(**json.loads(row["reflection_json"])) if row["reflection_json"] else None,
            artifacts=json.loads(row["artifacts_json"]) if row["artifacts_json"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # ─── Lesson ───

    def save_lesson(self, lesson: Lesson) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO lessons
                (lesson_id, trigger_json, recommendation, provenance_json,
                 scope_json, relationships_json, validation_json, metrics_json,
                 status, expires_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lesson.lesson_id, json.dumps(lesson.trigger), lesson.recommendation,
            json.dumps(lesson.provenance), json.dumps(lesson.scope),
            json.dumps(lesson.relationships), json.dumps(lesson.validation),
            json.dumps(lesson.metrics), lesson.status.value,
            lesson.expires_at.isoformat() if lesson.expires_at else None,
            lesson.created_at.isoformat(), lesson.updated_at.isoformat(),
        ))
        self.conn.commit()

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        row = self.conn.execute(
            "SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_lesson(row)

    def list_lessons(self, status: Optional[LessonStatus] = None, limit: int = 50) -> list[Lesson]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM lessons WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                (status.value, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM lessons ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_lesson(r) for r in rows]

    def _row_to_lesson(self, row: sqlite3.Row) -> Lesson:
        return Lesson(
            lesson_id=row["lesson_id"],
            trigger=json.loads(row["trigger_json"]),
            recommendation=row["recommendation"],
            provenance=json.loads(row["provenance_json"]) if row["provenance_json"] else {},
            scope=json.loads(row["scope_json"]) if row["scope_json"] else {},
            relationships=json.loads(row["relationships_json"]) if row["relationships_json"] else {},
            validation=json.loads(row["validation_json"]) if row["validation_json"] else {},
            metrics=json.loads(row["metrics_json"]) if row["metrics_json"] else {},
            status=LessonStatus(row["status"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def update_lesson_status(self, lesson_id: str, status: LessonStatus) -> None:
        self.conn.execute(
            "UPDATE lessons SET status = ?, updated_at = ? WHERE lesson_id = ?",
            (status.value, datetime.utcnow().isoformat(), lesson_id)
        )

    # ─── Eval ───

    def save_eval(self, eval_: EvalArtifact) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO evals
                (eval_id, origin_experience, runner, command, expected_json,
                 generated_by, review_json, last_result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            eval_.eval_id, eval_.origin_experience, eval_.runner, eval_.command,
            json.dumps(eval_.expected), eval_.generated_by,
            json.dumps(eval_.review) if eval_.review else None,
            json.dumps(eval_.last_result) if eval_.last_result else None,
            eval_.created_at.isoformat(),
        ))

    # ─── Replay ───

    def save_replay(self, replay: CounterfactualReplay) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO replays
                (replay_id, experience_id, original_strategy, alternative_strategy,
                 verification_mode, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            replay.replay_id, replay.experience_id,
            replay.original_strategy, replay.alternative_strategy,
            replay.verification_mode, json.dumps(replay.result),
            replay.created_at.isoformat(),
        ))

    # ─── Delivery ───

    def save_delivery(self, delivery: LessonDelivery) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO deliveries
                (delivery_id, lesson_id, experience_id, strategy, delivered_at,
                 delivery_context, acknowledged, applied, application_evidence_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            delivery.delivery_id, delivery.lesson_id, delivery.experience_id,
            delivery.strategy.value, delivery.delivered_at.isoformat(),
            delivery.delivery_context,
            1 if delivery.acknowledged else 0,
            1 if delivery.applied else 0,
            json.dumps(delivery.application_evidence_refs),
        ))

    def get_deliveries_for_lesson(self, lesson_id: str) -> list[LessonDelivery]:
        rows = self.conn.execute(
            "SELECT * FROM deliveries WHERE lesson_id = ? ORDER BY delivered_at DESC",
            (lesson_id,)
        ).fetchall()
        return [LessonDelivery(
            delivery_id=r["delivery_id"], lesson_id=r["lesson_id"],
            experience_id=r["experience_id"],
            strategy=DeliveryStrategy(r["strategy"]),
            delivered_at=datetime.fromisoformat(r["delivered_at"]),
            delivery_context=r["delivery_context"],
            acknowledged=bool(r["acknowledged"]),
            applied=bool(r["applied"]),
            application_evidence_refs=json.loads(r["application_evidence_json"]) if r["application_evidence_json"] else [],
        ) for r in rows]

    # ─── Lesson Evaluation ───

    def save_lesson_evaluation(self, le: LessonEvaluation) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO lesson_evals
                (evaluation_id, lesson_id, method, population_json, results_json,
                 decision, evidence_refs_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            le.evaluation_id, le.lesson_id, le.method.value,
            json.dumps(le.population), json.dumps(le.results),
            le.decision, json.dumps(le.evidence_refs),
            le.created_at.isoformat(),
        ))
        self.conn.commit()

    # ─── Rollback ───

    def save_rollback(self, rollback: LessonRollback) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO rollbacks
                (rollback_id, lesson_id, reason, previous_status, new_status,
                 affected_deliveries_json, replacement_lesson_id, evidence_refs_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rollback.rollback_id, rollback.lesson_id, rollback.reason,
            rollback.previous_status.value, rollback.new_status.value,
            json.dumps(rollback.affected_deliveries),
            rollback.replacement_lesson_id,
            json.dumps(rollback.evidence_refs),
            rollback.created_at.isoformat(),
        ))

    # ─── Training Candidate ───

    def save_training_candidate(self, tc: TrainingCandidate) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO training_candidates
                (candidate_id, source_experience_ids_json, format, validation_json,
                 status, artifact_ref, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tc.candidate_id, json.dumps(tc.source_experience_ids),
            tc.format.value, json.dumps(tc.validation),
            tc.status.value, tc.artifact_ref, tc.created_at.isoformat(),
        ))

    def list_training_candidates(self, status: Optional[TrainingStatus] = None) -> list[TrainingCandidate]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM training_candidates WHERE status = ? ORDER BY created_at DESC",
                (status.value,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM training_candidates ORDER BY created_at DESC"
            ).fetchall()
        result = []
        for r in rows:
            tc = TrainingCandidate(
                candidate_id=r["candidate_id"],
                source_experience_ids=json.loads(r["source_experience_ids_json"]),
                format=TrainingFormat(r["format"]),
                validation=json.loads(r["validation_json"]) if r["validation_json"] else {},
                status=TrainingStatus(r["status"]),
                artifact_ref=r["artifact_ref"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            result.append(tc)
        return result

    # ─── Feedback (internal) ───

    def _save_feedback(self, experience_id: str, fb: Feedback) -> None:
        self.conn.execute("""
            INSERT INTO feedback (experience_id, target_ref, source_type, source_id,
                                  verdict, explanation, evidence_refs_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            experience_id, fb.target_ref, fb.source_type.value, fb.source_id,
            fb.verdict, fb.explanation, json.dumps(fb.evidence_refs),
        ))

    # ─── Utility ───

    def save_artifact(self, name: str, content: str) -> str:
        path = self.artifact_dir / name
        path.write_text(content)
        return str(path)

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.commit()
            except Exception:
                pass
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()
