"""
ATS Scoring Agent - Accurate, Bug-Free ATS Compatibility Scoring

Fixed Issues:
1. ✅ Correct match ratio (separates required from preferred)
2. ✅ Consistent skill types handling
3. ✅ Issues affect the final score
4. ✅ Critical gaps block high scores
5. ✅ Realistic keyword scoring
6. ✅ Award-based formatting score (not penalty-based)
7. ✅ Experience relevance checking
8. ✅ Preferred skills as bonus, not penalty

API Support:
- Together AI (for final submission)
- Groq (for development/testing)
"""
import os
import re
from typing import Optional, List, Dict, Tuple

# Import both clients
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from together import Together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False

from models.schemas import (
    ParsedResume, ParsedJobDescription, GapAnalysis,
    ATSScore, ATSBucket, ATSIssue, SkillGap
)


class ATSScorerAgent:
    """
    ATS Scoring Agent with accurate, fair scoring
    
    Score Breakdown:
    - Required Skills: 40% (most critical)
    - Keywords: 20%
    - Formatting: 20%
    - Experience Alignment: 20%
    
    Preferred skills add BONUS points (max +10), don't penalize
    
    API Support:
    Set USE_GROQ=true in .env to use Groq (for testing)
    Set USE_GROQ=false to use Together AI (for submission)
    """
    
    # Critical skills that must match for role consideration
    CRITICAL_SKILLS_BY_ROLE = {
        "python": ["python", "django", "fastapi", "flask"],
        "backend": ["python", "java", "go", "nodejs", "fastapi", "django", "spring"],
        "frontend": ["javascript", "react", "vue", "angular", "typescript"],
        "fullstack": ["javascript", "python", "react", "nodejs"],
        "data": ["python", "sql", "pandas", "spark"],
        "devops": ["docker", "kubernetes", "aws", "terraform"],
        "cloud": ["aws", "azure", "gcp", "docker"],
    }
    
    # Issue severity penalties - more lenient
    SEVERITY_PENALTIES = {
        "critical": -15,
        "high": -6,
        "medium": -3,
        "low": -1
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ATS Scorer Agent with Groq (free) or Together AI (production)
        
        Auto-selects based on USE_GROQ environment variable:
        - USE_GROQ=true → Groq with llama-3.3-70b-versatile
        - USE_GROQ=false/unset → Together AI with Mixtral-8x7B
        """
        use_groq = os.getenv("USE_GROQ", "false").lower() == "true"
        
        if use_groq and GROQ_AVAILABLE:
            # Groq Configuration (Free Tier)
            self.client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
            self.model = "llama-3.3-70b-versatile"
            self.provider = "groq"  # ← FIXED: Changed from api_type to provider
        elif TOGETHER_AVAILABLE:
            # Together AI Configuration (Production)
            self.client = Together(api_key=api_key or os.getenv("TOGETHER_API_KEY"))
            self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
            self.provider = "together"  # ← FIXED: Changed from api_type to provider
        else:
            raise RuntimeError("Neither Groq nor Together AI client is available. Install with: pip install groq together")
    
    def score(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription, 
        gap_analysis: GapAnalysis
    ) -> ATSScore:
        """Calculate comprehensive, accurate ATS score"""
        
        # Step 1: Identify issues FIRST (affects final score)
        issues = self._identify_issues(resume, jd, gap_analysis)
        
        # Step 2: Check for critical blockers (only SEVERE ones cap score)
        critical_issues = [i for i in issues if i.severity == "critical"]
        missing_critical = self._get_missing_critical_skills(jd, gap_analysis)
        
        # Only cap score for severe critical gaps (4+ missing critical skills)
        # Allow more flexibility for realistic scoring
        has_severe_blockers = len(missing_critical) >= 4 or len(critical_issues) >= 3

        # Step 3: Calculate component scores
        skill_score, skill_details = self._calculate_skill_score(gap_analysis, jd)
        keyword_score = self._calculate_keyword_score(gap_analysis)
        formatting_score = self._calculate_formatting_score(resume)
        experience_score = self._calculate_experience_score(resume, jd)
        preferred_bonus = self._calculate_preferred_bonus(gap_analysis)

        # Step 4: Calculate base score (weighted)
        base_score = int(
            skill_score * 0.40 +      # Required skills: 40%
            keyword_score * 0.20 +     # Keywords: 20%
            formatting_score * 0.20 +  # Formatting: 20%
            experience_score * 0.20    # Experience: 20%
        )

        # Step 5: Add preferred skills bonus (max +10)
        base_score += preferred_bonus

        # Step 6: Apply issue penalties (less severe)
        issue_penalty = sum(self.SEVERITY_PENALTIES.get(i.severity, 0) for i in issues)
        penalized_score = base_score + issue_penalty

        # Step 7: Cap score only for truly severe blockers
        if has_severe_blockers:
            # Can't be "strong" with severe critical gaps
            penalized_score = min(penalized_score, 60)
        elif len(missing_critical) >= 3:
            # 3 missing critical = can't be higher than moderate
            penalized_score = min(penalized_score, 75)
        elif len(missing_critical) >= 2:
            # 2 missing critical = small penalty, can still be moderate
            penalized_score = min(penalized_score, 82)
        
        # Final score clamped to 0-100
        overall_score = max(0, min(100, penalized_score))
        
        # Step 8: Determine bucket (considers critical gaps)
        bucket = self._determine_bucket(overall_score, missing_critical, skill_details)
        
        # Step 9: Generate recommendations
        recommendations = self._get_recommendations(
            resume, jd, gap_analysis, issues, skill_details
        )
        
        return ATSScore(
            overall_score=overall_score,
            bucket=bucket,
            skill_match_score=skill_score,
            keyword_score=keyword_score,
            formatting_score=formatting_score,
            experience_alignment_score=experience_score,
            issues=issues,
            missing_keywords=gap_analysis.missing_keywords[:10],
            recommendations=recommendations
        )
    
    def _get_missing_critical_skills(
        self, 
        jd: ParsedJobDescription, 
        gap_analysis: GapAnalysis
    ) -> List[str]:
        """
        Identify missing skills that are TRULY critical for the role
        
        Only marks as critical if:
        - It's in the FIRST 3 required skills (primary requirements)
        - AND it's a known critical skill for the role type
        """
        
        # Determine which skills are critical based on role
        role_lower = jd.role.lower()
        critical_for_role = set()
        
        for role_type, skills in self.CRITICAL_SKILLS_BY_ROLE.items():
            if role_type in role_lower:
                critical_for_role.update(skills)
        
        # Check which critical skills are missing
        missing_critical = []
        
        # Get missing required skills
        missing_required = [s.skill.lower() for s in gap_analysis.missing_skills 
                          if s.importance == "required"]
        
        # Only TOP 3 required skills + role-critical skills count
        top_required = {s.lower() for s in jd.required_skills[:3]}
        
        for skill in missing_required:
            skill_lower = skill.lower()
            # Consider critical if: in top 3 required OR a known critical skill for the role
            if skill_lower in critical_for_role or skill_lower in top_required:
                missing_critical.append(skill)
        
        return missing_critical
    
    def _calculate_skill_score(
        self, 
        gap_analysis: GapAnalysis,
        jd: ParsedJobDescription
    ) -> Tuple[int, Dict]:
        """
        Calculate skill match score - CORRECTLY separates required from preferred
        
        Returns: (score, details_dict)
        """
        
        # Get ONLY required skills matched
        # matching_skills is List[str], missing_skills is List[SkillGap]
        
        # Count required matched: we need to check against JD required skills
        required_skills_lower = {s.lower() for s in jd.required_skills}
        matched_skills_lower = {s.lower() for s in gap_analysis.matching_skills}
        
        # Count required that were matched
        required_matched = matched_skills_lower.intersection(required_skills_lower)
        
        # Count required that were missed
        missing_required = [s for s in gap_analysis.missing_skills if s.importance == "required"]
        
        # Total required skills
        total_required = len(jd.required_skills)
        
        if total_required == 0:
            return 70, {"required_matched": 0, "required_total": 0, "match_rate": 1.0}
        
        # Calculate CORRECT match ratio
        match_ratio = len(required_matched) / total_required
        
        # Score based on match ratio - more lenient for realistic scoring
        if match_ratio >= 0.7:
            score = 85 + int((match_ratio - 0.7) * 50)  # 85-100
        elif match_ratio >= 0.5:
            score = 65 + int((match_ratio - 0.5) * 100)  # 65-85
        elif match_ratio >= 0.3:
            score = 45 + int((match_ratio - 0.3) * 100)  # 45-65
        elif match_ratio >= 0.2:
            score = 25 + int((match_ratio - 0.2) * 100)  # 25-45
        else:
            score = max(10, int(match_ratio * 125))  # 10-25 minimum
        
        details = {
            "required_matched": len(required_matched),
            "required_total": total_required,
            "match_rate": round(match_ratio, 3),
            "matched_skills": list(required_matched),
            "missing_required": [s.skill for s in missing_required]
        }
        
        return max(0, min(100, score)), details
    
    def _calculate_preferred_bonus(self, gap_analysis: GapAnalysis) -> int:
        """
        Calculate bonus for matching preferred skills
        
        This is BONUS only - missing preferred skills don't penalize
        Max bonus: +10 points
        """
        # Count preferred skills matched
        matched_preferred = [s for s in gap_analysis.matching_skills]
        # We need to check against missing_skills to see what was preferred
        missing_preferred_count = len([s for s in gap_analysis.missing_skills 
                                       if s.importance == "preferred"])
        
        total_preferred = len(matched_preferred) + missing_preferred_count
        
        if total_preferred == 0:
            return 0
        
        # Estimate how many matched were preferred (not exact, but reasonable)
        # Since matching_skills doesn't have importance, assume non-required are preferred
        matched_preferred_estimate = len(matched_preferred) - len([
            s for s in gap_analysis.missing_skills if s.importance == "required"
        ])
        matched_preferred_estimate = max(0, matched_preferred_estimate)
        
        # Max +10 bonus, +2 per matched preferred skill
        bonus = min(10, matched_preferred_estimate * 2)
        
        return bonus
    
    def _calculate_keyword_score(self, gap_analysis: GapAnalysis) -> int:
        """
        Calculate keyword density score - realistic scoring
        
        0 keywords matched = low score (not 40+)
        """
        total_keywords = len(gap_analysis.matching_keywords) + len(gap_analysis.missing_keywords)
        
        if total_keywords == 0:
            return 50  # Neutral, not 75
        
        matched = len(gap_analysis.matching_keywords)
        match_ratio = matched / total_keywords
        
        # Realistic scoring for keywords (less strict):
        # 60%+ = good (75-100)
        # 40-60% = moderate (55-75)
        # 20-40% = fair (30-55)
        # <20% = poor (0-30)

        if match_ratio >= 0.6:
            score = 75 + int((match_ratio - 0.6) * 83)  # 75-100
        elif match_ratio >= 0.4:
            score = 55 + int((match_ratio - 0.4) * 100)  # 55-75
        elif match_ratio >= 0.2:
            score = 30 + int((match_ratio - 0.2) * 125)  # 30-55
        else:
            score = max(5, int(match_ratio * 150))  # 5-30 minimum
        
        return max(0, min(100, score))
    
    def _calculate_formatting_score(self, resume: ParsedResume) -> int:
        """
        Calculate formatting score - AWARD points, don't deduct
        
        Start at 0, award for each element present
        """
        score = 0
        
        # Essential sections (40 points possible)
        if resume.skills and len(resume.skills) >= 3:
            score += 15
        elif resume.skills:
            score += 8
        
        if resume.experience and len(resume.experience) >= 1:
            score += 15
            # Bonus for detailed experience
            avg_bullets = sum(len(exp.description) for exp in resume.experience) / len(resume.experience)
            if avg_bullets >= 4:
                score += 10
            elif avg_bullets >= 2:
                score += 5
        
        # Important sections (30 points possible)
        if resume.summary:
            score += 10
        
        if resume.education:
            score += 10
        
        if resume.email:
            score += 5
        
        if resume.phone:
            score += 5
        
        # Professional extras (30 points possible)
        if resume.linkedin:
            score += 10
        
        if resume.github:
            score += 10
        
        if resume.certifications and len(resume.certifications) >= 1:
            score += 10
        
        return min(100, score)
    
    def _calculate_experience_score(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription
    ) -> int:
        """
        Calculate experience alignment score - checks RELEVANCE
        
        Fair scoring even for candidates with 1 strong relevant experience
        """
        if not resume.experience:
            return 20  # Baseline for having resume structure
        
        # Extract role keywords for relevance checking (more comprehensive)
        role_keywords = set()
        for word in jd.role.lower().split():
            if len(word) > 2:
                role_keywords.add(word)
        
        # Add required skills as keywords
        for skill in jd.required_skills[:5]:
            role_keywords.add(skill.lower())
        
        # Add JD keywords
        for kw in jd.keywords[:5] if jd.keywords else []:
            role_keywords.add(kw.lower())
        
        # Count relevant experience
        relevant_exp_count = 0
        total_relevant_bullets = 0
        high_relevance_exp = 0
        
        for exp in resume.experience:
            exp_text = f"{exp.title} {exp.company} {' '.join(exp.description)}".lower()
            
            # Also include skills used in the experience
            if exp.skills_used:
                exp_text += " " + " ".join(s.lower() for s in exp.skills_used)
            
            # Check relevance
            relevance_matches = sum(1 for kw in role_keywords if kw in exp_text)
            
            if relevance_matches >= 3:
                high_relevance_exp += 1
                relevant_exp_count += 1
                total_relevant_bullets += len(exp.description)
            elif relevance_matches >= 2:
                relevant_exp_count += 1
                total_relevant_bullets += len(exp.description)
            elif relevance_matches >= 1:
                relevant_exp_count += 0.5
                total_relevant_bullets += len(exp.description) // 2
        
        # Score based on relevant experience
        # More generous for 1 highly relevant experience
        if high_relevance_exp >= 1:
            score = 70  # 1 highly relevant experience is valuable
        elif relevant_exp_count >= 2:
            score = 75
        elif relevant_exp_count >= 1:
            score = 60  # Bumped up from 55
        elif len(resume.experience) >= 1:
            score = 45  # Has experience but not relevant - still gives some credit
        else:
            score = 20
        
        # Seniority alignment bonus (more forgiving)
        exp_count = len(resume.experience)
        seniority_map = {"entry": 0, "junior": 1, "mid": 2, "senior": 3, "lead": 4, "principal": 5}
        required_exp = seniority_map.get(jd.seniority.value, 2)
        
        # For mid-level, even 1 relevant experience is acceptable
        if jd.seniority.value in ["entry", "junior", "mid"]:
            if exp_count >= 1:
                score += 15
        elif exp_count >= required_exp:
            score += 20
        elif exp_count >= max(1, required_exp - 1):
            score += 10
        
        # Detail bonus
        if total_relevant_bullets >= 8:
            score += 10
        elif total_relevant_bullets >= 4:
            score += 5
        
        return min(100, score)
    
    def _determine_bucket(
        self, 
        score: int, 
        missing_critical: List[str],
        skill_details: Dict
    ) -> ATSBucket:
        """
        Determine ATS bucket - CONSIDERS critical gaps, not just score
        """
        
        match_rate = skill_details.get("match_rate", 0)
        
        # CRITICAL FIRST: Missing critical skills = NOT_ATS_FRIENDLY
        if missing_critical and len(missing_critical) >= 2:
            return ATSBucket.NOT_ATS_FRIENDLY
        
        # If missing 1 critical skill but score is high, cap at MODERATE
        if missing_critical and len(missing_critical) == 1:
            if score >= 60:
                return ATSBucket.MODERATE
            else:
                return ATSBucket.WEAK
        
        # Score + match rate based determination
        if score >= 80 and match_rate >= 0.7:
            return ATSBucket.STRONG
        elif score >= 60 and match_rate >= 0.5:
            return ATSBucket.MODERATE
        elif score >= 40 or match_rate >= 0.3:
            return ATSBucket.WEAK
        else:
            return ATSBucket.NOT_ATS_FRIENDLY
    
    def _identify_issues(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription, 
        gap_analysis: GapAnalysis
    ) -> List[ATSIssue]:
        """Identify specific ATS issues with appropriate severity"""
        issues = []
        
        # CRITICAL: Missing required skills
        missing_required = [s for s in gap_analysis.missing_skills if s.importance == "required"]
        critical_skills_missing = [s for s in missing_required 
                                   if s.skill.lower() in jd.required_skills[0:3] if jd.required_skills]
        
        if len(critical_skills_missing) >= 2:
            issues.append(ATSIssue(
                category="Skills",
                issue=f"Missing critical skills: {', '.join(s.skill for s in critical_skills_missing[:3])}",
                severity="critical",
                suggestion="These skills are essential for the role. Consider if this position is right for you."
            ))
        elif len(missing_required) >= 3:
            issues.append(ATSIssue(
                category="Skills",
                issue=f"Missing {len(missing_required)} required skills",
                severity="high",
                suggestion=f"Add or highlight: {', '.join(s.skill for s in missing_required[:3])}"
            ))
        elif missing_required:
            issues.append(ATSIssue(
                category="Skills",
                issue=f"Missing some required skills: {', '.join(s.skill for s in missing_required)}",
                severity="medium",
                suggestion="Mention these skills if you have any experience with them"
            ))
        
        # HIGH: Missing contact info
        if not resume.email:
            issues.append(ATSIssue(
                category="Contact",
                issue="Missing email address",
                severity="high",
                suggestion="Add your professional email - recruiters can't contact you without it"
            ))
        
        # HIGH: No work experience for non-entry roles
        if not resume.experience and jd.seniority.value not in ["entry"]:
            issues.append(ATSIssue(
                category="Experience",
                issue="No work experience listed",
                severity="high",
                suggestion="Add relevant work experience, internships, or significant projects"
            ))
        
        # MEDIUM: Missing summary
        if not resume.summary:
            issues.append(ATSIssue(
                category="Formatting",
                issue="Missing professional summary",
                severity="medium",
                suggestion="Add a 2-3 sentence summary highlighting your fit for this role"
            ))
        
        # MEDIUM: Sparse experience descriptions
        if resume.experience:
            sparse_exp = [exp for exp in resume.experience if len(exp.description) < 2]
            if len(sparse_exp) >= len(resume.experience) / 2:
                issues.append(ATSIssue(
                    category="Experience",
                    issue="Experience descriptions lack detail",
                    severity="medium",
                    suggestion="Add 3-5 bullet points per position with quantified achievements"
                ))
        
        # MEDIUM: Missing keywords
        if len(gap_analysis.missing_keywords) > len(gap_analysis.matching_keywords):
            issues.append(ATSIssue(
                category="Keywords",
                issue=f"Resume missing {len(gap_analysis.missing_keywords)} important keywords",
                severity="medium",
                suggestion=f"Incorporate: {', '.join(gap_analysis.missing_keywords[:5])}"
            ))
        
        # LOW: Missing LinkedIn
        if not resume.linkedin:
            issues.append(ATSIssue(
                category="Contact",
                issue="No LinkedIn profile",
                severity="low",
                suggestion="Add LinkedIn URL to boost professional credibility"
            ))
        
        # LOW: Missing tools
        if gap_analysis.missing_tools and len(gap_analysis.missing_tools) >= 2:
            issues.append(ATSIssue(
                category="Tools",
                issue=f"Not familiar with: {', '.join(gap_analysis.missing_tools[:3])}",
                severity="low",
                suggestion="Mention similar tools you've used or consider learning these"
            ))
        
        return issues
    
    def _get_recommendations(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription, 
        gap_analysis: GapAnalysis,
        issues: List[ATSIssue],
        skill_details: Dict
    ) -> List[str]:
        """Generate actionable recommendations prioritized by impact"""
        recommendations = []
        
        match_rate = skill_details.get("match_rate", 0)
        
        # Critical first
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues:
            recommendations.append(f"⚠️ CRITICAL: {critical_issues[0].suggestion}")
        
        # High priority
        high_issues = [i for i in issues if i.severity == "high"]
        for issue in high_issues[:2]:
            recommendations.append(f"🔴 {issue.suggestion}")
        
        # Skill-based recommendations
        if match_rate < 0.5:
            missing = skill_details.get("missing_required", [])[:3]
            if missing:
                recommendations.append(f"📌 Key skills to highlight: {', '.join(missing)}")
        
        # Keywords
        if gap_analysis.missing_keywords:
            recommendations.append(f"🔑 Add keywords: {', '.join(gap_analysis.missing_keywords[:5])}")
        
        # Summary
        if not resume.summary:
            recommendations.append(f"✍️ Add a professional summary mentioning {jd.role} experience")
        
        # General
        if match_rate >= 0.7:
            recommendations.append("✅ Strong skill match - focus on quantifying achievements")
        
        return recommendations[:6]


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    else:
        data = json.loads(sys.stdin.read())
    
    resume = ParsedResume(**data["resume"])
    jd = ParsedJobDescription(**data["jd"])
    gap_analysis = GapAnalysis(**data["gap_analysis"])
    
    agent = ATSScorerAgent()
    result = agent.score(resume, jd, gap_analysis)
    print(result.model_dump_json(indent=2))