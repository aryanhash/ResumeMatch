"""
AutoApply AI Agents Package

Agents are partially generated using Cline CLI.
OUMI provides fine-tuned ATS classification.
Together AI powers the core intelligence.
"""
from .parse_resume import ResumeParserAgent
from .jd_analyzer import JDAnalyzerAgent  # ← FIXED: Changed from analyze_jd
from .gap_analysis import GapAnalysisAgent
from .skill_agent import SkillAgent
from .oumi_ats_classifier import OumiATSClassifier
from .ats_scorer import ATSScorerAgent
from .resume_rewrite import ResumeRewriteAgent
from .cover_letter import CoverLetterAgent
from .explanation import ExplanationAgent
from .project_recommendations import ProjectRecommendationAgent

__all__ = [
    "ResumeParserAgent",
    "JDAnalyzerAgent", 
    "GapAnalysisAgent",
    "SkillAgent",
    "OumiATSClassifier",
    "ATSScorerAgent",
    "ResumeRewriteAgent",
    "CoverLetterAgent",
    "ExplanationAgent",
    "ProjectRecommendationAgent"
]