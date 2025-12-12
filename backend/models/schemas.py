"""
Pydantic schemas for AutoApply AI
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class ATSBucket(str, Enum):
    """Enumeration of ATS score categories"""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NOT_ATS_FRIENDLY = "not_ats_friendly"


class Seniority(str, Enum):
    """Enumeration of job seniority levels"""
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"


# Resume Parser Schemas
class Education(BaseModel):
    """Schema representing an education entry"""
    degree: str
    institution: str
    year: Optional[str] = None
    gpa: Optional[str] = None
    field_of_study: Optional[str] = None


class Experience(BaseModel):
    """Schema representing a work experience entry"""
    title: str
    company: str
    duration: str
    description: List[str]
    skills_used: List[str] = []


class Project(BaseModel):
    """Schema representing a project entry"""
    name: str
    description: str
    technologies: List[str]
    link: Optional[str] = None
    impact: Optional[str] = None


class ParsedResume(BaseModel):
    """Schema for structured resume data"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[Experience] = []
    education: List[Education] = []
    projects: List[Project] = []
    certifications: List[str] = []
    languages: List[str] = []
    raw_text: str = ""


# Job Description Schemas
class ParsedJobDescription(BaseModel):
    """Schema for structured job description data"""
    role: str
    company: Optional[str] = None
    required_skills: List[str]
    preferred_skills: List[str] = []
    tools: List[str] = []
    seniority: Seniority = Seniority.MID
    soft_skills: List[str] = []
    keywords: List[str] = []
    responsibilities: List[str] = []
    qualifications: List[str] = []
    experience_years: Optional[str] = None


# Gap Analysis Schemas
class SkillGap(BaseModel):
    """Schema representing a specific skill gap"""
    skill: str
    importance: str = "required"  # required, preferred
    category: str = "technical"  # technical, soft, tool


class GapAnalysis(BaseModel):
    """Schema for the result of the gap analysis between resume and JD"""
    matching_skills: List[str]
    missing_skills: List[SkillGap]
    matching_tools: List[str]
    missing_tools: List[str]
    matching_keywords: List[str]
    missing_keywords: List[str]
    experience_match: bool
    seniority_match: bool
    overall_match_percentage: float
    strengths: List[str]
    weaknesses: List[str]


# ATS Scoring Schemas
class ATSIssue(BaseModel):
    """Schema representing a specific ATS compatibility issue"""
    category: str
    issue: str
    severity: str  # high, medium, low
    suggestion: str


class ATSScore(BaseModel):
    """Schema for detailed ATS scoring results"""
    overall_score: int = Field(ge=0, le=100)
    bucket: ATSBucket
    skill_match_score: int = Field(ge=0, le=100)
    keyword_score: int = Field(ge=0, le=100)
    formatting_score: int = Field(ge=0, le=100)
    experience_alignment_score: int = Field(ge=0, le=100)
    issues: List[ATSIssue]
    missing_keywords: List[str]
    recommendations: List[str]


# Resume Rewrite Schemas
class ImprovedBulletPoint(BaseModel):
    """Schema for an improved resume bullet point"""
    original: str
    improved: str
    reason: str


class RewrittenResume(BaseModel):
    """Schema for the rewritten/optimized resume"""
    summary: str
    improved_bullets: List[ImprovedBulletPoint]
    reordered_skills: List[str]
    enhanced_experience: List[Experience]
    optimized_sections_order: List[str]
    version_name: str = "ATS Optimized"


# Cover Letter Schema
class CoverLetter(BaseModel):
    """Schema for the generated cover letter"""
    content: str
    tone: str = "professional"
    word_count: int
    key_highlights: List[str]


# Explanation Schema
class ResumeExplanation(BaseModel):
    """Schema for the explanation of AI analysis"""
    recruiter_perspective: str
    ats_breakdown: str
    improvement_areas: List[Dict[str, str]]
    what_stands_out: List[str]
    red_flags: List[str]


# Project Recommendation Schemas
class ProjectRecommendation(BaseModel):
    """Schema for a recommended project"""
    name: str
    description: str
    skills_covered: List[str]
    difficulty: str  # beginner, intermediate, advanced
    estimated_time: str
    resources: List[str]
    github_ideas: List[str] = []


class LearningPath(BaseModel):
    """Schema for a recommended learning path"""
    skill: str
    resources: List[str]
    timeline: str
    projects: List[str]


class ProjectRecommendations(BaseModel):
    """Schema for the collection of project recommendations"""
    recommended_projects: List[ProjectRecommendation]
    learning_paths: List[LearningPath]
    open_source_ideas: List[str]


# Final Output Schema
class AutoApplyResult(BaseModel):
    """Schema for the final aggregated results of the pipeline"""
    parsed_resume: ParsedResume
    parsed_jd: ParsedJobDescription
    gap_analysis: GapAnalysis
    ats_score: ATSScore
    rewritten_resume: RewrittenResume
    cover_letter: CoverLetter
    explanation: ResumeExplanation
    project_recommendations: ProjectRecommendations
    processing_time: float


# API Request/Response Schemas
class ProcessRequest(BaseModel):
    """Schema for processing request"""
    resume_text: str
    job_description: str


class ProcessResponse(BaseModel):
    """Schema for the API response"""
    success: bool
    workflow_id: Optional[str] = None
    result: Optional[AutoApplyResult] = None
    error: Optional[str] = None

