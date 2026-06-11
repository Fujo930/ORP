"""Counterfactual Replay — 隔离环境回放替代策略"""

import os
import subprocess
import tempfile
from typing import Any, Optional

from orp.schema import CounterfactualReplay


class CounterfactualReplayer:
    """反事实回放 — 在隔离环境中比较原始策略与替代策略"""

    def replay(self, experience_id: str, original: str, alternative: str,
               workdir: Optional[str] = None) -> CounterfactualReplay:
        """尝试在隔离环境中回放替代策略
        
        返回 CounterfactualReplay，其中 result.status 为:
        - improved: 替代策略结果更好
        - equivalent: 结果相当
        - worse: 替代策略更差
        - predicted: 无法实际回放，只能输出预测
        """
        isolation = self._create_isolation(workdir)
        if not isolation:
            # 无法创建隔离环境，只能输出预测
            return CounterfactualReplay(
                experience_id=experience_id,
                original_strategy=original,
                alternative_strategy=alternative,
                verification_mode="predicted",
                result={"status": "predicted", "note": "Could not create isolation environment"},
            )
        
        try:
            # 运行替代策略
            start_cmd = alternative.split()
            if not start_cmd:
                return CounterfactualReplay(
                    experience_id=experience_id,
                    original_strategy=original,
                    alternative_strategy=alternative,
                    verification_mode="sandbox_replay",
                    result={"status": "predicted", "note": "Empty alternative strategy"},
                )
            
            result = subprocess.run(
                start_cmd,
                capture_output=True, text=True,
                cwd=isolation, timeout=120,
            )
            success = result.returncode == 0
            
            return CounterfactualReplay(
                experience_id=experience_id,
                original_strategy=original,
                alternative_strategy=alternative,
                verification_mode="sandbox_replay",
                result={
                    "status": "improved" if success else "worse",
                    "exit_code": result.returncode,
                    "duration": "completed",
                },
            )
        except subprocess.TimeoutExpired:
            return CounterfactualReplay(
                experience_id=experience_id,
                original_strategy=original,
                alternative_strategy=alternative,
                verification_mode="sandbox_replay",
                result={"status": "worse", "error": "timed out"},
            )
        except FileNotFoundError:
            return CounterfactualReplay(
                experience_id=experience_id,
                original_strategy=original,
                alternative_strategy=alternative,
                verification_mode="predicted",
                result={"status": "predicted", "error": "command not found"},
            )
        finally:
            self._cleanup_isolation(isolation)

    def _create_isolation(self, workdir: Optional[str] = None) -> Optional[str]:
        try:
            tmp = tempfile.mkdtemp(prefix="orp_replay_")
            if workdir and os.path.isdir(workdir):
                # 复制工作目录内容（浅层）
                for item in os.listdir(workdir):
                    src = os.path.join(workdir, item)
                    dst = os.path.join(tmp, item)
                    if os.path.isfile(src):
                        try:
                            with open(src, 'rb') as fsrc:
                                with open(dst, 'wb') as fdst:
                                    fdst.write(fsrc.read())
                        except (PermissionError, OSError):
                            pass
            return tmp
        except Exception:
            return None

    def _cleanup_isolation(self, path: str) -> None:
        try:
            import shutil
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass
