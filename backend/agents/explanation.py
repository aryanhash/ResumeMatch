"""
Explanation Agent - Provides detailed analysis and explanations

API Support:
- Together AI (for final submission)
- Groq (for development/testing)
"""
import json
import os
from typing import Optional

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
    ResumeExplanation
)


class ExplanationAgent:
    """Agent responsible for explaining resume analysis from recruiter perspective"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with automatic API selection based on USE_GROQ env var"""
        use_groq = os.getenv("USE_GROQ", "false").lower() == "true"
        
        if use_groq and GROQ_AVAILABLE:
            # Use Groq for development/testing
            print("🚀 Using Groq API for ExplanationAgent")
            self.client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
            self.model = "llama-3.1-70b-versatile"
            self.api_type = "groq"
        elif TOGETHER_AVAILABLE:
            # Use Together AI for production
            print("🚀 Using Together AI for ExplanationAgent")
            self.client = Together(api_key=api_key or os.getenv("TOGETHER_API_KEY"))
            self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
            self.api_type = "together"
        else:
            raise RuntimeError(
                "❌ No AI API available for ExplanationAgent!\n"
                "Install either: pip install together OR pip install groq"
            )
    
    def explain(
        self,
        resume: ParsedResume,
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis,
        ats_score: ATSScore
    ) -> ResumeExplanation:
        """Generate comprehensive explanation of resume analysis"""
        
        # Get recruiter perspective
        recruiter_perspective = self._get_recruiter_perspective(resume, jd, gap_analysis)
        
        # Generate ATS breakdown
        ats_breakdown = self._get_ats_breakdown(ats_score)
        
        # Identify improvement areas
        improvement_areas = self._identify_improvements(gap_analysis, ats_score)
        
        # Find standout elements
        standouts = self._find_standouts(resume, gap_analysis)
        
        # Identify red flags
        red_flags = self._identify_red_flags(resume, jd, gap_analysis)
        
        return ResumeExplanation(
            recruiter_perspective=recruiter_perspective,
            ats_breakdown=ats_breakdown,
            improvement_areas=improvement_areas,
            what_stands_out=standouts,
            red_flags=red_flags
        )
    
    def _get_recruiter_perspective(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis
    ) -> str:
        """Get AI-generated recruiter perspective"""
        
        prompt = f"""You are an experienced technical recruiter reviewing a resume for a {jd.role} position.

CANDIDATE PROFILE:
- Name: {resume.name or 'Candidate'}
- Experience: {len(resume.experience)} positions
- Skills: {', '.join(resume.skills[:10])}
- Education: {resume.education[0].degree if resume.education else 'Not specified'}

JOB REQUIREMENTS:
- Role: {jd.role}
- Seniority: {jd.seniority.value}
- Required Skills: {', '.join(jd.required_skills[:8])}

MATCH ANALYSIS:
- Matching Skills: {', '.join(gap_analysis.matching_skills[:8])}
- Missing Required: {', '.join(s.skill for s in gap_analysis.missing_skills if s.importance == 'required')[:5]}
- Overall Match: {gap_analysis.overall_match_percentage}%

Write a 3-4 sentence recruiter assessment of this candidate. Be honest but constructive.
Consider:
- First impressions
- Strengths for this role
- Main concerns
- Interview potential

Return ONLY the assessment text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior technical recruiter. Provide honest, constructive feedback."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=400
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            match_pct = gap_analysis.overall_match_percentage
            if match_pct >= 70:
                return f"This candidate shows strong alignment with the {jd.role} position, demonstrating relevant skills and experience. Worth moving forward to an interview to assess technical depth and cultural fit."
            elif match_pct >= 50:
                return f"This candidate has some relevant experience for the {jd.role} role, but there are gaps in key required skills. Could be worth a phone screen to assess potential and learning ability."
            else:
                return f"The candidate's profile has limited overlap with the {jd.role} requirements. Would recommend focusing on roles more aligned with their current skill set."
    
    def _get_ats_breakdown(self, ats_score: ATSScore) -> str:
        """Generate detailed ATS breakdown explanation"""
        
        breakdown = f"""ATS COMPATIBILITY BREAKDOWN

Overall Score: {ats_score.overall_score}/100 ({ats_score.bucket.value.replace('_', ' ').title()})

Component Scores:
- Skill Match: {ats_score.skill_match_score}/100 - {"Excellent" if ats_score.skill_match_score >= 80 else "Good" if ats_score.skill_match_score >= 60 else "Needs Work"}
- Keyword Density: {ats_score.keyword_score}/100 - {"Strong" if ats_score.keyword_score >= 80 else "Moderate" if ats_score.keyword_score >= 60 else "Low"}
- Formatting: {ats_score.formatting_score}/100 - {"Well Structured" if ats_score.formatting_score >= 80 else "Acceptable" if ats_score.formatting_score >= 60 else "Issues Found"}
- Experience Alignment: {ats_score.experience_alignment_score}/100 - {"Aligned" if ats_score.experience_alignment_score >= 70 else "Partial Match" if ats_score.experience_alignment_score >= 50 else "Gap Exists"}

Key Issues Found: {len(ats_score.issues)}
"""
        
        for issue in ats_score.issues[:3]:
            breakdown += f"\n• [{issue.severity.upper()}] {issue.issue}"
        
        return breakdown
    
    def _identify_improvements(self, gap_analysis: GapAnalysis, ats_score: ATSScore) -> list:
        """Identify specific improvement areas with suggestions"""
        improvements = []
        
        # Skill gaps
        missing_required = [s for s in gap_analysis.missing_skills if s.importance == "required"]
        if missing_required:
            improvements.append({
                "area": "Required Skills Gap",
                "issue": f"Missing {len(missing_required)} required skills",
                "suggestion": f"Add experience with: {', '.join(s.skill for s in missing_required[:4])}"
            })
        
        # Keyword gaps
        if len(gap_analysis.missing_keywords) > 3:
            improvements.append({
                "area": "Keyword Optimization",
                "issue": "Resume lacks important industry keywords",
                "suggestion": f"Incorporate: {', '.join(gap_analysis.missing_keywords[:5])}"
            })
        
        # Tool gaps
        if gap_analysis.missing_tools:
            improvements.append({
                "area": "Technology Stack",
                "issue": f"Missing experience with {len(gap_analysis.missing_tools)} tools",
                "suggestion": f"Mention experience with or learn: {', '.join(gap_analysis.missing_tools[:3])}"
            })
        
        # Based on ATS issues
        for issue in ats_score.issues:
            if issue.severity == "high":
                improvements.append({
                    "area": issue.category,
                    "issue": issue.issue,
                    "suggestion": issue.suggestion
                })
        
        return improvements[:5]  # Top 5 improvements
    
    def _find_standouts(self, resume: ParsedResume, gap_analysis: GapAnalysis) -> list:
        """Find what stands out positively in the resume"""
        standouts = []
        
        # Strong skill match
        if len(gap_analysis.matching_skills) >= 5:
            standouts.append(f"Strong skill alignment with {len(gap_analysis.matching_skills)} matching skills")
        
        # Relevant experience
        if len(resume.experience) >= 3:
            standouts.append("Solid professional experience with multiple positions")
        
        # Projects
        if resume.projects and len(resume.projects) >= 2:
            standouts.append("Active project portfolio demonstrates practical experience")
        
        # Certifications
        if resume.certifications:
            standouts.append(f"Professional certifications: {', '.join(resume.certifications[:3])}")
        
        # GitHub presence
        if resume.github:
            standouts.append("GitHub profile shows commitment to open source/personal projects")
        
        # Education
        if resume.education:
            standouts.append(f"Educational background: {resume.education[0].degree}")
        
        return standouts if standouts else ["Resume demonstrates relevant professional background"]
    
    def _identify_red_flags(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis
    ) -> list:
        """Identify potential red flags in the application"""
        red_flags = []
        
        # Major skill gaps
        missing_required = [s for s in gap_analysis.missing_skills if s.importance == "required"]
        if len(missing_required) >= 3:
            red_flags.append(f"Missing {len(missing_required)} required skills may disqualify candidate")
        
        # Experience mismatch
        if not gap_analysis.seniority_match:
            red_flags.append("Experience level may not match role seniority requirements")
        
        # No contact info
        if not resume.email and not resume.phone:
            red_flags.append("Missing contact information on resume")
        
        # Very short experience descriptions
        if resume.experience:
            short_exp = sum(1 for exp in resume.experience if len(exp.description) < 2)
            if short_exp == len(resume.experience):
                red_flags.append("Experience descriptions lack detail - difficult to assess capabilities")
        
        # Low overall match
        if gap_analysis.overall_match_percentage < 40:
            red_flags.append("Overall profile match is below 40% - may not be suitable for this specific role")
        
        return red_flags if red_flags else []


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    else:
        data = json.loads(sys.stdin.read())
    
    resume = ParsedResume(**data["resume"])
    jd = ParsedJobDescription(**data["jd"])
    gap_analysis = GapAnalysis(**data["gap_analysis"])
    ats_score = ATSScore(**data["ats_score"])
    
    agent = ExplanationAgent()
    result = agent.explain(resume, jd, gap_analysis, ats_score)
    print(result.model_dump_json(indent=2))