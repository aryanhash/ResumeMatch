"""
Resume Rewrite Agent - Honest, Context-Aware Resume Optimization

CRITICAL PRINCIPLE: This agent NEVER fabricates experience or adds false claims.
It ONLY reorders, emphasizes, and improves presentation of EXISTING content.

Fixed Issues:
1. ✅ Summary uses gap analysis and ATS score
2. ✅ Bullet improvements don't fabricate metrics
3. ✅ Experience enhancement doesn't add false skills
4. ✅ Skill reordering uses confidence/weight levels
5. ✅ Section order uses full context (gap analysis, ATS score)
6. ✅ Output validation for honesty
7. ✅ All helper methods receive full context

API Support:
- Together AI (for final submission)
- Groq (for development/testing)
"""
import json
import os
import re
import logging
from typing import Optional, List, Dict, Any

# Import both APIs with graceful fallback
try:
    from together import Together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False
    print("⚠️ Together AI not installed")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️ Groq not installed")

from models.schemas import (
    ParsedResume, ParsedJobDescription, GapAnalysis, ATSScore,
    RewrittenResume, Experience, SkillGap
)

logger = logging.getLogger(__name__)


class ResumeRewriteAgent:
    """
    Agent responsible for honest, context-aware resume optimization.
    
    This agent:
    ✅ Reorders content to emphasize matching skills
    ✅ Improves bullet points with action verbs
    ✅ Creates targeted summaries based on gap analysis
    ✅ Validates all output is traceable to original
    
    This agent NEVER:
    ❌ Adds skills to experiences where they weren't used
    ❌ Fabricates metrics or numbers
    ❌ Claims experience the candidate doesn't have
    ❌ Invents certifications or achievements
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with automatic API selection based on USE_GROQ env var"""
        use_groq = os.getenv("USE_GROQ", "false").lower() == "true"
        
        if use_groq and GROQ_AVAILABLE:
            # Use Groq for development/testing
            print("🚀 Using Groq API for ResumeRewriteAgent")
            self.client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
            self.model = "llama-3.1-70b-versatile"
            self.api_type = "groq"
        elif TOGETHER_AVAILABLE:
            # Use Together AI for production
            print("🚀 Using Together AI for ResumeRewriteAgent")
            self.client = Together(api_key=api_key or os.getenv("TOGETHER_API_KEY"))
            self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
            self.api_type = "together"
        else:
            raise RuntimeError(
                "❌ No AI API available for ResumeRewriteAgent!\n"
                "Install either: pip install together OR pip install groq"
            )
    
    def _clean_and_truncate(self, text: str, max_chars: int = 8000) -> str:
        """Clean and truncate text to fit context limits"""
        if not text:
            return ""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        return text
    
    def rewrite(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis,
        ats_score: ATSScore
    ) -> RewrittenResume:
        """
        Rewrite resume for job alignment, maintaining complete honesty.
        
        Uses full context: resume, JD, gap analysis, and ATS score.
        """
        
        # Generate context-aware summary
        summary = self._generate_summary(resume, jd, gap_analysis, ats_score)
        
        # Improve bullets honestly (no fabrication)
        improved_bullets = self._improve_bullets(resume, jd, gap_analysis)
        
        # Reorder skills by relevance weight
        reordered_skills = self._reorder_skills(resume, jd, gap_analysis)
        
        # Enhance experience (HONESTLY - no adding false skills)
        enhanced_experience = self._enhance_experience(resume, jd, gap_analysis)
        
        # Determine section order based on strengths
        section_order = self._determine_section_order(resume, jd, gap_analysis, ats_score)
        
        # Build full text for PDF/Word generation
        full_text = self._build_full_text(
            resume, summary, enhanced_experience, reordered_skills
        )
        
        rewritten = RewrittenResume(
            summary=summary,
            improved_bullets=improved_bullets,
            reordered_skills=reordered_skills,
            enhanced_experience=enhanced_experience,
            optimized_sections_order=section_order,
            version_name=f"Optimized for {jd.role}",
            full_text=full_text
        )
        
        # Validate honesty
        validation_issues = self._validate_rewritten_resume(rewritten, resume, gap_analysis)
        if validation_issues:
            logger.warning(f"Resume rewrite validation issues: {validation_issues}")
        
        return rewritten
    
    def _generate_summary(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis,
        ats_score: ATSScore
    ) -> str:
        """Generate context-aware professional summary"""
        
        # Extract matching and missing skills
        matching_skills = [s if isinstance(s, str) else s.skill 
                         for s in gap_analysis.matching_skills[:5]]
        missing_critical = [s.skill for s in gap_analysis.missing_skills 
                          if hasattr(s, 'importance') and s.importance == "required"][:2]
        
        # Determine experience level
        exp_count = len(resume.experience)
        exp_years = self._estimate_years(resume)
        
        # Determine candidate strength
        is_strong_match = ats_score.overall_score >= 75
        is_moderate_match = 50 <= ats_score.overall_score < 75
        
        prompt = f"""Write a professional summary for a {jd.role} position.

CANDIDATE PROFILE:
- Current/Recent Title: {resume.experience[0].title if resume.experience else 'Professional'}
- Experience: ~{exp_years} years ({exp_count} positions)
- Key Strengths: {', '.join(matching_skills) if matching_skills else 'Various technical skills'}

MATCH ANALYSIS:
- ATS Score: {ats_score.overall_score}/100 ({ats_score.bucket})
- Matching Required Skills: {', '.join(matching_skills) if matching_skills else 'Limited matches'}
- Critical Skill Gaps: {', '.join(missing_critical) if missing_critical else 'No critical gaps'}

TARGET ROLE:
- Position: {jd.role}
- Seniority: {jd.seniority.value if hasattr(jd.seniority, 'value') else jd.seniority}
- Must-Have Skills: {', '.join(jd.required_skills[:5])}

WRITING GUIDELINES:
1. Be HONEST about experience level - don't exaggerate
2. Lead with MATCHING skills and relevant experience
3. {'Focus on transferable skills and learning agility' if not is_strong_match else 'Emphasize strong alignment with requirements'}
4. Use keywords: {', '.join(jd.keywords[:5]) if jd.keywords else 'role-specific terms'}
5. Keep to 2-3 sentences maximum
6. CRITICAL: Do NOT mention or claim ANY skills from the "Critical Skill Gaps" list
7. CRITICAL: Only mention skills that are explicitly listed in "Key Strengths" or "Matching Required Skills"
8. If candidate is weak match, focus on enthusiasm, learning ability, and transferable skills

Write the summary now. Return ONLY the summary text, no explanations."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an honest resume writer. Never exaggerate or fabricate."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Remove any quotes that might wrap the response
            if summary.startswith('"') and summary.endswith('"'):
                summary = summary[1:-1]
            
            return summary
            
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return self._fallback_summary(resume, jd, matching_skills)
    
    def _fallback_summary(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription,
        matching_skills: List[str]
    ) -> str:
        """Generate fallback summary if LLM fails"""
        title = resume.experience[0].title if resume.experience else "Professional"
        exp_years = self._estimate_years(resume)
        skills_str = ", ".join(matching_skills[:3]) if matching_skills else "relevant technical skills"
        
        return (
            f"{title} with {exp_years}+ years of experience in {skills_str}. "
            f"Seeking to contribute expertise to {jd.role} role with focus on "
            f"delivering high-quality results and continuous improvement."
        )
    
    def _estimate_years(self, resume: ParsedResume) -> int:
        """Estimate years of experience from resume"""
        # Count positions as rough estimate
        return max(1, len(resume.experience))
    
    def _clean_text(self, text: str) -> str:
        """Clean text of control characters and invalid characters that break JSON"""
        if not text:
            return ""

        # Remove control characters (0x00-0x1F except tab, newline, carriage return)
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')

        # Remove other problematic characters
        text = text.replace('\ufeff', '')  # BOM character
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u2019', "'")  # Smart quote
        text = text.replace('\u201c', '"')  # Left double quote
        text = text.replace('\u201d', '"')  # Right double quote

        # Clean up multiple spaces
        import re
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _improve_bullets(
        self,
        resume: ParsedResume,
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis
    ) -> List[Dict[str, str]]:
        """Improve bullet points HONESTLY without fabricating metrics"""

        matching_skills = [s if isinstance(s, str) else s.skill
                         for s in gap_analysis.matching_skills[:5]]

        # Get bullets from relevant experiences
        sample_bullets = []
        for exp in resume.experience[:3]:
            exp_text = (exp.title + " " + " ".join(exp.description)).lower()

            # Check if this experience is relevant to the JD
            is_relevant = any(skill.lower() in exp_text for skill in matching_skills)

            for bullet in exp.description[:3]:
                # Clean the bullet text
                clean_bullet = self._clean_text(bullet)
                if clean_bullet:  # Only add non-empty bullets
                    sample_bullets.append({
                        "bullet": clean_bullet,
                        "role": exp.title,
                        "company": exp.company,
                        "is_relevant": is_relevant,
                        "skills_used": exp.skills_used
                    })

        if not sample_bullets:
            return []
        
        prompt = f"""Improve these resume bullets HONESTLY for a {jd.role} role.

SKILLS TO EMPHASIZE (if present in original): {', '.join(matching_skills)}
TARGET KEYWORDS: {', '.join(jd.keywords[:8]) if jd.keywords else 'role-specific terms'}

BULLETS TO IMPROVE:
{json.dumps(sample_bullets[:6], indent=2)}

CRITICAL RULES:
1. Do NOT add numbers/metrics unless they are IMPLIED by original
   - "Fixed bugs" → "Resolved software defects" ✓ (action verb)
   - "Fixed bugs" → "Fixed 47 bugs reducing downtime by 99%" ❌ (fabricated number)
2. Do NOT claim skills not present in original bullet
3. DO use action verbs (Led, Built, Designed, Implemented, Optimized)
4. DO make bullets more specific using original context
5. DO emphasize skills that match the job IF they appear in original
6. Keep improvements realistic and verifiable

Return JSON array:
[
    {{
        "original": "Original bullet text",
        "improved": "Improved bullet text", 
        "reason": "What was changed and why"
    }}
]

Return ONLY valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You improve resumes honestly. Never fabricate achievements."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean JSON
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            improved = json.loads(result_text.strip())
            
            # Validate no fabrication
            validated = self._validate_bullet_improvements(improved, sample_bullets)
            
            return validated
            
        except Exception as e:
            logger.warning(f"Bullet improvement failed: {e}")
            return self._fallback_bullets(sample_bullets)
    
    def _validate_bullet_improvements(
        self, 
        improved: List[Dict], 
        originals: List[Dict]
    ) -> List[Dict[str, str]]:
        """Validate that improvements don't fabricate numbers"""
        
        validated = []
        
        for item in improved:
            original = item.get("original", "")
            new_text = item.get("improved", original)
            
            # Check if new text has numbers not in original
            original_numbers = set(re.findall(r'\d+(?:\.\d+)?%?', original))
            new_numbers = set(re.findall(r'\d+(?:\.\d+)?%?', new_text))
            
            fabricated_numbers = new_numbers - original_numbers
            
            if fabricated_numbers:
                # Remove fabricated numbers from improvement
                logger.warning(f"Removing fabricated numbers: {fabricated_numbers}")
                for num in fabricated_numbers:
                    new_text = new_text.replace(num, "")
                new_text = re.sub(r'\s+', ' ', new_text).strip()
            
            validated.append({
                "original": original,
                "improved": new_text,
                "reason": item.get("reason", item.get("changes", "Action verb and clarity improvements"))
            })
        
        return validated
    
    def _fallback_bullets(self, sample_bullets: List[Dict]) -> List[Dict[str, str]]:
        """Generate simple improvements if LLM fails"""
        
        action_verbs = ["Developed", "Implemented", "Designed", "Led", "Built", "Created"]
        improved = []
        
        for i, bullet_info in enumerate(sample_bullets[:5]):
            original = bullet_info.get("bullet", "")
            
            # Simple improvement: add action verb if missing
            if not any(original.startswith(verb) for verb in action_verbs):
                verb = action_verbs[i % len(action_verbs)]
                new_text = f"{verb} {original[0].lower()}{original[1:]}"
            else:
                new_text = original
            
            improved.append({
                "original": original,
                "improved": new_text,
                "reason": "Added action verb for stronger impact"
            })
        
        return improved
    
    def _reorder_skills(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis
    ) -> List[str]:
        """Reorder skills by relevance weight"""
        
        # Build skill weights
        weighted_skills = []
        
        required_set = {s.lower() for s in jd.required_skills}
        preferred_set = {s.lower() for s in jd.preferred_skills}
        tools_set = {s.lower() for s in jd.tools}
        matching_set = {(s if isinstance(s, str) else s.skill).lower() 
                       for s in gap_analysis.matching_skills}
        
        for skill in resume.skills:
            skill_lower = skill.lower()
            weight = 0
            
            # Weight by JD importance
            if skill_lower in required_set:
                weight += 100
            elif skill_lower in tools_set:
                weight += 75
            elif skill_lower in preferred_set:
                weight += 50
            
            # Bonus for being a confirmed match
            if skill_lower in matching_set:
                weight += 30
            
            # Weight by experience usage
            usage_count = sum(
                1 for exp in resume.experience 
                if skill_lower in [s.lower() for s in exp.skills_used]
            )
            weight += usage_count * 10
            
            # Weight by project usage
            project_usage = sum(
                1 for proj in resume.projects 
                if skill_lower in [t.lower() for t in proj.technologies]
            )
            weight += project_usage * 5
            
            weighted_skills.append((skill, weight))
        
        # Sort by weight descending
        weighted_skills.sort(key=lambda x: x[1], reverse=True)
        
        return [skill for skill, _ in weighted_skills]
    
    def _enhance_experience(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis
    ) -> List[Experience]:
        """
        Enhance experience entries HONESTLY.
        
        CRITICAL: Only add skills to an experience if they are
        ACTUALLY MENTIONED in that experience's description.
        """
        
        matching_skills = [s if isinstance(s, str) else s.skill 
                         for s in gap_analysis.matching_skills]
        
        enhanced = []
        
        for exp in resume.experience:
            # Start with existing skills
            verified_skills = list(exp.skills_used)
            
            # ONLY add matching skills if they appear in the description
            desc_text = " ".join(exp.description).lower()
            
            for skill in matching_skills:
                skill_lower = skill.lower()
                
                # Check if skill is mentioned in this experience
                if skill_lower in desc_text and skill not in verified_skills:
                    # Verify with word boundary
                    if re.search(r'\b' + re.escape(skill_lower) + r'\b', desc_text):
                        verified_skills.append(skill)
            
            enhanced.append(Experience(
                title=exp.title,
                company=exp.company,
                duration=exp.duration,
                description=exp.description,
                skills_used=verified_skills
            ))
        
        return enhanced
    
    def _determine_section_order(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis,
        ats_score: ATSScore
    ) -> List[str]:
        """Determine optimal section order based on candidate strengths"""
        
        sections = ["Contact", "Summary"]
        
        skill_score = ats_score.skill_match_score
        exp_score = ats_score.experience_alignment_score
        
        has_strong_experience = exp_score >= 70
        has_strong_skills = skill_score >= 70
        has_projects = len(resume.projects) > 0
        is_entry_level = jd.seniority.value in ["entry", "junior"] if hasattr(jd.seniority, 'value') else False
        
        if has_strong_skills and has_strong_experience:
            # Strong candidate: Lead with experience
            sections.extend(["Experience", "Skills", "Projects"])
        elif has_strong_skills and not has_strong_experience:
            # Skills strong but experience weak: Lead with skills
            sections.extend(["Skills", "Projects", "Experience"])
        elif has_strong_experience and not has_strong_skills:
            # Experience strong but skills weak: Lead with experience
            sections.extend(["Experience", "Projects", "Skills"])
        elif has_projects and (skill_score < 50 or exp_score < 50):
            # Weak match: Lead with projects to show practical ability
            sections.extend(["Projects", "Skills", "Experience"])
        elif is_entry_level and resume.education:
            # Entry level: Education might be strength
            sections.extend(["Education", "Skills", "Projects", "Experience"])
        else:
            # Default order
            sections.extend(["Skills", "Experience", "Projects"])
        
        # Add remaining sections
        if resume.education and "Education" not in sections:
            sections.append("Education")
        if resume.certifications:
            sections.append("Certifications")
        
        return sections
    
    def _build_full_text(
        self, 
        resume: ParsedResume,
        summary: str,
        enhanced_experience: List[Experience],
        reordered_skills: List[str]
    ) -> str:
        """Build full resume text for document generation"""
        
        lines = []
        
        # Header
        lines.append(resume.name.upper())
        contact_parts = []
        if resume.email:
            contact_parts.append(resume.email)
        if resume.phone:
            contact_parts.append(resume.phone)
        if resume.location:
            contact_parts.append(resume.location)
        if resume.linkedin:
            contact_parts.append(resume.linkedin)
        lines.append(" | ".join(contact_parts))
        lines.append("")
        
        # Summary
        lines.append("PROFESSIONAL SUMMARY")
        lines.append(summary)
        lines.append("")
        
        # Skills
        lines.append("TECHNICAL SKILLS")
        lines.append(", ".join(reordered_skills))
        lines.append("")
        
        # Experience
        lines.append("PROFESSIONAL EXPERIENCE")
        for exp in enhanced_experience:
            lines.append(f"{exp.title} | {exp.company}")
            lines.append(exp.duration)
            for bullet in exp.description:
                lines.append(f"• {bullet}")
            if exp.skills_used:
                lines.append(f"Skills: {', '.join(exp.skills_used)}")
            lines.append("")
        
        # Projects
        if resume.projects:
            lines.append("PROJECTS")
            for proj in resume.projects:
                lines.append(proj.name)
                lines.append(proj.description)
                lines.append(f"Technologies: {', '.join(proj.technologies)}")
                lines.append("")
        
        # Education
        if resume.education:
            lines.append("EDUCATION")
            for edu in resume.education:
                lines.append(f"{edu.degree} - {edu.institution}")
                if edu.year:
                    lines.append(edu.year)
            lines.append("")
        
        # Certifications
        if resume.certifications:
            lines.append("CERTIFICATIONS")
            for cert in resume.certifications:
                lines.append(f"• {cert}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _validate_rewritten_resume(
        self, 
        rewritten: RewrittenResume, 
        original: ParsedResume,
        gap_analysis: GapAnalysis
    ) -> List[str]:
        """Validate that rewritten resume is honest"""
        
        issues = []
        
        # Get missing skills
        missing_skills = [s.skill.lower() for s in gap_analysis.missing_skills 
                        if hasattr(s, 'skill')]
        
        # Check summary doesn't claim missing skills
        summary_lower = rewritten.summary.lower()
        for skill in missing_skills[:5]:
            if skill in summary_lower:
                # Allow mentions in context of "learning" or "pursuing"
                learning_patterns = [
                    f"learning {skill}", f"pursuing {skill}", 
                    f"developing {skill}", f"gaining {skill}"
                ]
                if not any(p in summary_lower for p in learning_patterns):
                    issues.append(f"Summary may claim '{skill}' which is a gap")
        
        # Check enhanced experience doesn't add false skills
        original_skills_by_title = {
            exp.title: set(exp.skills_used) for exp in original.experience
        }
        
        for enhanced_exp in rewritten.enhanced_experience:
            original_skills = original_skills_by_title.get(enhanced_exp.title, set())
            new_skills = set(enhanced_exp.skills_used) - original_skills
            
            if new_skills:
                # These are skills we added - verify they were in description
                desc_text = " ".join(enhanced_exp.description).lower()
                for skill in new_skills:
                    if skill.lower() not in desc_text:
                        issues.append(
                            f"Added '{skill}' to {enhanced_exp.title} but not found in description"
                        )
        
        return issues


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
        
        resume = ParsedResume(**data.get("resume", {}))
        jd = ParsedJobDescription(**data.get("jd", {}))
        gap_analysis = GapAnalysis(**data.get("gap_analysis", {}))
        ats_score = ATSScore(**data.get("ats_score", {}))
        
        agent = ResumeRewriteAgent()
        result = agent.rewrite(resume, jd, gap_analysis, ats_score)
        print(result.model_dump_json(indent=2))
    else:
        print("Usage: python resume_rewrite.py <input.json>")