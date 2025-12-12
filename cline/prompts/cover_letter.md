# Cline Prompt: Cover Letter Generator Agent

## Objective
Generate a Python agent that creates **honest, personalized** cover letters.

---

## Critical Issues to Fix

### Issue #1: No Fabrication Prevention
```python
# ❌ WRONG - LLM can make up achievements
prompt = "Write a cover letter highlighting candidate achievements"

# ✅ CORRECT - constrain to actual resume content
prompt = """Write a cover letter.

ONLY reference these ACTUAL achievements from resume:
{resume.experience[0].description[:3]}

DO NOT invent metrics, numbers, or accomplishments not listed above.
"""
```

### Issue #2: No Gap Handling Strategy
```python
# ❌ WRONG - ignores critical skill gaps
prompt = f"Skills: {resume.skills}, Matching: {matching_skills}"

# ✅ CORRECT - handle gaps appropriately
if len(missing_critical) <= 2:
    # Minor gaps - focus on strengths
    gap_instruction = "Focus on matching skills, don't mention gaps."
elif len(missing_critical) <= 4:
    # Moderate gaps - acknowledge eagerness to learn
    gap_instruction = "Briefly mention eagerness to learn {missing_skills[0]}."
else:
    # Major gaps - flag for review
    gap_instruction = "CRITICAL: Too many skill gaps. Recommend not sending."
```

### Issue #3: No Validation Against Resume
```python
# ❌ WRONG - no check if cover letter claims match resume
return CoverLetter(content=llm_response)

# ✅ CORRECT - validate claims
def _validate_cover_letter(self, content: str, resume: ParsedResume) -> List[str]:
    warnings = []
    
    # Check for numbers not in resume
    content_numbers = re.findall(r'\d+(?:\.\d+)?%?', content)
    resume_numbers = re.findall(r'\d+(?:\.\d+)?%?', resume.raw_text)
    
    for num in content_numbers:
        if num not in resume_numbers and not num.isdigit():
            warnings.append(f"Cover letter mentions '{num}' not found in resume")
    
    return warnings
```

---

## Requirements

Write a Python script that:

### 1. Gap-Aware Content Strategy

```python
def _determine_content_strategy(self, gap_analysis: GapAnalysis) -> dict:
    """Determine how to handle skill gaps in cover letter."""
    
    matching = [s if isinstance(s, str) else s.skill 
                for s in gap_analysis.matching_skills]
    missing = [s.skill for s in gap_analysis.missing_skills 
               if s.importance == "required"]
    
    match_rate = len(matching) / (len(matching) + len(missing)) if (matching or missing) else 1.0
    
    if match_rate >= 0.7:
        return {
            "strategy": "focus_strengths",
            "mention_gaps": False,
            "confidence": "high"
        }
    elif match_rate >= 0.5:
        return {
            "strategy": "acknowledge_learning",
            "mention_gaps": True,
            "gap_to_mention": missing[0] if missing else None,
            "confidence": "moderate"
        }
    else:
        return {
            "strategy": "flag_for_review",
            "mention_gaps": True,
            "confidence": "low",
            "warning": "Consider if this role is appropriate fit"
        }
```

### 2. Honest Content Generation

```python
prompt = f"""Write a professional cover letter for a {jd.role} position at {jd.company or 'the company'}.

CANDIDATE INFORMATION (Use ONLY this - do not invent):
- Current Role: {resume.experience[0].title if resume.experience else 'Professional'}
- Key Skills: {', '.join(matching_skills[:5])}
- Top Achievement: {resume.experience[0].description[0] if resume.experience else 'N/A'}

JOB REQUIREMENTS:
- Role: {jd.role}
- Required Skills: {', '.join(jd.required_skills[:5])}
- Company: {jd.company or 'Not specified'}

SKILL MATCH STATUS:
- Match Rate: {strategy['confidence']}
- Strategy: {strategy['strategy']}
{f"- Learning: Express eagerness to learn {strategy.get('gap_to_mention', '')}" if strategy['mention_gaps'] else ""}

CRITICAL RULES:
1. Use ONLY achievements from candidate information above
2. Do NOT invent metrics, percentages, or numbers
3. Do NOT claim skills the candidate doesn't have
4. Keep to 3-4 paragraphs, 250-350 words
5. Include company-specific language if company name provided
6. End with clear call to action

Return ONLY the cover letter text."""
```

### 3. Output Validation

```python
def _validate_output(self, content: str, resume: ParsedResume, 
                     gap_analysis: GapAnalysis) -> List[str]:
    """Validate cover letter doesn't fabricate."""
    warnings = []
    
    # Check for missing skills mentioned as strengths
    missing_skills = {s.skill.lower() for s in gap_analysis.missing_skills 
                     if s.importance == "required"}
    
    content_lower = content.lower()
    for skill in missing_skills:
        # Check if mentioned positively (not as "learning")
        if skill in content_lower:
            learning_patterns = [f"learning {skill}", f"developing {skill}", 
                               f"gaining {skill}", f"exploring {skill}"]
            if not any(p in content_lower for p in learning_patterns):
                warnings.append(f"Cover letter may over-claim '{skill}' which is missing")
    
    # Check for fabricated metrics
    metrics_in_content = re.findall(r'\d+%|\d+\+?\s*(?:years?|projects?|teams?)', content)
    for metric in metrics_in_content:
        if metric not in resume.raw_text:
            warnings.append(f"Metric '{metric}' not found in resume - verify accuracy")
    
    return warnings
```

---

## Output Format

```python
from pydantic import BaseModel
from typing import List, Optional

class CoverLetter(BaseModel):
    content: str
    tone: str  # professional, friendly, formal
    word_count: int
    key_highlights: List[str]  # Main points emphasized
    match_confidence: str  # high, moderate, low
    warnings: List[str] = []  # Validation warnings

class CoverLetterAgent:
    def __init__(self, api_key: str):
        self.client = Together(api_key=api_key)
    
    def generate(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription, 
        gap_analysis: GapAnalysis,
        tone: str = "professional"
    ) -> CoverLetter:
        ...
```

---

## Data Flow

```
ParsedResume + ParsedJobDescription + GapAnalysis
    ↓
CoverLetterAgent.generate()
    ↓
    1. Determine content strategy based on gaps
    2. Generate with LLM using constrained prompt
    3. Validate output against resume
    4. Return with warnings if any
    ↓
CoverLetter (with warnings for review)
```

---

## Gap Handling Matrix

| Match Rate | Strategy | Gap Handling |
|------------|----------|--------------|
| 70%+ | Focus Strengths | Don't mention gaps |
| 50-69% | Acknowledge Learning | "Eager to develop {skill}" |
| 30-49% | Balanced | Acknowledge gaps, highlight transferables |
| <30% | Flag for Review | Add warning, recommend human review |

---

## Safety & Ethics

### MUST DO
- Only reference achievements from resume
- Acknowledge gaps honestly (if strategy calls for it)
- Use real company name if available
- Keep metrics traceable to resume

### MUST NOT DO
- Invent metrics or percentages
- Claim skills the candidate lacks
- Exaggerate experience level
- Copy generic templates without personalization

### WARNINGS
- Flag any cover letter with <50% match rate
- Flag if using fabricated-looking metrics
- Flag if claiming missing critical skills

---

## Error Cases

- Empty resume → Return minimal letter with warning
- No matching skills → Flag for review, focus on transferable skills
- LLM returns too long → Truncate to 400 words
- LLM hallucinates metrics → Remove in post-processing
