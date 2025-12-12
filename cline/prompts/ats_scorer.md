# Cline Prompt: ATS Scoring Agent

## Objective
Generate a Python agent that calculates **accurate, honest** ATS compatibility scores.

---

## Critical Issues to Fix
These bugs existed in previous implementations and MUST be avoided:

### Bug #1: Wrong Match Ratio Calculation
```python
# ❌ WRONG - mixes required with preferred
matched_count = len(gap_analysis.matching_skills)  # Includes ALL matches!
missing_required = [s for s in gap_analysis.missing_skills if s.importance == "required"]
total_required = matched_count + len(missing_required)  # Wrong denominator!
match_ratio = matched_count / total_required  # Inflated!

# ✅ CORRECT - only count required skills
required_matched = [s for s in gap_analysis.matching_skills 
                   if hasattr(s, 'importance') and s.importance == "required"]
required_missing = [s for s in gap_analysis.missing_skills 
                   if s.importance == "required"]
total_required = len(required_matched) + len(required_missing)
match_ratio = len(required_matched) / total_required if total_required > 0 else 0
```

### Bug #2: Issues Not Affecting Score
```python
# ❌ WRONG - identifies issues but doesn't apply penalties
issues = self._identify_issues(...)
return ATSScore(overall_score=base_score, issues=issues)  # Issues ignored!

# ✅ CORRECT - apply penalties for issues
issues = self._identify_issues(...)
penalty = sum(25 if i.severity == "critical" else 10 if i.severity == "high" else 5 
              for i in issues)
final_score = max(0, base_score - penalty)
```

### Bug #3: Critical Skills Not Blocking
```python
# ❌ WRONG - score 85 even if missing Python (critical skill)
if score >= 80:
    bucket = "STRONG"

# ✅ CORRECT - cap score if critical skills missing
if missing_critical_skills:
    final_score = min(final_score, 55)  # Can't be STRONG without critical skills
    bucket = "MODERATE" if final_score >= 50 else "WEAK"
```

---

## Requirements

Write a Python script that:

### 1. Input Validation
- Accepts `ParsedResume`, `ParsedJobDescription`, and `GapAnalysis`
- Validates all inputs are non-None
- Handles empty skill lists gracefully

### 2. Component Score Calculation

#### skill_match_score (0-100)
```
Match ONLY against required_skills:
- 80%+ required matched = 85-100 points
- 60-79% matched = 65-84 points  
- 40-59% matched = 45-64 points
- <40% matched = 0-44 points

SEPARATELY add bonus for preferred skills:
- Each matched preferred = +2 points (max +10)

DO NOT mix required and preferred in the same calculation.
```

#### keyword_score (0-100)
```
Count JD keywords found in resume:
- 80%+ keywords = 90-100
- 60-79% = 70-89
- 40-59% = 50-69
- <40% = 0-49

Minimum score = 0 (not 40!)
```

#### formatting_score (0-100)
```
AWARD points for presence (don't deduct for absence):
- Has skills section: +20
- Has experience section: +20
- Has education section: +10
- Has contact info (email): +15
- Has contact info (phone): +10
- Has summary: +10
- Has projects: +10
- Clean structure: +5

Total possible: 100
```

#### experience_alignment_score (0-100)
```
Check experience RELEVANCE to role:
- Extract keywords from JD role title
- Check if resume experience titles match
- Check years are appropriate for seniority

Senior role + 1 year experience = LOW score
Junior role + 5+ years = HIGH score (overqualified but not blocked)
```

### 3. Issue Identification

```python
def _identify_issues(self, resume, jd, gap_analysis) -> List[ATSIssue]:
    issues = []
    
    # Critical: Missing required skills
    for skill in gap_analysis.missing_skills:
        if skill.importance == "required":
            issues.append(ATSIssue(
                category="skills",
                issue=f"Missing required skill: {skill.skill}",
                severity="critical" if skill.category == "critical" else "high",
                suggestion=f"Add {skill.skill} to skills or show experience with it"
            ))
    
    # High: Missing contact info
    if not resume.email:
        issues.append(ATSIssue(
            category="contact",
            issue="No email address",
            severity="high",
            suggestion="Add professional email address"
        ))
    
    # Medium: Experience mismatch
    if jd.seniority.value == "senior" and len(resume.experience) < 3:
        issues.append(ATSIssue(
            category="experience",
            issue="Limited experience for senior role",
            severity="medium",
            suggestion="Highlight leadership and complex projects"
        ))
    
    return issues
```

### 4. Score Calculation with Penalties

```python
def score(self, resume, jd, gap_analysis) -> ATSScore:
    # 1. Calculate base component scores
    skill_score = self._calculate_skill_score(gap_analysis)
    keyword_score = self._calculate_keyword_score(gap_analysis)
    formatting_score = self._calculate_formatting_score(resume)
    experience_score = self._calculate_experience_score(resume, jd)
    
    # 2. Calculate weighted base score
    base_score = int(
        skill_score * 0.40 +      # Skills most important
        keyword_score * 0.20 +
        formatting_score * 0.20 +
        experience_score * 0.20
    )
    
    # 3. Identify issues FIRST
    issues = self._identify_issues(resume, jd, gap_analysis)
    
    # 4. Apply penalties
    penalty = 0
    for issue in issues:
        if issue.severity == "critical":
            penalty += 25
        elif issue.severity == "high":
            penalty += 10
        elif issue.severity == "medium":
            penalty += 5
    
    final_score = max(0, base_score - penalty)
    
    # 5. Check for critical skill gaps (blocks STRONG bucket)
    missing_critical = [s for s in gap_analysis.missing_skills 
                       if s.importance == "required" and s.category == "critical"]
    if missing_critical:
        final_score = min(final_score, 55)
    
    # 6. Determine bucket AFTER all adjustments
    bucket = self._determine_bucket(final_score, bool(missing_critical))
    
    return ATSScore(
        overall_score=final_score,
        bucket=bucket,
        skill_match_score=skill_score,
        keyword_score=keyword_score,
        formatting_score=formatting_score,
        experience_alignment_score=experience_score,
        issues=issues,
        recommendations=self._get_recommendations(issues)
    )
```

### 5. Bucket Determination

```python
def _determine_bucket(self, score: int, has_critical_gaps: bool) -> ATSBucket:
    if has_critical_gaps:
        return ATSBucket.MODERATE if score >= 50 else ATSBucket.WEAK
    
    if score >= 80:
        return ATSBucket.STRONG
    elif score >= 60:
        return ATSBucket.MODERATE
    elif score >= 40:
        return ATSBucket.WEAK
    else:
        return ATSBucket.NOT_ATS_FRIENDLY
```

---

## Output Format

```python
from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class ATSBucket(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NOT_ATS_FRIENDLY = "not_ats_friendly"

class ATSIssue(BaseModel):
    category: str  # skills, contact, experience, formatting
    issue: str
    severity: str  # critical, high, medium, low
    suggestion: str

class ATSScore(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    bucket: ATSBucket
    skill_match_score: int = Field(ge=0, le=100)
    keyword_score: int = Field(ge=0, le=100)
    formatting_score: int = Field(ge=0, le=100)
    experience_alignment_score: int = Field(ge=0, le=100)
    issues: List[ATSIssue]
    missing_keywords: List[str]
    recommendations: List[str]

class ATSScorerAgent:
    def score(self, resume: ParsedResume, jd: ParsedJobDescription, 
              gap_analysis: GapAnalysis) -> ATSScore:
        ...
```

---

## Data Flow

```
GapAnalysis (from gap_analysis.py)
    ↓
    - matching_skills: List[SkillMatch]  # Has .skill and .importance
    - missing_skills: List[SkillGap]     # Has .skill, .importance, .category
    ↓
ATSScorerAgent.score()
    ↓
ATSScore (to frontend)
```

---

## Safety & Ethics

- NEVER inflate scores to make resume look better
- Issues MUST affect the final score
- Critical skill gaps MUST block STRONG bucket
- Be honest about weaknesses
- Recommendations should be actionable

---

## Error Cases

- Empty skills list → Return 0 skill_match_score, flag issue
- No experience → Return low experience_score, flag issue
- Malformed input → Raise ValueError with clear message
- LLM failure → Use rule-based fallback (no LLM needed for scoring)
