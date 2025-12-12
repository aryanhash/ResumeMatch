# Cline Prompt: Resume Parser Agent

## Objective
Generate a Python agent that parses resumes into **structured, validated** JSON.

---

## Critical Issues to Fix

### Issue #1: No Field Validation
```python
# ❌ WRONG - accepts whatever LLM returns
return ParsedResume(**llm_response)

# ✅ CORRECT - validate required fields
if not parsed.email:
    raise ValueError("Resume must have email address")
if not parsed.experience:
    parsed.warnings.append("No experience section found")
```

### Issue #2: No Date Validation
```python
# ❌ WRONG - accepts any date string
duration = "Recent" or "A while ago"

# ✅ CORRECT - normalize dates
def _normalize_date(self, date_str: str) -> str:
    if re.match(r'\d{4}', date_str):
        return date_str  # Already normalized
    if "present" in date_str.lower() or "current" in date_str.lower():
        return "Present"
    return date_str  # Keep as-is with warning
```

### Issue #3: Skills Not Deduplicated
```python
# ❌ WRONG - keeps duplicates
skills = ["Python", "python", "PYTHON", "Py"]

# ✅ CORRECT - normalize and deduplicate
def _deduplicate_skills(self, skills: List[str]) -> List[str]:
    normalized = {}
    for skill in skills:
        key = skill.lower().strip()
        if key not in normalized:
            normalized[key] = skill.strip()
    return list(normalized.values())
```

---

## Requirements

Write a Python script that:

### 1. Text Preprocessing

```python
def _preprocess(self, text: str) -> str:
    """Clean resume text for parsing."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Fix common OCR/PDF extraction issues
    text = text.replace('•', '-')
    text = text.replace('●', '-')
    text = text.replace('○', '-')
    
    # Truncate if too long (avoid token limits)
    if len(text) > 20000:
        text = text[:20000] + "..."
    
    return text.strip()
```

### 2. Required vs Optional Fields

```python
# REQUIRED - must exist or raise error
required_fields = {
    "name": "Candidate name",
    "email": "Contact email (critical for ATS)",
}

# IMPORTANT - should exist, warn if missing
important_fields = {
    "phone": "Phone number",
    "skills": "Skills section",
    "experience": "Work experience",
}

# OPTIONAL - nice to have
optional_fields = {
    "linkedin": "LinkedIn profile",
    "github": "GitHub profile",
    "summary": "Professional summary",
    "projects": "Personal/side projects",
    "certifications": "Certifications",
}
```

### 3. Experience Extraction

```python
def _extract_experience(self, text: str) -> List[Experience]:
    """Extract work experience with validation."""
    experiences = []
    
    # LLM extraction
    prompt = f"""Extract work experience from this resume.

For each role, extract:
- title: Job title
- company: Company name
- duration: Start - End (e.g., "Jan 2020 - Present")
- description: List of bullet points (3-5 per role)
- skills_used: Technologies/skills mentioned in this role

Validate:
- Dates should be real (1990-2025 range)
- If end date missing, assume "Present"
- Extract minimum 2 bullet points per role

Resume:
{text}

Return JSON array of experience objects."""

    # ... LLM call and parsing
    
    # Validation
    for exp in experiences:
        if not exp.title:
            continue  # Skip invalid entries
        if not exp.description or len(exp.description) < 1:
            exp.description = ["Responsibilities not specified"]
        if not exp.duration:
            exp.duration = "Dates not specified"
    
    return experiences
```

### 4. Skill Extraction and Normalization

```python
SKILL_ALIASES = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "k8s": "Kubernetes",
    "postgres": "PostgreSQL",
    "mongo": "MongoDB",
    "node": "Node.js",
    "react.js": "React",
    "vue.js": "Vue",
}

def _normalize_skills(self, skills: List[str]) -> List[str]:
    """Normalize and deduplicate skills."""
    normalized = {}
    
    for skill in skills:
        skill_clean = skill.strip()
        skill_lower = skill_clean.lower()
        
        # Apply aliases
        if skill_lower in SKILL_ALIASES:
            skill_clean = SKILL_ALIASES[skill_lower]
            skill_lower = skill_clean.lower()
        
        # Deduplicate by lowercase key
        if skill_lower not in normalized:
            normalized[skill_lower] = skill_clean
    
    return sorted(list(normalized.values()))
```

### 5. Validation and Warnings

```python
def _validate_parsed(self, parsed: ParsedResume) -> List[str]:
    """Validate parsed resume and return warnings."""
    warnings = []
    
    # Required field checks
    if not parsed.email:
        warnings.append("CRITICAL: No email address found")
    if not parsed.name:
        warnings.append("CRITICAL: No name found")
    
    # Important field checks
    if not parsed.phone:
        warnings.append("WARNING: No phone number")
    if not parsed.skills:
        warnings.append("WARNING: No skills section - check experience for implicit skills")
    if not parsed.experience:
        warnings.append("WARNING: No work experience found")
    elif len(parsed.experience) < 2:
        warnings.append("INFO: Only one work experience entry")
    
    # Data quality checks
    for exp in parsed.experience:
        if len(exp.description) < 2:
            warnings.append(f"INFO: Few bullets for {exp.title} at {exp.company}")
    
    if len(parsed.skills) > 50:
        warnings.append("INFO: Very long skills list - consider categorizing")
    
    return warnings
```

---

## Output Format

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class Education(BaseModel):
    degree: str
    institution: str
    year: Optional[str] = None
    gpa: Optional[str] = None
    field_of_study: Optional[str] = None

class Experience(BaseModel):
    title: str
    company: str
    duration: str
    description: List[str] = []
    skills_used: List[str] = []

class Project(BaseModel):
    name: str
    description: str
    technologies: List[str] = []
    link: Optional[str] = None
    impact: Optional[str] = None

class ParsedResume(BaseModel):
    name: str
    email: str
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
    raw_text: str = ""  # Keep for validation
    warnings: List[str] = []  # Parsing warnings

class ResumeParserAgent:
    def parse(self, resume_text: str) -> ParsedResume:
        ...
```

---

## Data Flow

```
Raw Resume Text (from PDF/DOCX/TXT)
    ↓
ResumeParserAgent.parse()
    ↓
    1. Preprocess text
    2. Extract with LLM
    3. Normalize skills
    4. Validate fields
    5. Generate warnings
    ↓
ParsedResume (with warnings)
    ↓
Used by: GapAnalysisAgent, ResumeRewriteAgent, CoverLetterAgent
```

---

## Fallback Extraction

```python
def _fallback_parse(self, text: str) -> ParsedResume:
    """Fallback parsing if LLM fails."""
    
    # Extract email
    email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', text)
    email = email_match.group() if email_match else ""
    
    # Extract phone
    phone_match = re.search(r'\+?[\d\s-]{10,}', text)
    phone = phone_match.group().strip() if phone_match else None
    
    # Extract skills from common section headers
    skills = []
    skills_section = re.search(r'(?:SKILLS|TECHNICAL SKILLS)[:\s]*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\Z)', 
                               text, re.IGNORECASE)
    if skills_section:
        skills_text = skills_section.group(1)
        skills = [s.strip() for s in re.split(r'[,|•\n]', skills_text) if s.strip()]
    
    # Extract name (usually first line)
    name = text.split('\n')[0].strip()[:50]
    
    return ParsedResume(
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        raw_text=text,
        warnings=["Used fallback parsing - review for accuracy"]
    )
```

---

## Error Cases

- Empty text → Raise ValueError("Resume text is empty")
- Only whitespace → Raise ValueError("Resume contains no content")
- No email found → Set email="" with CRITICAL warning
- Very short text (<100 chars) → Warning + attempt extraction
- Binary data → Raise ValueError("Invalid text format")
- LLM timeout → Use fallback extraction
