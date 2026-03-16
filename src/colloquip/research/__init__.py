"""Research subsystem: autonomous research loops, hypothesis generation, and evaluation."""

from colloquip.research.hypothesis_generator import HypothesisGenerator
from colloquip.research.loop import ResearchLoopRunner
from colloquip.research.synthesis_evaluator import SynthesisEvaluator

__all__ = [
    "HypothesisGenerator",
    "ResearchLoopRunner",
    "SynthesisEvaluator",
]
