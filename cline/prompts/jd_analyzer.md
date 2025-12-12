# Cline Prompt: Job Description Analyzer Agent

## Objective
Generate a Python agent that extracts **structured, ATS-focused** requirements from job descriptions.

---

## Critical Issues to Fix

### Issue #1: Keywords Too Vague
```python
# ❌ WRONG - returns company mission words
keywords = ["sustainability", "innovation", "empower", "transform"]

# ✅ CORRECT - returns ATS-matchable technical terms
keywords = ["Python", "FastAPI", "MongoDB", "Microservices", "REST API"]
```

### Issue #2: Broken Skill Extraction
```python
# ❌ WRONG - regex matches too much
SKILL_PATTERNS = r'(?:proficiency|experience|knowledge).{0,50}(?:in|with|of)\s*(.+?)(?:\.|,|and)'
# Matches: "experience in transforming agriculture" → extracts "transforming agriculture"

# ✅ CORRECT - use known skill vocabulary
KNOWN_SKILLS = ["Python", "JavaScript", "FastAPI", "Django", "MongoDB", ...]
found_skills = [skill for skill in KNOWN_SKILLS if skill.lower() in jd_text.lower()]
```

### Issue #3: Seniority Not Inferred from Years
```python
# ❌ WRONG - expects LLM to always return seniority
seniority = parsed_data.get("seniority", "mid")  # Falls back to mid always

# ✅ CORRECT - infer from experience_years
def _infer_seniority(experience_years: str) -> Seniority:
    if "1-2" in experience_years or "1+" in experience_years:
        return Seniority.JUNIOR
    elif "3-5" in experience_years or "3+" in experience_years:
        return Seniority.MID
    elif "5+" in experience_years or "7+" in experience_years:
        return Seniority.SENIOR
    return Seniority.MID
```

---

## Requirements

Write a Python script that:

### 1. Text Preprocessing
```python
def _clean_and_truncate(self, jd_text: str, max_chars: int = 15000) -> str:
    """
    Clean and truncate JD text.
    KEEP the LAST max_chars (requirements are usually at the end).
    """
    jd_text = re.sub(r'\s+', ' ', jd_text).strip()
    if len(jd_text) > max_chars:
        # Keep end, not beginning (requirements at end)
        jd_text = "..." + jd_text[-max_chars:]
    return jd_text
```

### 2. LLM Extraction with Clear Prompt

```python
prompt = f"""Extract structured data from this job description.

Return JSON:
{{
    "role": "Job Title",
    "company": "Company Name or null",
    "required_skills": ["skill1", "skill2"],
    "preferred_skills": ["skill1", "skill2"],
    "tools": ["tool1", "tool2"],
    "seniority": "entry|junior|mid|senior|lead|principal",
    "soft_skills": ["communication", "teamwork"],
    "keywords": ["keyword1", "keyword2"],
    "responsibilities": ["responsibility1"],
    "qualifications": ["qualification1"],
    "experience_years": "3-5 years" or null
}}

CRITICAL - Keywords Rules:
✅ INCLUDE: Programming languages, frameworks, databases, cloud platforms,
            development methodologies, architecture patterns, specific tools
✅ EXAMPLES: Python, FastAPI, MongoDB, AWS, Kubernetes, Microservices, Agile

❌ EXCLUDE: Company mission words (sustainability, innovation, transform)
❌ EXCLUDE: Industry buzzwords (agriculture, farming, empower)
❌ EXCLUDE: Generic words (opportunities, challenges, solutions)

Job Description:
{jd_text}

Return ONLY valid JSON."""
```

### 3. Validation and Normalization

```python
def _validate_and_normalize(self, data: dict) -> dict:
    """Ensure all fields have correct types and values."""
    
    # Ensure lists are lists
    for field in ["required_skills", "preferred_skills", "tools", 
                  "keywords", "soft_skills", "responsibilities", "qualifications"]:
        if not isinstance(data.get(field), list):
            data[field] = []
    
    # Normalize seniority
    valid_seniorities = ["entry", "junior", "mid", "senior", "lead", "principal"]
    if data.get("seniority") not in valid_seniorities:
        data["seniority"] = self._infer_seniority(data.get("experience_years", ""))
    
    # Clean skills (remove duplicates, standardize)
    data["required_skills"] = list(set(s.strip() for s in data["required_skills"]))
    data["preferred_skills"] = list(set(s.strip() for s in data["preferred_skills"]))
    
    # Filter out bad keywords
    bad_keywords = {"sustainability", "innovation", "transform", "empower", 
                    "opportunities", "challenges", "solutions", "agriculture"}
    data["keywords"] = [k for k in data["keywords"] 
                       if k.lower() not in bad_keywords]
    
    return data
```

### 4. Fallback Skill Extraction

```python
KNOWN_SKILLS = [
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust",
    "React", "Vue", "Angular", "FastAPI", "Django", "Flask", "Express",
    "PostgreSQL", "MongoDB", "Redis", "MySQL", "DynamoDB",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
    "Git", "CI/CD", "Jenkins", "GitHub Actions",
    "REST API", "GraphQL", "gRPC", "Microservices",
    "Agile", "Scrum", "Kanban"
]

def _extract_skills_fallback(self, jd_text: str) -> List[str]:
    """Extract skills using known vocabulary when LLM fails."""
    jd_lower = jd_text.lower()
    found = []
    
    for skill in KNOWN_SKILLS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, jd_lower):
            found.append(skill)
    
    return found
```

---

## Output Format

```python
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class Seniority(str, Enum):
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"

class ParsedJobDescription(BaseModel):
    role: str
    company: Optional[str] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    tools: List[str] = []
    seniority: Seniority = Seniority.MID
    soft_skills: List[str] = []
    keywords: List[str] = []  # ONLY technical/ATS keywords
    responsibilities: List[str] = []
    qualifications: List[str] = []
    experience_years: Optional[str] = None

class JDAnalyzerAgent:
    def analyze(self, jd_text: str) -> ParsedJobDescription:
        ...
```

---

## Data Flow

```
Raw JD Text
    ↓
JDAnalyzerAgent.analyze()
    ↓
ParsedJobDescription
    ↓
Used by: GapAnalysisAgent, ATSScorerAgent, CoverLetterAgent
```

---

## Keywords - What to Include/Exclude

### ✅ INCLUDE (Technical/ATS Keywords)
- Programming languages: Python, JavaScript, Java, Go
- Frameworks: React, FastAPI, Django, Spring
- Databases: PostgreSQL, MongoDB, Redis
- Cloud: AWS, Azure, GCP, Docker, Kubernetes
- Methodologies: Agile, Scrum, TDD, CI/CD
- Architectures: Microservices, REST, GraphQL

### ❌ EXCLUDE (Not ATS Keywords)
- Company values: innovation, sustainability, transformation
- Industry terms: agriculture, farming, healthcare (unless technical)
- Generic business: opportunities, challenges, solutions, empower
- Soft descriptions: passionate, dynamic, fast-paced

---

## Error Cases

- Empty JD → Return minimal ParsedJobDescription with role="Unknown"
- LLM returns invalid JSON → Log error, use fallback extraction
- Very short JD (<100 chars) → Flag as incomplete, extract what's possible
- Foreign language JD → Attempt extraction, may have limited results
