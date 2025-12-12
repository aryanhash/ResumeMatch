# Cline Prompt: Skill Enhancement Agent

## Objective
Generate a Python agent that **ethically** enhances and clarifies skill representation.

---

## CRITICAL ETHICAL RULES

This agent exists to CLARIFY and ORGANIZE skills, NOT to add fake ones.

### ✅ ALLOWED
- Standardize skill names (JS → JavaScript)
- Deduplicate skills
- Categorize skills logically
- Extract skills from experience descriptions
- Identify skill levels from context
- Suggest clearer presentation

### ❌ FORBIDDEN
- Add skills not in resume
- Invent certifications
- Claim expertise without evidence
- Inflate skill levels
- Fabricate experience with skills

---

## Requirements

### 1. Skill Standardization

```python
SKILL_SYNONYMS = {
    "javascript": ["js", "javascript", "ecmascript", "es6"],
    "typescript": ["ts", "typescript"],
    "kubernetes": ["k8s", "kubernetes", "kube"],
    "postgresql": ["postgres", "postgresql", "psql", "pg"],
    "mongodb": ["mongo", "mongodb"],
    "react": ["react", "reactjs", "react.js"],
    "nodejs": ["node", "nodejs", "node.js"],
    "fastapi": ["fastapi", "fast api"],
    "rest api": ["rest", "restful", "rest api"],
    "ci/cd": ["cicd", "ci/cd", "continuous integration"],
}

def _standardize_skills(self, skills: List[str]) -> List[str]:
    """Normalize and deduplicate skills."""
    
    # Build reverse lookup
    synonym_to_canonical = {}
    for canonical, synonyms in SKILL_SYNONYMS.items():
        for syn in synonyms:
            synonym_to_canonical[syn.lower()] = canonical.title()
    
    normalized = {}
    for skill in skills:
        skill_lower = skill.lower().strip()
        
        # Apply standardization
        if skill_lower in synonym_to_canonical:
            standard = synonym_to_canonical[skill_lower]
        else:
            standard = skill.strip()
        
        # Deduplicate
        if standard.lower() not in normalized:
            normalized[standard.lower()] = standard
    
    return sorted(normalized.values())
```

### 2. Skill Level Extraction

```python
LEVEL_PATTERNS = {
    "expert": [
        r"expert\s+in", r"mastery\s+of", r"deep\s+knowledge",
        r"extensive\s+experience", r"\d+\+?\s*years.*experience"
    ],
    "advanced": [
        r"advanced", r"proficient\s+in", r"strong\s+skills?",
        r"solid\s+experience", r"led\s+development"
    ],
    "intermediate": [
        r"experience\s+with", r"worked\s+with", r"developed\s+using",
        r"built", r"implemented"
    ],
    "beginner": [
        r"learning", r"exploring", r"basic\s+knowledge",
        r"familiar\s+with", r"exposure\s+to"
    ],
}

def _extract_skill_levels(self, resume: ParsedResume) -> Dict[str, str]:
    """Extract skill levels from resume language."""
    
    levels = {}
    text_lower = resume.raw_text.lower()
    
    # Include experience descriptions
    for exp in resume.experience:
        text_lower += " " + " ".join(exp.description).lower()
    
    for skill in resume.skills:
        skill_lower = skill.lower()
        detected_level = "intermediate"  # Default
        
        for level, patterns in LEVEL_PATTERNS.items():
            for pattern in patterns:
                # Check pattern near skill
                full_pattern = pattern + r'.*?' + re.escape(skill_lower)
                alt_pattern = re.escape(skill_lower) + r'.*?' + pattern
                
                if re.search(full_pattern, text_lower) or re.search(alt_pattern, text_lower):
                    detected_level = level
                    break
            
            if detected_level != "intermediate":
                break
        
        levels[skill] = detected_level
    
    return levels
```

### 3. Experience-Based Skill Extraction

```python
VALID_SKILL_PATTERNS = [
    r'\b(python|javascript|typescript|java|go|rust|ruby|php)\b',
    r'\b(react|vue|angular|fastapi|django|flask|express|spring)\b',
    r'\b(postgresql|mongodb|redis|mysql|dynamodb)\b',
    r'\b(docker|kubernetes|aws|azure|gcp|terraform)\b',
    r'\b(git|github|linux|nginx|jenkins)\b',
    r'\b(leadership|mentoring|communication|teamwork)\b',
]

def _extract_from_experience(self, resume: ParsedResume) -> List[str]:
    """Extract skills from experience that aren't in skills list."""
    
    existing = {s.lower() for s in resume.skills}
    found = set()
    
    # Compile experience text
    exp_text = ""
    for exp in resume.experience:
        exp_text += " " + exp.title + " "
        exp_text += " ".join(exp.description) + " "
        for skill in exp.skills_used:
            if skill.lower() not in existing:
                found.add(self._standardize_single(skill))
    
    # Add project technologies
    for proj in resume.projects:
        for tech in proj.technologies:
            if tech.lower() not in existing:
                found.add(self._standardize_single(tech))
    
    # Pattern-based extraction
    exp_lower = exp_text.lower()
    for pattern in VALID_SKILL_PATTERNS:
        matches = re.findall(pattern, exp_lower, re.IGNORECASE)
        for match in matches:
            standard = self._standardize_single(match)
            if standard.lower() not in existing:
                found.add(standard)
    
    return sorted(list(found))
```

### 4. Skill Categorization

```python
SKILL_CATEGORIES = {
    "Programming Languages": [
        "python", "javascript", "typescript", "java", "go", "rust", "ruby"
    ],
    "Frontend Frameworks": [
        "react", "vue", "angular", "svelte", "next.js"
    ],
    "Backend Frameworks": [
        "fastapi", "django", "flask", "express", "spring", "nodejs"
    ],
    "Databases": [
        "postgresql", "mongodb", "redis", "mysql", "sqlite"
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform"
    ],
    "Tools": [
        "git", "github", "linux", "nginx", "jenkins", "ci/cd"
    ],
    "Soft Skills": [
        "leadership", "communication", "mentoring", "teamwork"
    ],
}

def _categorize_skills(self, skills: List[str]) -> Dict[str, List[str]]:
    """Categorize skills into logical groups."""
    
    categorized = {cat: [] for cat in SKILL_CATEGORIES}
    categorized["Other"] = []
    
    for skill in skills:
        skill_lower = skill.lower()
        found = False
        
        for category, category_skills in SKILL_CATEGORIES.items():
            if skill_lower in category_skills:
                categorized[category].append(skill)
                found = True
                break
        
        if not found:
            categorized["Other"].append(skill)
    
    # Remove empty categories
    return {k: sorted(v) for k, v in categorized.items() if v}
```

### 5. Skill-Experience Alignment Check

```python
def _check_alignment(self, resume: ParsedResume) -> List[dict]:
    """Check if claimed skills match experience."""
    
    warnings = []
    exp_count = len(resume.experience)
    
    SENIOR_SKILLS = {
        "leadership": 3,
        "system architecture": 4,
        "technical leadership": 4,
        "mentoring": 3,
    }
    
    for skill in resume.skills:
        skill_lower = skill.lower()
        
        for senior_skill, min_exp in SENIOR_SKILLS.items():
            if senior_skill in skill_lower and exp_count < min_exp:
                warnings.append({
                    "skill": skill,
                    "warning": f"Claims '{skill}' but has {exp_count} experience entries",
                    "suggestion": "Consider rephrasing to match experience level",
                    "severity": "medium"
                })
    
    return warnings
```

### 6. Evidence Gathering

```python
def _gather_evidence(self, resume: ParsedResume, skills: List[str]) -> Dict[str, List[str]]:
    """Gather evidence for each skill from resume."""
    
    evidence = {}
    
    for skill in skills:
        skill_lower = skill.lower()
        skill_evidence = []
        
        # Check experience
        for exp in resume.experience:
            exp_text = f"{exp.title} at {exp.company}: " + " | ".join(exp.description)
            if skill_lower in exp_text.lower():
                for desc in exp.description:
                    if skill_lower in desc.lower():
                        skill_evidence.append(f"Experience: {desc[:80]}...")
                        break
                else:
                    skill_evidence.append(f"Role: {exp.title} at {exp.company}")
        
        # Check projects
        for proj in resume.projects:
            if skill_lower in proj.description.lower() or \
               skill_lower in [t.lower() for t in proj.technologies]:
                skill_evidence.append(f"Project: {proj.name}")
        
        # Check certifications
        for cert in resume.certifications:
            if skill_lower in cert.lower():
                skill_evidence.append(f"Certification: {cert}")
        
        evidence[skill] = skill_evidence[:3] if skill_evidence else ["Listed in skills"]
    
    return evidence
```

### 7. Main Enhancement Method

```python
def enhance_skills(self, resume: ParsedResume) -> dict:
    """
    Enhance skill representation ethically.
    
    Returns comprehensive skill analysis with evidence.
    """
    
    # Standardize existing skills
    standardized = self._standardize_skills(resume.skills)
    
    # Extract skill levels
    skill_levels = self._extract_skill_levels(resume)
    
    # Extract from experience
    experience_skills = self._extract_from_experience(resume)
    
    # Combine and categorize
    all_skills = list(set(standardized + experience_skills))
    categorized = self._categorize_skills(all_skills)
    
    # Check alignment
    alignment_warnings = self._check_alignment(resume)
    
    # Gather evidence
    evidence = self._gather_evidence(resume, all_skills)
    
    return {
        "standardized_skills": all_skills,
        "skill_categories": categorized,
        "skill_levels": skill_levels,
        "skills_from_experience": experience_skills,
        "skill_evidence": evidence,
        "alignment_warnings": alignment_warnings,
        "enhancement_notes": []  # Can be populated by LLM suggestions
    }
```

---

## Output Format

```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class SkillEnhancement(BaseModel):
    standardized_skills: List[str]
    skill_categories: Dict[str, List[str]]
    skill_levels: Dict[str, str]  # skill -> beginner/intermediate/advanced/expert
    skills_from_experience: List[str]
    skill_evidence: Dict[str, List[str]]  # skill -> evidence list
    alignment_warnings: List[dict]
    enhancement_notes: List[str]

class SkillAgent:
    def enhance_skills(self, resume: ParsedResume) -> SkillEnhancement:
        ...
```

---

## Data Flow

```
ParsedResume
    ↓
SkillAgent.enhance_skills()
    ↓
    1. Standardize skill names
    2. Extract skill levels from context
    3. Find skills in experience not in skills list
    4. Categorize all skills
    5. Check experience alignment
    6. Gather evidence for each skill
    ↓
SkillEnhancement
    ↓
Used by: ResumeRewriteAgent, ATSScorerAgent
```

---

## Validation Rules

Every skill returned must be traceable:

1. **From skills list** → Direct from resume.skills
2. **From experience** → Found in exp.skills_used or exp.description
3. **From projects** → Found in project.technologies
4. **From certifications** → Found in resume.certifications

If not traceable → DO NOT INCLUDE

---

## Safety Checklist

Before returning enhancement:

- [ ] All skills exist in original resume
- [ ] No invented certifications
- [ ] Skill levels match evidence
- [ ] No inflated claims
- [ ] Alignment warnings for senior claims without experience
- [ ] Evidence gathered for verification

---

## Error Cases

- Empty skills list → Extract from experience, warn about ATS
- No experience → Focus on listed skills and certifications
- LLM suggests fake skills → Validate against resume, reject if not found
- Very short resume → Return what exists with appropriate warnings

