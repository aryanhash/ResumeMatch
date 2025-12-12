# AutoApply AI - Agent Data Flow

## Overview

This document describes how data flows between agents in the AutoApply AI pipeline.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT                                      │
│                    Resume (PDF/DOCX/TXT) + Job Description                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STEP 1: PARSING                                    │
│  ┌───────────────────┐         ┌───────────────────┐                        │
│  │  ResumeParser     │         │   JDAnalyzer      │                        │
│  │                   │         │                   │                        │
│  │  Input: text      │         │  Input: text      │                        │
│  │  Output:          │         │  Output:          │                        │
│  │  - ParsedResume   │         │  - ParsedJD       │                        │
│  └───────────────────┘         └───────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
           ParsedResume                           ParsedJobDescription
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STEP 2: ANALYSIS                                     │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │                      GapAnalysisAgent                              │      │
│  │                                                                    │      │
│  │  Input: ParsedResume + ParsedJobDescription                        │      │
│  │  Output: GapAnalysis                                               │      │
│  │    - matching_skills: List[SkillMatch]                            │      │
│  │    - missing_skills: List[SkillGap]                               │      │
│  │    - summary: GapSummary                                          │      │
│  │    - gaps: GapsByCategory                                         │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │                        SkillAgent                                  │      │
│  │                                                                    │      │
│  │  Input: ParsedResume                                               │      │
│  │  Output: SkillEnhancement                                          │      │
│  │    - standardized_skills                                           │      │
│  │    - skill_levels                                                  │      │
│  │    - skill_evidence                                                │      │
│  └───────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STEP 3: SCORING                                      │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │                       ATSScorerAgent                               │      │
│  │                                                                    │      │
│  │  Input: ParsedResume + ParsedJD + GapAnalysis                      │      │
│  │  Output: ATSScore                                                  │      │
│  │    - overall_score: 0-100                                          │      │
│  │    - bucket: STRONG/MODERATE/WEAK/NOT_ATS_FRIENDLY                │      │
│  │    - component scores (skill, keyword, formatting, experience)     │      │
│  │    - issues: List[ATSIssue]                                       │      │
│  │    - recommendations                                               │      │
│  └───────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STEP 4: OPTIMIZATION                                 │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │                    ResumeRewriteAgent                              │      │
│  │                                                                    │      │
│  │  Input: ParsedResume + ParsedJD + GapAnalysis + ATSScore           │      │
│  │  Output: RewrittenResume                                           │      │
│  │    - summary (context-aware)                                       │      │
│  │    - improved_bullets                                              │      │
│  │    - reordered_skills                                              │      │
│  │    - enhanced_experience                                           │      │
│  │    - optimized_sections_order                                      │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │                    CoverLetterAgent                                │      │
│  │                                                                    │      │
│  │  Input: ParsedResume + ParsedJD + GapAnalysis                      │      │
│  │  Output: CoverLetter                                               │      │
│  │    - content                                                       │      │
│  │    - tone                                                          │      │
│  │    - key_highlights                                                │      │
│  │    - match_confidence                                              │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │                  ProjectRecommendationAgent                        │      │
│  │                                                                    │      │
│  │  Input: GapAnalysis                                                │      │
│  │  Output: ProjectRecommendations                                    │      │
│  │    - recommended_projects                                          │      │
│  │    - learning_paths                                                │      │
│  │    - open_source_ideas                                             │      │
│  └───────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT                                          │
│                                                                              │
│  {                                                                           │
│    "parsed_resume": {...},                                                   │
│    "parsed_jd": {...},                                                       │
│    "gap_analysis": {...},                                                    │
│    "ats_score": {...},                                                       │
│    "rewritten_resume": {...},                                                │
│    "cover_letter": {...},                                                    │
│    "project_recommendations": {...}                                          │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Interface Definitions

### ParsedResume → Used by All Agents

```python
class ParsedResume:
    name: str
    email: str
    phone: Optional[str]
    skills: List[str]           # CRITICAL for gap analysis
    experience: List[Experience]
    education: List[Education]
    projects: List[Project]
    certifications: List[str]
    raw_text: str               # Used for text matching
```

### ParsedJobDescription → Used by Gap, ATS, Rewrite

```python
class ParsedJobDescription:
    role: str
    required_skills: List[str]  # CRITICAL - weight 100
    preferred_skills: List[str] # MEDIUM - weight 50
    tools: List[str]            # HIGH - weight 75
    keywords: List[str]         # For ATS matching
    seniority: Seniority
    experience_years: Optional[str]
```

### GapAnalysis → Core Analysis Output

```python
class GapAnalysis:
    # MATCHED
    matching_skills: List[SkillMatch]  # Has .skill, .importance, .confidence
    matching_tools: List[str]
    matching_keywords: List[str]
    
    # MISSING
    missing_skills: List[SkillGap]     # Has .skill, .importance, .category
    missing_tools: List[str]
    missing_keywords: List[str]
    
    # SUMMARY
    summary: GapSummary                # Has .required_match_rate, .overall_readiness
```

### ATSScore → Scoring Output

```python
class ATSScore:
    overall_score: int                 # 0-100, AFTER penalties
    bucket: ATSBucket                  # STRONG/MODERATE/WEAK/NOT_ATS_FRIENDLY
    skill_match_score: int             # Based on REQUIRED skills only
    keyword_score: int
    formatting_score: int
    experience_alignment_score: int
    issues: List[ATSIssue]             # MUST affect score
    recommendations: List[str]
```

---

## Critical Data Dependencies

### ATSScorerAgent REQUIRES:
```
GapAnalysis.matching_skills  → To count required matches
GapAnalysis.missing_skills   → To identify critical gaps
GapAnalysis.missing_skills[].importance = "required"  → For filtering
GapAnalysis.missing_skills[].category = "critical"    → For blocking STRONG
```

### ResumeRewriteAgent REQUIRES:
```
GapAnalysis.matching_skills  → For summary generation
GapAnalysis.missing_skills   → To avoid claiming missing skills
ATSScore.overall_score       → For content strategy
ATSScore.bucket              → For section ordering
```

### CoverLetterAgent REQUIRES:
```
GapAnalysis.matching_skills  → To highlight strengths
GapAnalysis.missing_skills   → For gap handling strategy
```

---

## Score Flow

```
GapAnalysis
    │
    ├── matching_skills (required) ──────┐
    │                                    │
    ├── missing_skills (required) ───────┼──► skill_match_score (40%)
    │                                    │
    ├── matching_keywords ───────────────┼──► keyword_score (20%)
    │                                    │
ParsedResume.sections ───────────────────┼──► formatting_score (20%)
    │                                    │
ParsedResume.experience + JD.role ───────┼──► experience_score (20%)
    │                                    │
    └── (all above) ─────────────────────┴──► base_score
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ Issue Penalties │
                                    │ Critical: -25   │
                                    │ High: -10       │
                                    │ Medium: -5      │
                                    └─────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ Critical Gap    │
                                    │ Check           │
                                    │ (caps at 55)    │
                                    └─────────────────┘
                                              │
                                              ▼
                                        final_score
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ Bucket          │
                                    │ Determination   │
                                    │ (with gap check)│
                                    └─────────────────┘
```

---

## Agent Responsibilities

| Agent | Primary Job | Ethical Constraint |
|-------|------------|-------------------|
| ResumeParser | Extract structured data | Return warnings for missing fields |
| JDAnalyzer | Extract requirements | Filter out buzzwords from keywords |
| GapAnalysis | Match skills honestly | Use multi-strategy matching |
| SkillAgent | Enhance presentation | Never add fake skills |
| ATSScorer | Calculate honest score | Issues must affect score |
| ResumeRewriter | Optimize presentation | Never fabricate experience |
| CoverLetter | Generate personalized letter | Only reference real achievements |
| ProjectRec | Suggest improvements | Real resources, realistic timelines |

---

## Error Propagation

```
ResumeParser fails
    └── Return fallback ParsedResume with warnings
        └── GapAnalysis runs with limited data
            └── ATSScore calculates with available info
                └── Final result includes all warnings
```

Each agent should:
1. Handle upstream errors gracefully
2. Add its own warnings to the chain
3. Never crash the pipeline
4. Return best-effort output

