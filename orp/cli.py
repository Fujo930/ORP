"""ORP CLI — 命令行界面"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from orp.schema import (
    ExperienceRecord, TimelineEvent, EventKind, LessonStatus,
    CounterfactualReplay, EvalArtifact, DeliveryStrategy,
)
from orp.storage import ORPStorage
from orp.experience import ExperienceBuilder, Redactor, EvidenceLinker
from orp.capture import capture_command, capture_git_diff, capture_trace_context
from orp.reflect import ReflectionAnalyzer, Challenger
from orp.replay import CounterfactualReplayer
from orp.compiler import ExperienceCompiler
from orp.lessons import LessonStore
from orp.conflicts import ConflictDefender
from orp.delivery import DeliveryRouter
from orp.effects import EffectEvaluator
from orp.rollback import RollbackManager
from orp.training import TrainingPipeline
from orp.mcp_server import MCPServer
from orp.export import ExportEngine
from orp.viewer import HTMLReporter


def cmd_wrap(args):
    """orp wrap -- python agent.py"""
    goal = args.goal or " ".join(args.command[:3])
    with capture_trace_context(goal) as ctx:
        result = capture_command(args.command, timeout=args.timeout)
        ctx.set_outcome("success" if result["success"] else "failed", result)
    
    events = ctx.get_events()
    events.append(TimelineEvent(
        kind="outcome",
        content="Exit code: " + str(result.get("exit_code", -1)),
        source="system",
    ))
    builder = ExperienceBuilder()
    record = builder.from_events(events, goal=goal)
    record.outcome.status = "success" if result.get("success", False) else "failed"
    
    storage = ORPStorage()
    storage.save_experience(record)
    print("Experience recorded: " + record.experience_id)
    print("  Outcome: " + record.outcome.status)


def cmd_inspect(args):
    """orp inspect [id]"""
    storage = ORPStorage()
    if args.id == "latest":
        exps = storage.list_experiences(limit=1)
        if not exps:
            print("No experiences found")
            return
        exp = exps[0]
    else:
        exp = storage.get_experience(args.id)
        if not exp:
            print("Experience not found: " + args.id)
            return
    
    print()
    print("Experience: " + exp.experience_id)
    print("  Agent:    " + exp.agent.get("id", "?"))
    print("  Model:    " + exp.agent.get("model", "?"))
    print("  Goal:     " + exp.task.get("goal", "?"))
    print("  Outcome:  " + exp.outcome.status)
    print("  Timeline: " + str(len(exp.timeline)) + " events")
    print()
    print("Events:")
    for evt in exp.timeline:
        markers = {"observation": "\u25cf", "claim": "\u25b3", "action": "\u25b6",
                   "feedback": "\u25a0", "outcome": "\u25c6", "decision": "\u25c8"}
        marker = markers.get(evt.kind.value, "\u25cb")
        print("  " + marker + " [" + evt.kind.value + "] " + evt.content[:120])


def cmd_learn(args):
    """orp learn [id]"""
    storage = ORPStorage()
    if args.id == "latest":
        exps = storage.list_experiences(limit=1)
        if not exps:
            print("No experiences to learn from")
            return
        exp = exps[0]
    else:
        exp = storage.get_experience(args.id)
        if not exp:
            print("Experience not found: " + args.id)
            return
    
    print("Learning from: " + exp.experience_id)
    
    analyzer = ReflectionAnalyzer()
    reflection = analyzer.analyze(exp)
    exp.reflection = reflection
    print("  Diagnosis: " + (reflection.diagnosis or "none"))
    
    challenger = Challenger()
    challenged = challenger.challenge(exp)
    if challenged:
        print("  Claims challenged: " + str(len(challenged)))
        for c in challenged:
            print("    " + c["issue"] + ": " + c["content"][:80])
    
    compiler = ExperienceCompiler()
    artifacts = compiler.compile(exp)
    
    for lesson in artifacts.get("lessons", []):
        storage.save_lesson(lesson)
        print("  Lesson: " + lesson.lesson_id[:12] + "... " + lesson.recommendation[:80])
    for eval_ in artifacts.get("evals", []):
        storage.save_eval(eval_)
        print("  Eval:   " + eval_.eval_id[:12] + "... " + eval_.command)
    
    storage.save_experience(exp)
    print("  Done.")


def cmd_replay(args):
    """orp replay <id>"""
    storage = ORPStorage()
    exp = storage.get_experience(args.id)
    if not exp:
        print("Experience not found: " + args.id)
        return
    replayer = CounterfactualReplayer()
    replay = replayer.replay(
        experience_id=exp.experience_id,
        original="original",
        alternative=args.strategy or "Review trace and write tests first",
    )
    storage.save_replay(replay)
    print("Replay: " + replay.replay_id[:12] + "...")
    print("  Mode:   " + replay.verification_mode)
    print("  Result: " + replay.result.get("status", "unknown"))


def cmd_lessons(args):
    """orp lessons <subcommand>"""
    storage = ORPStorage()
    store = LessonStore(storage)
    
    if args.subcommand == "list":
        status = LessonStatus(args.status) if args.status else None
        lessons = storage.list_lessons(status=status)
        for l in lessons:
            rid = l.lesson_id[:16] + "..."
            print(rid + " " + l.status.value + " " + l.recommendation[:60])
    
    elif args.subcommand == "validate":
        issues = store.validate_lesson(args.id)
        if not issues:
            print("Lesson " + args.id + ": valid")
        else:
            print("Lesson " + args.id + ": issues")
            for i in issues:
                print("  - " + i)
    
    elif args.subcommand == "conflicts":
        defender = ConflictDefender(storage)
        reviewed = defender.auto_review_conflicts()
        if reviewed:
            print("Lessons moved to under_review: " + str(reviewed))
        else:
            print("No conflicts found")
    
    elif args.subcommand == "rollback":
        manager = RollbackManager(storage)
        rollback = manager.rollback(args.id, args.reason or "Manual rollback")
        if rollback:
            print("Lesson " + args.id + ": " + rollback.previous_status.value + " -> " + rollback.new_status.value)
        else:
            print("Lesson not found: " + args.id)
    
    elif args.subcommand == "deliver":
        lesson = storage.get_lesson(args.id)
        if not lesson:
            print("Lesson not found: " + args.id)
            return
        strategy = DeliveryStrategy(args.strategy) if args.strategy else DeliveryStrategy.PROMPT_CONTEXT
        router = DeliveryRouter(storage)
        delivery = router.deliver(lesson, "cli", strategy=strategy, context=args.context)
        print("Delivered: " + delivery.delivery_id[:12] + "... via " + delivery.strategy.value)


def cmd_effects(args):
    """orp effects evaluate <id>"""
    storage = ORPStorage()
    evaluator = EffectEvaluator(storage)
    
    if args.id == "all":
        evals = evaluator.auto_evaluate_all()
        print("Evaluated " + str(len(evals)) + " lessons")
        for e in evals:
            print("  " + e.lesson_id[:12] + "... -> " + e.decision)
    else:
        lesson = storage.get_lesson(args.id)
        if not lesson:
            print("Lesson not found: " + args.id)
            return
        evaluation = evaluator.evaluate_matched_baseline(lesson)
        storage.save_lesson_evaluation(evaluation)
        print("Evaluation: " + evaluation.evaluation_id[:12] + "...")
        print("  Method:   " + evaluation.method.value)
        print("  Decision: " + evaluation.decision)


def cmd_training(args):
    """orp training <subcommand>"""
    storage = ORPStorage()
    pipeline = TrainingPipeline(storage)
    
    if args.subcommand == "candidates":
        candidates = storage.list_training_candidates()
        if not candidates:
            print("No training candidates")
            return
        for c in candidates:
            print(c.candidate_id[:16] + "... " + c.format.value + " " + c.status.value)
    
    elif args.subcommand == "export":
        exported = pipeline.export_approved()
        if not exported:
            print("No approved candidates to export")
            return
        print("Exporting " + str(len(exported)) + " approved candidates")
        for e in exported:
            print("  " + e["candidate_id"][:12] + "...")


def cmd_mcp(args):
    """orp mcp-server"""
    server = MCPServer(transport=args.transport)
    if args.transport == "stdio":
        print("Starting ORP MCP Server (stdio)...", file=sys.stderr)
        server.run_stdio()
    else:
        print("Transport " + args.transport + " not yet implemented")


def cmd_report(args):
    """orp report"""
    storage = ORPStorage()
    reporter = HTMLReporter(storage)
    path = reporter.write_report(args.output or "orp_report.html")
    print("Report written to " + path)
    if args.open:
        import subprocess
        try:
            subprocess.Popen(["start", path], shell=True)
        except Exception:
            pass


def cmd_diff(args):
    """orp diff <id1> <id2>"""
    storage = ORPStorage()
    a = storage.get_experience(args.id1)
    b = storage.get_experience(args.id2)
    if not a or not b:
        print("One or both experiences not found")
        return
    
    a_actions = len([e for e in a.timeline if e.kind == EventKind.ACTION])
    b_actions = len([e for e in b.timeline if e.kind == EventKind.ACTION])
    a_claims = len([e for e in a.timeline if e.kind == EventKind.CLAIM])
    b_claims = len([e for e in b.timeline if e.kind == EventKind.CLAIM])
    a_evidence = sum(len(e.evidence_refs) for e in a.timeline)
    b_evidence = sum(len(e.evidence_refs) for e in b.timeline)
    
    print("Metric                          Before              After")
    print("-" * 60)
    print("Task success                    " + a.outcome.status.ljust(20) + b.outcome.status)
    print("Tool calls                      " + str(a_actions).ljust(20) + str(b_actions))
    print("Claims                          " + str(a_claims).ljust(20) + str(b_claims))
    print("Evidence refs                   " + str(a_evidence).ljust(20) + str(b_evidence))


def cmd_export(args):
    """orp export [id]"""
    storage = ORPStorage()
    engine = ExportEngine(storage)
    content = engine.to_json(args.id)
    if content:
        print(content[:2000])
    else:
        print("Experience not found: " + args.id)


def main():
    parser = argparse.ArgumentParser(description="ORP — Open Reflection Protocol CLI")
    sub = parser.add_subparsers(dest="command")
    
    p = sub.add_parser("wrap", help="Wrap an agent with ORP")
    p.add_argument("command", nargs="+")
    p.add_argument("--goal")
    p.add_argument("--timeout", type=int, default=300)
    p.set_defaults(func=cmd_wrap)
    
    p = sub.add_parser("inspect", help="Inspect an experience")
    p.add_argument("id", default="latest", nargs="?")
    p.set_defaults(func=cmd_inspect)
    
    p = sub.add_parser("learn", help="Generate lessons from an experience")
    p.add_argument("id", default="latest", nargs="?")
    p.set_defaults(func=cmd_learn)
    
    p = sub.add_parser("replay", help="Counterfactual replay")
    p.add_argument("id")
    p.add_argument("--strategy")
    p.set_defaults(func=cmd_replay)
    
    p = sub.add_parser("lessons", help="Manage lessons")
    p.add_argument("subcommand", choices=["list", "validate", "conflicts", "rollback", "deliver"])
    p.add_argument("id", nargs="?", default="")
    p.add_argument("--status")
    p.add_argument("--strategy")
    p.add_argument("--reason")
    p.add_argument("--context")
    p.set_defaults(func=cmd_lessons)
    
    p = sub.add_parser("effects", help="Evaluate lesson effects")
    p.add_argument("subcommand", choices=["evaluate"])
    p.add_argument("id")
    p.set_defaults(func=cmd_effects)
    
    p = sub.add_parser("training", help="Training candidates")
    p.add_argument("subcommand", choices=["candidates", "export"])
    p.set_defaults(func=cmd_training)
    
    p = sub.add_parser("mcp-server", help="Start MCP lesson server")
    p.add_argument("--transport", default="stdio", choices=["stdio", "http"])
    p.set_defaults(func=cmd_mcp)
    
    p = sub.add_parser("report", help="Generate HTML report")
    p.add_argument("--output", default="orp_report.html")
    p.add_argument("--open", action="store_true")
    p.set_defaults(func=cmd_report)
    
    p = sub.add_parser("diff", help="Compare two experiences")
    p.add_argument("id1")
    p.add_argument("id2")
    p.set_defaults(func=cmd_diff)
    
    p = sub.add_parser("export", help="Export an experience")
    p.add_argument("id", default="latest", nargs="?")
    p.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
