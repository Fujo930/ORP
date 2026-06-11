"""
ORP 实战示例：给一个代码审查 Agent 加上反思能力

运行方式: python examples/code_review_with_reflection.py
"""

import json
from reflection_journal import Journal


def code_review_agent(pr_diff: str) -> dict:
    """
    模拟一个代码审查 Agent 的推理过程。
    真实场景中这里会调用 LLM，这里仅做演示。
    """
    # 模拟 LLM 的推理步骤
    reasoning_steps = [
        {
            "type": "hypothesis",
            "content": "PR #42 中 UserController.java 有潜在的 NPE 风险",
            "confidence": 0.6,
            "evidence_refs": ["diff:UserController.java:+15"],
        },
        {
            "type": "action",
            "content": "检查 diff 中 UserController.java 的变更",
            "confidence": 1.0,
        },
        {
            "type": "observation",
            "content": "第 15 行新增了 user.getName() 调用但未做 null 检查",
            "confidence": 1.0,
            "evidence_refs": [
                "diff:UserController.java:+15",
                "diff:UserController.java:+15-20"
            ],
            "parent_step": 2,
        },
        {
            "type": "critique",
            "content": "用户可能在未登录状态下访问此接口，SecurityContext 可能为空",
            "confidence": 0.75,
            "uncertainty": "需要确认该接口的认证配置",
            "parent_step": 3,
        },
        {
            "type": "verification",
            "content": "检查 SecurityConfig.java 中该接口的认证规则",
            "confidence": 1.0,
        },
        {
            "type": "observation",
            "content": "该接口配置为 'permitAll'，未登录用户也可访问",
            "confidence": 1.0,
            "evidence_refs": ["SecurityConfig.java:42"],
            "parent_step": 5,
        },
        {
            "type": "critique",
            "content": "如果接口 permitAll 且未做 null 检查，这确实是一个 NPE",
            "confidence": 0.95,
            "evidence_refs": ["observation@3", "observation@6"],
        },
        {
            "type": "synthesis",
            "content": (
                "建议：在 user.getName() 前添加 Objects.requireNonNull(user, "
                "'User must be authenticated'). 同时考虑是否应限制该接口为 "
                "authenticated-only"
            ),
            "confidence": 0.9,
        },
    ]

    conclusion = (
        "NPE 风险确认。UserController.java:+15 新增的 user.getName() "
        "在没有 null 检查的情况下调用，且接口配置为 permitAll。"
        "建议添加 null 检查并讨论是否应限制接口访问。"
    )

    return {
        "reasoning_steps": reasoning_steps,
        "conclusion": conclusion,
        "risk_level": "high",
    }


def main():
    # 1. 创建日记本
    journal = Journal(agent_id="code_reviewer_v2")

    # 2. 模拟一个 PR 审查请求
    pr_diff = """
    diff --git a/UserController.java b/UserController.java
    +15: String userName = user.getName();  // <-- 潜在 NPE
    """
    pr_number = 42

    # 3. Agent 执行审查
    result = code_review_agent(pr_diff)

    # 4. 记录推理过程
    trace_id = journal.record(
        goal=f"审查 PR #{pr_number} 中的 NPE 风险",
        steps=result["reasoning_steps"],
        conclusion=result["conclusion"],
        metadata={
            "pr_number": pr_number,
            "repo": "moss-fork",
            "risk_level": result["risk_level"],
            "reviewer": "code_reviewer_v2",
        },
    )

    print(f"✅ 推理轨迹已记录: {str(trace_id)[:8]}...")

    # 5. 查看本次推理的验证报告
    trace = journal.storage.get(trace_id)
    if trace and trace.verification:
        v = trace.verification
        print(f"\n📊 验证报告:")
        print(f"   Groundedness:      {v.checks['groundedness']:.2f}")
        print(f"   Validity:           {v.checks['validity']:.2f}")
        print(f"   Coherence:          {v.checks['coherence']:.2f}")
        print(f"   Uncertainty Honesty: {v.checks['uncertainty_honesty']:.2f}")
        print(f"   Passed:             {'✅' if v.passed else '❌'}")

    # 6. 查看反思
    if trace and trace.reflection:
        r = trace.reflection
        print(f"\n💡 反思:")
        print(f"   做得好的: {r.what_went_well}")
        print(f"   可改进:   {r.what_could_improve}")
        print(f"   下次:     {r.next_time}")

    # 7. 模拟多次审查后查看汇总
    print(f"\n📈 运行 3 次模拟审查后...")

    for i in range(2):
        result2 = code_review_agent(f"PR #{pr_number + i + 1}")
        journal.record(
            goal=f"审查 PR #{pr_number + i + 1}",
            steps=result2["reasoning_steps"],
            conclusion=result2["conclusion"],
        )

    # 8. 输出总结
    summary = journal.summarize(limit=5)
    print(f"\n{summary}")


if __name__ == "__main__":
    main()
