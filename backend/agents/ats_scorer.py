"""
ATS Scoring Agent - Improved Logic with Fair Scoring

Key Improvements:
1. ✅ Graduated penalty system (not flat -15 for all critical)
2. ✅ Bucket alignment with external OUMI classifier
3. ✅ Integer-only experience counting
4. ✅ More realistic score ranges
5. ✅ Better handling of edge cases
"""
import os
import re
from typing import Optional, List, Dict, Tuple
from together import Together
from models.schemas import (
    ParsedResume, ParsedJobDescription, GapAnalysis,
    ATSScore, ATSBucket, ATSIssue, SkillGap
)


class ATSScorerAgent:
    """
    ATS Scoring Agent with balanced, fair scoring
    
    Score Breakdown:
    - Required Skills: 40% (most critical)
    - Keywords: 20%
    - Formatting: 20%
    - Experience Alignment: 20%
    - Preferred Skills Bonus: up to +10
    
    Scoring Philosophy:
    - 80+: Strong candidate, good match
    - 60-79: Moderate candidate, worth reviewing
    - 40-59: Weak candidate, significant gaps
    - <40: Not ATS friendly, poor match
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
    
    # GRADUATED penalty system - fairer than flat penalties
    SEVERITY_PENALTIES = {
        "critical": lambda count: min(-8 * count, -20),  # -8 per issue, max -20
        "high": lambda count: min(-4 * count, -12),      # -4 per issue, max -12
        "medium": lambda count: min(-2 * count, -6),     # -2 per issue, max -6
        "low": lambda count: min(-1 * count, -3)         # -1 per issue, max -3
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = Together(api_key=api_key or os.getenv("TOGETHER_API_KEY"))
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    
    def score(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription, 
        gap_analysis: GapAnalysis
    ) -> ATSScore:
        """Calculate comprehensive, accurate ATS score"""
        
        # Step 1: Calculate component scores
        skill_score, skill_details = self._calculate_skill_score(gap_analysis, jd)
        keyword_score = self._calculate_keyword_score(gap_analysis)
        formatting_score = self._calculate_formatting_score(resume)
        experience_score = self._calculate_experience_score(resume, jd)
        preferred_bonus = self._calculate_preferred_bonus(gap_analysis, jd)

        # Step 2: Calculate base score (weighted)
        base_score = int(
            skill_score * 0.40 +      # Required skills: 40%
            keyword_score * 0.20 +     # Keywords: 20%
            formatting_score * 0.20 +  # Formatting: 20%
            experience_score * 0.20    # Experience: 20%
        )

        # Step 3: Add preferred skills bonus (max +10)
        base_score += preferred_bonus

        # Step 4: Identify issues and apply GRADUATED penalties
        issues = self._identify_issues(resume, jd, gap_analysis)
        issue_penalty = self._calculate_issue_penalty(issues)
        penalized_score = base_score + issue_penalty

        # Step 5: Check for critical blockers
        missing_critical = self._get_missing_critical_skills(jd, gap_analysis)
        
        # Apply caps only for SEVERE blockers (more lenient)
        if len(missing_critical) >= 4:
            # 4+ critical missing = hard cap
            penalized_score = min(penalized_score, 55)
        elif len(missing_critical) >= 3:
            # 3 critical missing = moderate cap
            penalized_score = min(penalized_score, 65)
        elif len(missing_critical) == 2:
            # 2 critical missing = light cap
            penalized_score = min(penalized_score, 75)
        # 1 critical missing = no cap, let penalties handle it
        
        # Final score clamped to 0-100
        overall_score = max(0, min(100, penalized_score))
        
        # Step 6: Determine bucket (aligned with OUMI classifier expectations)
        bucket = self._determine_bucket(overall_score, missing_critical, skill_details)
        
        # Step 7: Generate recommendations
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
    
    def _calculate_issue_penalty(self, issues: List[ATSIssue]) -> int:
        """
        Calculate graduated penalty based on issue counts
        
        This prevents over-penalization from a single critical issue
        """
        # Group issues by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
        
        # Apply graduated penalties
        total_penalty = 0
        for severity, count in severity_counts.items():
            if count > 0:
                penalty_func = self.SEVERITY_PENALTIES[severity]
                total_penalty += penalty_func(count)
        
        return total_penalty
    
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
        if not jd.required_skills:
            return []
        
        # Determine which skills are critical based on role
        role_lower = jd.role.lower()
        critical_for_role = set()
        
        for role_type, skills in self.CRITICAL_SKILLS_BY_ROLE.items():
            if role_type in role_lower:
                critical_for_role.update(skills)
        
        # Get missing required skills
        missing_required = [s.skill.lower() for s in gap_analysis.missing_skills 
                          if s.importance == "required"]
        
        # Only TOP 3 required skills + role-critical skills count
        top_required = {s.lower() for s in jd.required_skills[:3]}
        
        missing_critical = []
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
        Calculate skill match score - correctly separates required from preferred
        """
        if not jd.required_skills:
            return 70, {"required_matched": 0, "required_total": 0, "match_rate": 1.0}
        
        # Count required matched
        required_skills_lower = {s.lower() for s in jd.required_skills}
        
        required_matched = set()
        for skill in gap_analysis.matching_skills:
            skill_lower = skill.lower()
            if skill_lower in required_skills_lower:
                required_matched.add(skill_lower)
        
        missing_required = [s for s in gap_analysis.missing_skills if s.importance == "required"]
        total_required = len(jd.required_skills)
        
        # Calculate match ratio
        match_ratio = len(required_matched) / total_required
        
        # More realistic scoring curve
        if match_ratio >= 0.8:
            score = 88 + int((match_ratio - 0.8) * 60)  # 88-100
        elif match_ratio >= 0.6:
            score = 72 + int((match_ratio - 0.6) * 80)  # 72-88
        elif match_ratio >= 0.4:
            score = 55 + int((match_ratio - 0.4) * 85)  # 55-72
        elif match_ratio >= 0.2:
            score = 35 + int((match_ratio - 0.2) * 100)  # 35-55
        else:
            score = max(15, int(match_ratio * 175))  # 15-35
        
        details = {
            "required_matched": len(required_matched),
            "required_total": total_required,
            "match_rate": round(match_ratio, 3),
            "matched_skills": list(required_matched),
            "missing_required": [s.skill for s in missing_required]
        }
        
        return max(0, min(100, score)), details
    
    def _calculate_preferred_bonus(
        self, 
        gap_analysis: GapAnalysis, 
        jd: ParsedJobDescription
    ) -> int:
        """Calculate bonus for matching preferred skills (max +10)"""
        if not jd.preferred_skills:
            return 0
        
        preferred_skills_lower = {s.lower() for s in jd.preferred_skills}
        matched_skills_lower = {s.lower() for s in gap_analysis.matching_skills}
        
        preferred_matched = matched_skills_lower.intersection(preferred_skills_lower)
        matched_count = len(preferred_matched)
        
        # +2 per preferred skill matched, capped at +10
        bonus = min(10, matched_count * 2)
        
        return bonus
    
    def _calculate_keyword_score(self, gap_analysis: GapAnalysis) -> int:
        """Calculate keyword density score"""
        total_keywords = len(gap_analysis.matching_keywords) + len(gap_analysis.missing_keywords)
        
        if total_keywords == 0:
            return 50  # Neutral baseline
        
        matched = len(gap_analysis.matching_keywords)
        match_ratio = matched / total_keywords
        
        # Realistic keyword scoring
        if match_ratio >= 0.7:
            score = 82 + int((match_ratio - 0.7) * 60)  # 82-100
        elif match_ratio >= 0.5:
            score = 65 + int((match_ratio - 0.5) * 85)  # 65-82
        elif match_ratio >= 0.3:
            score = 45 + int((match_ratio - 0.3) * 100)  # 45-65
        elif match_ratio >= 0.15:
            score = 25 + int((match_ratio - 0.15) * 133)  # 25-45
        else:
            score = max(10, int(match_ratio * 167))  # 10-25
        
        return max(0, min(100, score))
    
    def _calculate_formatting_score(self, resume: ParsedResume) -> int:
        """Calculate formatting score - award points for completeness"""
        score = 0
        
        # Essential sections (40 points)
        if resume.skills and len(resume.skills) >= 5:
            score += 20
        elif resume.skills and len(resume.skills) >= 3:
            score += 15
        elif resume.skills:
            score += 8
        
        if resume.experience and len(resume.experience) >= 2:
            score += 20
            # Bonus for detailed experience
            avg_bullets = sum(len(exp.description) for exp in resume.experience) / len(resume.experience)
            if avg_bullets >= 4:
                score += 5
        elif resume.experience:
            score += 15
        
        # Important sections (30 points)
        if resume.summary:
            score += 10
        
        if resume.education:
            score += 10
        
        if resume.email:
            score += 5
        
        if resume.phone:
            score += 5
        
        # Professional extras (30 points)
        if resume.linkedin:
            score += 10
        
        if resume.github:
            score += 10
        
        if resume.certifications and len(resume.certifications) >= 1:
            score += 10
        
        return min(100, score)
    
    def _count_relevance_matches(self, exp_text: str, role_keywords: set) -> int:
        """Count keyword matches using word boundaries"""
        count = 0
        for kw in role_keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, exp_text, re.IGNORECASE):
                count += 1
        return count
    
    def _calculate_experience_score(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription
    ) -> int:
        """Calculate experience alignment score - INTEGER COUNTS ONLY"""
        if not resume.experience:
            return 20
        
        # Extract role keywords
        role_keywords = set()
        if jd.role:
            for word in jd.role.lower().split():
                if len(word) > 2:
                    role_keywords.add(word)
        
        if jd.required_skills:
            for skill in jd.required_skills[:5]:
                role_keywords.add(skill.lower())
        
        if jd.keywords:
            for kw in jd.keywords[:5]:
                role_keywords.add(kw.lower())
        
        # Count relevant experience (INTEGER ONLY - NO FLOATS)
        high_relevance = 0  # 3+ keyword matches
        medium_relevance = 0  # 2 keyword matches
        low_relevance = 0  # 1 keyword match
        total_bullets = 0
        
        for exp in resume.experience:
            exp_text = f"{exp.title} {exp.company} {' '.join(exp.description)}".lower()
            
            if exp.skills_used:
                exp_text += " " + " ".join(s.lower() for s in exp.skills_used)
            
            relevance_matches = self._count_relevance_matches(exp_text, role_keywords)
            
            if relevance_matches >= 3:
                high_relevance += 1
                total_bullets += len(exp.description)
            elif relevance_matches >= 2:
                medium_relevance += 1
                total_bullets += len(exp.description)
            elif relevance_matches >= 1:
                low_relevance += 1
                total_bullets += len(exp.description) // 2
        
        # Score based on relevance (clearer thresholds)
        if high_relevance >= 2:
            score = 80
        elif high_relevance >= 1:
            score = 70
        elif medium_relevance >= 2:
            score = 65
        elif medium_relevance >= 1 or low_relevance >= 2:
            score = 55
        elif low_relevance >= 1:
            score = 45
        else:
            # Has experience but not relevant
            score = 35
        
        # Seniority alignment bonus
        exp_count = len(resume.experience)
        seniority_map = {"entry": 0, "junior": 1, "mid": 2, "senior": 3, "lead": 4, "principal": 5}
        required_exp = seniority_map.get(jd.seniority.value, 2)
        
        if jd.seniority.value in ["entry", "junior"]:
            if exp_count >= 1:
                score += 15
        elif jd.seniority.value == "mid":
            if exp_count >= 2:
                score += 15
            elif exp_count >= 1:
                score += 10
        else:
            if exp_count >= required_exp:
                score += 15
            elif exp_count >= max(1, required_exp - 1):
                score += 8
        
        # Detail bonus
        if total_bullets >= 10:
            score += 5
        elif total_bullets >= 6:
            score += 3
        
        return min(100, score)
    
    def _determine_bucket(
        self, 
        score: int, 
        missing_critical: List[str],
        skill_details: Dict
    ) -> ATSBucket:
        """
        Determine ATS bucket - ALIGNED with OUMI classifier expectations
        
        Bucket Ranges:
        - STRONG: 80+ (excellent match)
        - MODERATE: 55-79 (good enough to proceed)
        - WEAK: 35-54 (significant gaps)
        - NOT_ATS_FRIENDLY: <35 (poor match)
        """
        match_rate = skill_details.get("match_rate", 0)
        
        # Hard floor: score < 30 is always NOT_ATS_FRIENDLY
        if score < 30:
            return ATSBucket.NOT_ATS_FRIENDLY
        
        # Critical skill penalties - more lenient thresholds
        if len(missing_critical) >= 4:
            # 4+ critical missing = cap at WEAK maximum
            return ATSBucket.WEAK if score >= 35 else ATSBucket.NOT_ATS_FRIENDLY
        elif len(missing_critical) >= 3:
            # 3 critical missing = cap at WEAK, unless score is really high
            if score >= 70:
                return ATSBucket.MODERATE  # Allow moderate if other areas strong
            elif score >= 45:
                return ATSBucket.WEAK
            else:
                return ATSBucket.NOT_ATS_FRIENDLY
        elif len(missing_critical) == 2:
            # 2 critical missing = can reach MODERATE
            if score >= 65:
                return ATSBucket.MODERATE
            elif score >= 45:
                return ATSBucket.WEAK
            else:
                return ATSBucket.NOT_ATS_FRIENDLY
        elif len(missing_critical) == 1:
            # 1 critical missing = still allow MODERATE (cap at STRONG though)
            if score >= 80:
                return ATSBucket.STRONG  # If everything else is great
            elif score >= 55:
                return ATSBucket.MODERATE
            elif score >= 35:
                return ATSBucket.WEAK
            else:
                return ATSBucket.NOT_ATS_FRIENDLY
        
        # No critical gaps - score-based determination (more generous)
        if score >= 80 and match_rate >= 0.7:
            return ATSBucket.STRONG
        elif score >= 75 and match_rate >= 0.6:
            return ATSBucket.STRONG
        elif score >= 55:  # Lowered from 60
            return ATSBucket.MODERATE
        elif score >= 35:  # Lowered from 40
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
        
        # CRITICAL: Missing TOP required skills
        missing_required = [s for s in gap_analysis.missing_skills if s.importance == "required"]
        top_required = [s.lower() for s in jd.required_skills[:3]] if jd.required_skills else []
        critical_skills_missing = [s for s in missing_required if s.skill.lower() in top_required]
        
        # Only mark as CRITICAL if 2+ TOP skills missing
        if len(critical_skills_missing) >= 2:
            issues.append(ATSIssue(
                category="Skills",
                issue=f"Missing {len(critical_skills_missing)} critical required skills: {', '.join(s.skill for s in critical_skills_missing[:3])}",
                severity="critical",
                suggestion="These are essential skills for this role. Consider if this position aligns with your expertise."
            ))
        elif len(missing_required) >= 4:
            # Many required skills missing (but not necessarily top ones)
            issues.append(ATSIssue(
                category="Skills",
                issue=f"Missing {len(missing_required)} required skills",
                severity="high",
                suggestion=f"Key gaps to address: {', '.join(s.skill for s in missing_required[:4])}"
            ))
        elif len(missing_required) >= 2:
            issues.append(ATSIssue(
                category="Skills",
                issue=f"Missing some required skills: {', '.join(s.skill for s in missing_required[:3])}",
                severity="medium",
                suggestion="Highlight these skills if you have any relevant experience"
            ))
        elif missing_required:
            issues.append(ATSIssue(
                category="Skills",
                issue=f"Missing: {missing_required[0].skill}",
                severity="low",
                suggestion="Consider adding this skill if applicable"
            ))
        
        # HIGH: Missing contact info
        if not resume.email:
            issues.append(ATSIssue(
                category="Contact",
                issue="Missing email address",
                severity="high",
                suggestion="Add professional email - essential for recruiter contact"
            ))
        
        # HIGH: No experience for non-entry roles
        if not resume.experience and jd.seniority.value not in ["entry"]:
            issues.append(ATSIssue(
                category="Experience",
                issue="No work experience listed",
                severity="high",
                suggestion="Add relevant experience, internships, or major projects"
            ))
        
        # MEDIUM: Missing summary
        if not resume.summary:
            issues.append(ATSIssue(
                category="Formatting",
                issue="Missing professional summary",
                severity="medium",
                suggestion=f"Add 2-3 sentence summary highlighting {jd.role} experience"
            ))
        
        # MEDIUM: Sparse descriptions
        if resume.experience:
            sparse_count = sum(1 for exp in resume.experience if len(exp.description) < 2)
            if sparse_count >= len(resume.experience) / 2:
                issues.append(ATSIssue(
                    category="Experience",
                    issue="Experience descriptions lack detail",
                    severity="medium",
                    suggestion="Add 3-5 bullet points per role with quantified achievements"
                ))
        
        # MEDIUM: Poor keyword coverage
        if len(gap_analysis.missing_keywords) > len(gap_analysis.matching_keywords) * 1.5:
            issues.append(ATSIssue(
                category="Keywords",
                issue=f"Missing {len(gap_analysis.missing_keywords)} important keywords",
                severity="medium",
                suggestion=f"Incorporate naturally: {', '.join(gap_analysis.missing_keywords[:5])}"
            ))
        
        # LOW: Missing LinkedIn
        if not resume.linkedin:
            issues.append(ATSIssue(
                category="Contact",
                issue="No LinkedIn profile",
                severity="low",
                suggestion="Add LinkedIn URL for professional credibility"
            ))
        
        # LOW: Missing tools
        if gap_analysis.missing_tools and len(gap_analysis.missing_tools) >= 3:
            issues.append(ATSIssue(
                category="Tools",
                issue=f"Unfamiliar with: {', '.join(gap_analysis.missing_tools[:3])}",
                severity="low",
                suggestion="Mention similar tools or consider gaining exposure"
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
        """Generate prioritized, actionable recommendations"""
        recommendations = []
        
        match_rate = skill_details.get("match_rate", 0)
        
        # Critical issues first
        critical = [i for i in issues if i.severity == "critical"]
        if critical:
            recommendations.append(f"⚠️ CRITICAL: {critical[0].suggestion}")
        
        # High priority issues
        high = [i for i in issues if i.severity == "high"]
        for issue in high[:2]:
            recommendations.append(f"🔴 {issue.suggestion}")
        
        # Skill recommendations
        if match_rate < 0.6:
            missing = skill_details.get("missing_required", [])[:3]
            if missing:
                recommendations.append(f"📌 Priority skills: {', '.join(missing)}")
        
        # Keyword incorporation
        if gap_analysis.missing_keywords:
            top_keywords = gap_analysis.missing_keywords[:5]
            recommendations.append(f"🔑 Add keywords: {', '.join(top_keywords)}")
        
        # Summary recommendation
        if not resume.summary:
            recommendations.append(f"✍️ Add summary mentioning {jd.role} expertise")
        
        # Positive reinforcement
        if match_rate >= 0.7:
            recommendations.append("✅ Strong skill match - focus on quantifying impact")
        elif match_rate >= 0.5:
            recommendations.append("📊 Good foundation - strengthen with specific examples")
        
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