# Cline Prompt: Gap Analysis Agent

## Objective
Generate a Python agent that performs **intelligent, honest** skill gap analysis between resume and job requirements.

---

## Critical Requirements

### 1. Multi-Strategy Skill Matching

Don't rely on exact string matching. Use multiple strategies:

```python
class SkillMatcher:
    """Multi-strategy skill matching with confidence scores."""
    
    SKILL_EQUIVALENCES = {
        "javascript": ["js", "ecmascript", "es6"],
        "typescript": ["ts"],
        "kubernetes": ["k8s", "kube"],
        "postgresql": ["postgres", "psql"],
        "mongodb": ["mongo"],
        "rest api": ["rest", "restful", "restful api"],
        "microservices": ["microservice", "microservice architecture"],
    }
    
    def match(self, skill: str, resume_skills: List[str], resume_text: str) -> MatchResult:
        """
        Match skill using multiple strategies.
        Returns MatchResult with confidence 0.0-1.0
        """
        skill_lower = skill.lower()
        
        # Strategy 1: Exact match (highest confidence)
        if any(s.lower() == skill_lower for s in resume_skills):
            return MatchResult(skill=skill, confidence=1.0, reason="exact_match")
        
        # Strategy 2: Equivalence match
        for canonical, equivalents in self.SKILL_EQUIVALENCES.items():
            if skill_lower == canonical or skill_lower in equivalents:
                all_variants = [canonical] + equivalents
                if any(v in [s.lower() for s in resume_skills] for v in all_variants):
                    return MatchResult(skill=skill, confidence=0.95, reason="equivalence")
        
        # Strategy 3: Text appearance (word boundary)
        pattern = r'\b' + re.escape(skill_lower) + r'\b'
        if re.search(pattern, resume_text.lower()):
            return MatchResult(skill=skill, confidence=0.85, reason="text_appearance")
        
        # Strategy 4: Partial match (lower confidence)
        for resume_skill in resume_skills:
            if skill_lower in resume_skill.lower() or resume_skill.lower() in skill_lower:
                return MatchResult(skill=skill, confidence=0.70, reason="partial_match")
        
        # Strategy 5: Semantic similarity (requires embeddings)
        # similarity = self.model.similarity(skill, resume_skills)
        # if similarity > 0.8:
        #     return MatchResult(skill=skill, confidence=similarity, reason="semantic")
        
        return MatchResult(skill=skill, confidence=0.0, reason="no_match")
```

### 2. Skill Criticality Framework

Not all skills are equal. Categorize by importance:

```python
class SkillCriticality:
    CRITICAL = 3    # Core tech stack (Python for Python role)
    HIGH = 2        # Required skills
    MEDIUM = 1      # Preferred skills
    LOW = 0.5       # Nice-to-have

    @classmethod
    def determine(cls, skill: str, jd: ParsedJobDescription) -> float:
        skill_lower = skill.lower()
        
        # Critical: In required AND matches role
        if skill_lower in [s.lower() for s in jd.required_skills]:
            role_lower = jd.role.lower()
            if skill_lower in role_lower:
                return cls.CRITICAL
            return cls.HIGH
        
        # Medium: In preferred skills
        if skill_lower in [s.lower() for s in jd.preferred_skills]:
            return cls.MEDIUM
        
        # Low: In tools or keywords
        return cls.LOW
```

### 3. Honest Gap Categorization

```python
def categorize_gaps(self, missing_skills: List[SkillGap]) -> dict:
    """Categorize gaps by severity with honest assessment."""
    
    critical = [s for s in missing_skills if s.criticality == "critical"]
    high = [s for s in missing_skills if s.criticality == "high"]
    medium = [s for s in missing_skills if s.criticality == "medium"]
    low = [s for s in missing_skills if s.criticality == "low"]
    
    return {
        "critical_gaps": critical,      # Must have - blocking
        "high_priority": high,          # Should have - significant
        "medium_priority": medium,      # Nice to have
        "low_priority": low,            # Optional
        "total_gaps": len(missing_skills),
        "blocking_gaps": len(critical) + len(high),
    }
```

### 4. Readiness Assessment

```python
def assess_readiness(self, matching: List, missing: List) -> str:
    """Honest assessment of job readiness."""
    
    if not missing:
        return "strong_fit"
    
    critical_missing = [s for s in missing if s.criticality == "critical"]
    high_missing = [s for s in missing if s.criticality == "high"]
    
    match_rate = len(matching) / (len(matching) + len(missing))
    
    if critical_missing:
        return "not_ready"  # Missing core requirements
    
    if match_rate >= 0.8 and len(high_missing) <= 1:
        return "ready"
    elif match_rate >= 0.6:
        return "moderately_ready"
    elif match_rate >= 0.4:
        return "needs_preparation"
    else:
        return "not_ready"
```

---

## Output Format

```python
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class SkillImportance(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"

class SkillCategory(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SkillMatch(BaseModel):
    skill: str
    importance: SkillImportance
    reason: str  # How it was matched
    confidence: float  # 0.0-1.0

class SkillGap(BaseModel):
    skill: str
    importance: SkillImportance
    category: SkillCategory
    reason: str  # Why it's missing

class GapSummary(BaseModel):
    required_match_rate: float
    preferred_match_rate: float
    overall_readiness: str

class GapsByCategory(BaseModel):
    critical: List[SkillGap]
    high_priority: List[SkillGap]
    medium_priority: List[SkillGap]
    low_priority: List[SkillGap]
    missing_tools: List[str]
    missing_keywords: List[str]

class GapAnalysis(BaseModel):
    # Matched items
    matching_skills: List[SkillMatch]
    matching_tools: List[str]
    matching_keywords: List[str]
    
    # Missing items
    missing_skills: List[SkillGap]
    missing_tools: List[str]
    missing_keywords: List[str]
    
    # Categorized gaps
    gaps: GapsByCategory
    
    # Assessment
    summary: GapSummary
    experience_match: bool
    seniority_match: bool
    
    # Insights
    strengths: List[str]
    weaknesses: List[str]
    action_plan: List[str]

class GapAnalysisAgent:
    def analyze(self, resume: ParsedResume, jd: ParsedJobDescription) -> GapAnalysis:
        ...
```

---

## Data Flow

```
ParsedResume + ParsedJobDescription
    ↓
GapAnalysisAgent.analyze()
    ↓
    1. Match required skills (multi-strategy)
    2. Match preferred skills
    3. Match tools
    4. Match keywords
    5. Check experience alignment
    6. Check seniority alignment
    7. Categorize gaps
    8. Assess readiness
    9. Generate insights
    ↓
GapAnalysis
    ↓
Used by: ATSScorerAgent, ResumeRewriteAgent, CoverLetterAgent, ProjectRecommendationAgent
```

---

## Matching Algorithm

```python
def analyze(self, resume: ParsedResume, jd: ParsedJobDescription) -> GapAnalysis:
    matcher = SkillMatcher()
    
    matching_skills = []
    missing_skills = []
    
    # 1. Match REQUIRED skills (most important)
    for skill in jd.required_skills:
        result = matcher.match(skill, resume.skills, resume.raw_text)
        
        if result.confidence >= 0.7:  # Threshold for "matched"
            matching_skills.append(SkillMatch(
                skill=skill,
                importance=SkillImportance.REQUIRED,
                reason=result.reason,
                confidence=result.confidence
            ))
        else:
            # Determine criticality
            category = SkillCategory.CRITICAL if skill.lower() in jd.role.lower() else SkillCategory.HIGH
            missing_skills.append(SkillGap(
                skill=skill,
                importance=SkillImportance.REQUIRED,
                category=category,
                reason=result.reason
            ))
    
    # 2. Match PREFERRED skills
    for skill in jd.preferred_skills:
        result = matcher.match(skill, resume.skills, resume.raw_text)
        
        if result.confidence >= 0.7:
            matching_skills.append(SkillMatch(
                skill=skill,
                importance=SkillImportance.PREFERRED,
                reason=result.reason,
                confidence=result.confidence
            ))
        else:
            missing_skills.append(SkillGap(
                skill=skill,
                importance=SkillImportance.PREFERRED,
                category=SkillCategory.MEDIUM,
                reason=result.reason
            ))
    
    # 3. Match tools
    # ... similar logic
    
    # 4. Calculate rates
    required_total = len(jd.required_skills)
    required_matched = len([s for s in matching_skills if s.importance == SkillImportance.REQUIRED])
    required_rate = (required_matched / required_total * 100) if required_total > 0 else 100
    
    # 5. Generate assessment
    readiness = self._assess_readiness(matching_skills, missing_skills)
    
    return GapAnalysis(
        matching_skills=matching_skills,
        missing_skills=missing_skills,
        # ... rest of fields
        summary=GapSummary(
            required_match_rate=required_rate,
            preferred_match_rate=preferred_rate,
            overall_readiness=readiness
        )
    )
```

---

## Safety & Ethics

- Be HONEST about gaps - don't hide critical mismatches
- Use confidence scores - don't claim 100% certainty
- Categorize realistically - critical gaps should be flagged
- Provide actionable insights - not just "you're missing X"

---

## Error Cases

- Empty JD skills → Return with warning, focus on keywords
- No resume skills → Extract from experience, warn about ATS
- All skills missing → Flag as "not_ready", provide learning path
- Semantic matching fails → Fall back to text matching

