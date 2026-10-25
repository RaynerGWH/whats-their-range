"""Local tournament evaluation, independent of the interactive API workers."""

from .policies import POLICIES, Policy, PolicySpec
from .runner import EvaluationConfig, evaluate, run_tournament, save_report

__all__ = ["POLICIES", "Policy", "PolicySpec", "EvaluationConfig", "evaluate", "run_tournament", "save_report"]
