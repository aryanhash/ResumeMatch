# Cline Prompt: Resume Rewrite Agent

## Objective
Generate a Python agent that **honestly** optimizes resumes for ATS and job alignment.

---

## CRITICAL ETHICAL RULES

This agent must NEVER fabricate. It can only reorganize, rephrase, and emphasize EXISTING content.

### ✅ ALLOWED
- Reorder skills to prioritize job-relevant ones
- Improve bullet point wording with action verbs
- Standardize skill names (JS → JavaScript)
- Create targeted professional summary
- Suggest section ordering based on strengths

### ❌ FORBIDDEN
- Add skills to experience where they weren't used
- Invent metrics or numbers ("99.5% uptime")
- Claim certifications that don't exist
- Exaggerate experience level
- Add false achievements

---

## Critical Issues to Fix

### Issue #1: Adding False Skills to Experience
```python
# ❌ WRONG - adds all matching skills to experience
enhanced_skills = list(set(exp.skills_used + gap_analysis.matching_skills[:5]))

# ✅ CORRECT - only add if skill appears in description
desc_text = " ".join(exp.description).lower()
for skill in matching_skills:
    if re.search(r'\b' + re.escape(skill.lower()) + r'\b', desc_text):
        verified_skills.append(skill)  # Only if mentioned
```

### Issue #2: Fabricating Metrics in Bullets
```python
# ❌ WRONG - LLM adds fake numbers
"Fixed bugs" → "Fixed 47 bugs reducing downtime by 99.5%"

# ✅ CORRECT - validate no new numbers added
original_numbers = re.findall(r'\d+(?:\.\d+)?%?', original_bullet)
new_numbers = re.findall(r'\d+(?:\.\d+)?%?', improved_bullet)
fabricated = set(new_numbers) - set(original_numbers)
if fabricated:
    # Remove or reject improvement
```

### Issue #3: Summary Ignoring Gaps
```python
# ❌ WRONG - doesn't consider what's missing
prompt = "Write summary for {role}"

# ✅ CORRECT - context-aware summary
prompt = f"""Write summary for {role}.

MATCH STATUS: {ats_score.bucket}
MATCHING SKILLS: {matching_skills}
MISSING CRITICAL: {missing_critical}

Do NOT claim skills from MISSING list.
{f"Acknowledge learning {missing_critical[0]}" if missing_critical else ""}
"""
```

---

## Requirements

### 1. Context-Aware Summary Generation

```python
def _generate_summary(
    self, 
    resume: ParsedResume, 
    jd: ParsedJobDescription,
    gap_analysis: GapAnalysis,
    ats_score: ATSScore
) -> str:
    """Generate honest, targeted professional summary."""
    
    matching = [s.skill if hasattr(s, 'skill') else s 
                for s in gap_analysis.matching_skills[:5]]
    missing_critical = [s.skill for s in gap_analysis.missing_skills 
                       if s.category == "critical"][:2]
    
    prompt = f"""Write a professional summary for a {jd.role} position.

CANDIDATE:
- Current Role: {resume.experience[0].title if resume.experience else 'Professional'}
- Experience: ~{len(resume.experience)} years
- Key Strengths: {', '.join(matching)}

MATCH STATUS:
- ATS Score: {ats_score.overall_score}/100 ({ats_score.bucket})
- Missing Critical Skills: {', '.join(missing_critical) if missing_critical else 'None'}

RULES:
1. Be HONEST about experience level
2. Lead with MATCHING skills
3. Do NOT claim skills from "Missing Critical Skills" list
4. Keep to 2-3 sentences
5. Use keywords: {', '.join(jd.keywords[:5])}

Return ONLY the summary text."""

    # ... LLM call
```

### 2. Honest Bullet Improvement

```python
def _improve_bullets(
    self, 
    resume: ParsedResume, 
    jd: ParsedJobDescription,
    gap_analysis: GapAnalysis
) -> List[dict]:
    """Improve bullets WITHOUT fabricating achievements."""
    
    prompt = f"""Improve these resume bullets for a {jd.role} role.

SKILLS TO EMPHASIZE (if present): {matching_skills}

BULLETS:
{bullets_json}

CRITICAL RULES:
1. Do NOT add numbers unless they exist in original
   - "Fixed bugs" → "Resolved software defects" ✓
   - "Fixed bugs" → "Fixed 47 bugs, 99% uptime" ❌ (fabricated!)
2. Use action verbs (Led, Built, Designed, Implemented)
3. Only emphasize skills if they appear in the original bullet
4. Keep improvements verifiable

Return JSON with original, improved, and changes."""

    result = llm_call(prompt)
    
    # Validate no fabrication
    validated = []
    for item in result:
        original_nums = set(re.findall(r'\d+(?:\.\d+)?%?', item['original']))
        new_nums = set(re.findall(r'\d+(?:\.\d+)?%?', item['improved']))
        
        if new_nums - original_nums:
            # Fabricated numbers - reject or clean
            item['improved'] = self._remove_fabricated_numbers(
                item['improved'], original_nums
            )
            item['changes'] += " (removed unverified metrics)"
        
        validated.append(item)
    
    return validated
```

### 3. Experience Enhancement (HONEST)

```python
def _enhance_experience(
    self, 
    resume: ParsedResume, 
    jd: ParsedJobDescription,
    gap_analysis: GapAnalysis
) -> List[Experience]:
    """
    Enhance experience entries WITHOUT adding false skills.
    
    Rule: Only add a skill to an experience if it appears
    in that experience's description text.
    """
    
    matching_skills = [s.skill if hasattr(s, 'skill') else s 
                      for s in gap_analysis.matching_skills]
    
    enhanced = []
    for exp in resume.experience:
        verified_skills = list(exp.skills_used)  # Start with existing
        
        desc_text = " ".join(exp.description).lower()
        
        for skill in matching_skills:
            skill_lower = skill.lower()
            
            # Only add if skill actually appears in description
            if skill not in verified_skills:
                pattern = r'\b' + re.escape(skill_lower) + r'\b'
                if re.search(pattern, desc_text):
                    verified_skills.append(skill)
        
        enhanced.append(Experience(
            title=exp.title,
            company=exp.company,
            duration=exp.duration,
            description=exp.description,
            skills_used=verified_skills
        ))
    
    return enhanced
```

### 4. Weighted Skill Reordering

```python
def _reorder_skills(
    self, 
    resume: ParsedResume, 
    jd: ParsedJobDescription,
    gap_analysis: GapAnalysis
) -> List[str]:
    """Reorder skills by relevance weight."""
    
    weighted = []
    
    for skill in resume.skills:
        weight = 0
        skill_lower = skill.lower()
        
        # JD importance
        if skill_lower in [s.lower() for s in jd.required_skills]:
            weight += 100
        elif skill_lower in [s.lower() for s in jd.tools]:
            weight += 75
        elif skill_lower in [s.lower() for s in jd.preferred_skills]:
            weight += 50
        
        # Confirmed match bonus
        for match in gap_analysis.matching_skills:
            match_skill = match.skill if hasattr(match, 'skill') else match
            if skill_lower == match_skill.lower():
                weight += 30
        
        # Experience usage
        for exp in resume.experience:
            if skill_lower in [s.lower() for s in exp.skills_used]:
                weight += 10
        
        weighted.append((skill, weight))
    
    weighted.sort(key=lambda x: x[1], reverse=True)
    return [skill for skill, _ in weighted]
```

### 5. Context-Aware Section Ordering

```python
def _determine_section_order(
    self, 
    resume: ParsedResume, 
    jd: ParsedJobDescription,
    gap_analysis: GapAnalysis,
    ats_score: ATSScore
) -> List[str]:
    """Determine optimal section order based on strengths."""
    
    sections = ["Contact", "Summary"]
    
    skill_score = ats_score.skill_match_score
    exp_score = ats_score.experience_alignment_score
    has_projects = len(resume.projects) > 0
    
    if skill_score >= 70 and exp_score >= 70:
        # Strong: Lead with experience
        sections += ["Experience", "Skills", "Projects"]
    elif skill_score >= 70:
        # Skills strong: Lead with skills
        sections += ["Skills", "Projects", "Experience"]
    elif has_projects and skill_score < 60:
        # Weak skills: Lead with projects (shows ability)
        sections += ["Projects", "Skills", "Experience"]
    else:
        # Default
        sections += ["Skills", "Experience", "Projects"]
    
    if resume.education:
        sections.append("Education")
    if resume.certifications:
        sections.append("Certifications")
    
    return sections
```

### 6. Output Validation

```python
def _validate_output(
    self, 
    rewritten: RewrittenResume,
    original: ParsedResume,
    gap_analysis: GapAnalysis
) -> List[str]:
    """Validate rewritten resume is honest."""
    
    issues = []
    
    # Check summary doesn't claim missing skills
    missing = {s.skill.lower() for s in gap_analysis.missing_skills}
    summary_lower = rewritten.summary.lower()
    
    for skill in missing:
        if skill in summary_lower:
            learning = [f"learning {skill}", f"developing {skill}"]
            if not any(l in summary_lower for l in learning):
                issues.append(f"Summary may over-claim '{skill}'")
    
    # Check no false skills added
    for enhanced in rewritten.enhanced_experience:
        original_exp = next(
            (e for e in original.experience if e.title == enhanced.title), 
            None
        )
        if original_exp:
            new_skills = set(enhanced.skills_used) - set(original_exp.skills_used)
            desc_text = " ".join(enhanced.description).lower()
            
            for skill in new_skills:
                if skill.lower() not in desc_text:
                    issues.append(f"Added '{skill}' to {enhanced.title} without evidence")
    
    return issues
```

---

## Output Format

```python
from pydantic import BaseModel
from typing import List, Optional

class RewrittenResume(BaseModel):
    summary: str
    improved_bullets: List[dict]  # {original, improved, changes}
    reordered_skills: List[str]
    enhanced_experience: List[Experience]
    optimized_sections_order: List[str]
    version_name: str
    full_text: str  # For PDF/Word generation
    validation_issues: List[str] = []

class ResumeRewriteAgent:
    def rewrite(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis,
        ats_score: ATSScore
    ) -> RewrittenResume:
        ...
```

---

## Data Flow

```
ParsedResume + ParsedJobDescription + GapAnalysis + ATSScore
    ↓
ResumeRewriteAgent.rewrite()
    ↓
    1. Generate context-aware summary
    2. Improve bullets (with validation)
    3. Reorder skills by relevance
    4. Enhance experience (HONESTLY)
    5. Determine section order
    6. Build full text
    7. Validate honesty
    ↓
RewrittenResume (with validation issues)
    ↓
Used by: PDF/Word generator, Frontend display
```

---

## Honesty Validation Checklist

Before returning RewrittenResume, verify:

- [ ] Summary doesn't claim missing critical skills
- [ ] No fabricated numbers in improved bullets
- [ ] Enhanced experience only adds skills from descriptions
- [ ] No new certifications invented
- [ ] Experience titles not inflated
- [ ] Years of experience not exaggerated

---

## Error Cases

- Empty experience → Focus on skills/projects
- No matching skills → Use transferable skills language
- Very weak match → Add disclaimer about skill development
- LLM fabricates → Strip fabricated content, log warning

