"""
OUMI ATS Classifier Agent - Intelligent, Realistic ATS Classification

This classifier provides:
- Semantic skill matching with confidence scores
- Weighted skill importance (core skills matter more)
- Realistic bucket assignment based on required skills
- Detailed match breakdown with reasons
"""
import os
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
from models.schemas import ParsedResume, ParsedJobDescription, ATSBucket

# Import skill matcher
try:
    from utils.skill_matcher import SkillMatcher, SkillOntology
    MATCHER_AVAILABLE = True
except ImportError:
    MATCHER_AVAILABLE = False


class MatchReason(Enum):
    """Reason for skill match - for transparency"""
    EXACT = "exact_match"
    CASE_INSENSITIVE = "case_insensitive"
    ALIAS = "alias_match"
    SEMANTIC = "semantic_similarity"
    TEXT_FOUND = "found_in_text"
    RELATED = "related_skill"
    NO_MATCH = "not_found"


@dataclass
class SkillMatch:
    """Detailed skill match result"""
    skill: str
    matched: bool
    matched_with: Optional[str]
    confidence: float  # 0.0 - 1.0
    reason: MatchReason
    importance: str  # "required" or "preferred"


class OumiATSClassifier:
    """
    Intelligent ATS Classifier with realistic scoring
    
    Score Breakdown:
    - Required Skills: 60% (most important)
    - Preferred Skills: 10% (bonus)
    - Formatting: 15% 
    - Experience Alignment: 15%
    
    Bucket Thresholds (based on required skills match rate):
    - Strong: 70%+ required skills AND 75+ total score
    - Moderate: 50%+ required skills AND 55+ total score
    - Weak: 30%+ required skills OR 40+ total score
    - Not ATS-Friendly: Below all thresholds
    """
    
    # Skill importance weights (core skills matter more)
    SKILL_WEIGHTS = {
        # Programming languages - high importance
        "python": 1.0, "javascript": 1.0, "typescript": 1.0, "java": 1.0,
        "go": 1.0, "rust": 1.0, "c++": 1.0, "c#": 1.0,
        
        # Frameworks - high importance
        "fastapi": 1.0, "django": 1.0, "flask": 1.0, "react": 1.0,
        "nodejs": 1.0, "express": 1.0, "spring": 1.0,
        
        # Databases - high importance
        "postgresql": 1.0, "mysql": 1.0, "mongodb": 1.0, "redis": 1.0,
        "sql": 0.9, "nosql": 0.9,
        
        # DevOps/Cloud - medium-high importance
        "docker": 0.9, "kubernetes": 0.9, "aws": 0.9, "azure": 0.9, "gcp": 0.9,
        "git": 0.8, "cicd": 0.8,
        
        # Architecture - medium importance
        "microservices": 0.8, "rest": 0.8, "graphql": 0.8, "grpc": 0.8,
        "orm": 0.7, "odm": 0.7,
        
        # Practices - medium importance
        "testing": 0.7, "debugging": 0.6, "agile": 0.6,
        
        # Soft skills - lower importance (shouldn't reject candidates for these)
        "communication": 0.3, "teamwork": 0.3, "problem_solving": 0.4,
        "leadership": 0.3, "collaboration": 0.3,
    }
    
    DEFAULT_WEIGHT = 0.7  # For skills not in the weights dict
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.ontology = SkillOntology() if MATCHER_AVAILABLE else None
        self.matcher = SkillMatcher() if MATCHER_AVAILABLE else None
    
    def classify(
        self, 
        resume: ParsedResume, 
        jd: ParsedJobDescription
    ) -> Dict[str, Any]:
        """
        Classify resume against job description
        
        Returns comprehensive analysis with:
        - ats_bucket: Strong/Moderate/Weak/Not ATS-friendly
        - scores: Detailed score breakdown
        - skill_matches: List of detailed skill match results
        - confidence: Overall classification confidence
        """
        
        # Get full resume text
        resume_text = self._get_full_resume_text(resume)
        
        # Match required skills
        required_matches = self._match_skills(
            jd.required_skills, 
            resume.skills, 
            resume_text,
            importance="required"
        )
        
        # Match preferred skills
        preferred_matches = self._match_skills(
            jd.preferred_skills,
            resume.skills,
            resume_text,
            importance="preferred"
        )
        
        # Calculate scores
        scores = self._calculate_scores(
            required_matches,
            preferred_matches,
            resume,
            jd
        )
        
        # Determine bucket
        bucket, bucket_reason = self._determine_bucket(scores)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(scores, required_matches)
        
        return {
            "ats_bucket": bucket,
            "bucket_reason": bucket_reason,
            "confidence": round(confidence, 2),
            "scores": scores,
            "skill_analysis": {
                "required": {
                    "total": len(jd.required_skills),
                    "matched": len([m for m in required_matches if m.matched]),
                    "match_rate": scores["required_match_rate"],
                    "details": [self._skill_match_to_dict(m) for m in required_matches]
                },
                "preferred": {
                    "total": len(jd.preferred_skills),
                    "matched": len([m for m in preferred_matches if m.matched]),
                    "match_rate": scores["preferred_match_rate"],
                    "details": [self._skill_match_to_dict(m) for m in preferred_matches]
                }
            },
            "recommendations": self._generate_recommendations(
                required_matches, preferred_matches, scores
            )
        }
    
    def _get_full_resume_text(self, resume: ParsedResume) -> str:
        """Compile all resume text for matching"""
        parts = [resume.raw_text]
        
        for exp in resume.experience:
            parts.extend([exp.title, exp.company])
            parts.extend(exp.description)
            parts.extend(exp.skills_used)
        
        for proj in resume.projects:
            parts.extend([proj.name, proj.description])
            parts.extend(proj.technologies)
        
        parts.extend(resume.certifications)
        
        return " ".join(filter(None, parts))
    
    def _match_skills(
        self,
        jd_skills: List[str],
        resume_skills: List[str],
        resume_text: str,
        importance: str
    ) -> List[SkillMatch]:
        """Match skills with detailed results"""
        
        results = []
        resume_skills_lower = {s.lower(): s for s in resume_skills}
        resume_text_lower = resume_text.lower()
        
        for jd_skill in jd_skills:
            match = self._match_single_skill(
                jd_skill, 
                resume_skills_lower, 
                resume_text_lower,
                resume_skills
            )
            match.importance = importance
            results.append(match)
        
        return results
    
    def _match_single_skill(
        self,
        jd_skill: str,
        resume_skills_lower: Dict[str, str],
        resume_text_lower: str,
        resume_skills: List[str]
    ) -> SkillMatch:
        """Match a single skill with confidence and reason"""
        
        jd_skill_lower = jd_skill.lower().strip()
        
        # 1. EXACT MATCH (highest confidence)
        if jd_skill_lower in resume_skills_lower:
            return SkillMatch(
                skill=jd_skill,
                matched=True,
                matched_with=resume_skills_lower[jd_skill_lower],
                confidence=1.0,
                reason=MatchReason.EXACT,
                importance=""
            )
        
        # 2. CASE-INSENSITIVE PARTIAL MATCH
        for rs_lower, rs_original in resume_skills_lower.items():
            if jd_skill_lower in rs_lower or rs_lower in jd_skill_lower:
                return SkillMatch(
                    skill=jd_skill,
                    matched=True,
                    matched_with=rs_original,
                    confidence=0.95,
                    reason=MatchReason.CASE_INSENSITIVE,
                    importance=""
                )
        
        # 3. ONTOLOGY/ALIAS MATCH
        if self.ontology:
            jd_normalized = self.ontology.normalize(jd_skill)
            for rs in resume_skills:
                rs_normalized = self.ontology.normalize(rs)
                if jd_normalized == rs_normalized:
                    return SkillMatch(
                        skill=jd_skill,
                        matched=True,
                        matched_with=rs,
                        confidence=0.9,
                        reason=MatchReason.ALIAS,
                        importance=""
                    )
        
        # 4. TEXT SEARCH (skill mentioned in resume but not in skills list)
        if self._skill_in_text(jd_skill_lower, resume_text_lower):
            return SkillMatch(
                skill=jd_skill,
                matched=True,
                matched_with=f"[found in resume text]",
                confidence=0.85,
                reason=MatchReason.TEXT_FOUND,
                importance=""
            )
        
        # 5. SEMANTIC MATCH (if matcher available)
        if self.matcher and resume_skills:
            is_match, conf, matched_with = self.matcher.match_skill(
                jd_skill, resume_skills, resume_text_lower
            )
            if is_match and conf >= 0.75:
                return SkillMatch(
                    skill=jd_skill,
                    matched=True,
                    matched_with=matched_with,
                    confidence=conf,
                    reason=MatchReason.SEMANTIC,
                    importance=""
                )
        
        # 6. RELATED SKILL CHECK (lower confidence)
        if self.ontology:
            related = self.ontology.get_related(jd_skill)
            for rel in related:
                rel_lower = rel.lower()
                if rel_lower in resume_skills_lower:
                    return SkillMatch(
                        skill=jd_skill,
                        matched=True,
                        matched_with=f"{resume_skills_lower[rel_lower]} (related)",
                        confidence=0.7,
                        reason=MatchReason.RELATED,
                        importance=""
                    )
        
        # NO MATCH
        return SkillMatch(
            skill=jd_skill,
            matched=False,
            matched_with=None,
            confidence=0.0,
            reason=MatchReason.NO_MATCH,
            importance=""
        )
    
    def _skill_in_text(self, skill: str, text: str) -> bool:
        """Check if skill is mentioned in text with word boundaries"""
        # Handle compound skills
        skill_parts = skill.replace('-', ' ').replace('/', ' ').split()
        
        # For single-word skills, use word boundary
        if len(skill_parts) == 1:
            pattern = r'\b' + re.escape(skill) + r'\b'
            return bool(re.search(pattern, text, re.IGNORECASE))
        
        # For compound skills, check if main part is present
        main_parts = [p for p in skill_parts if len(p) >= 4]
        if main_parts:
            for part in main_parts:
                pattern = r'\b' + re.escape(part) + r'\b'
                if re.search(pattern, text, re.IGNORECASE):
                    return True
        
        return False
    
    def _get_skill_weight(self, skill: str) -> float:
        """Get importance weight for a skill"""
        skill_lower = skill.lower()
        
        # Check exact match
        if skill_lower in self.SKILL_WEIGHTS:
            return self.SKILL_WEIGHTS[skill_lower]
        
        # Check normalized form
        if self.ontology:
            normalized = self.ontology.normalize(skill)
            if normalized in self.SKILL_WEIGHTS:
                return self.SKILL_WEIGHTS[normalized]
        
        return self.DEFAULT_WEIGHT
    
    def _calculate_scores(
        self,
        required_matches: List[SkillMatch],
        preferred_matches: List[SkillMatch],
        resume: ParsedResume,
        jd: ParsedJobDescription
    ) -> Dict[str, Any]:
        """Calculate detailed scores with proper weighting"""
        
        # Required skills score (60 points max, weighted)
        if required_matches:
            total_weight = sum(
                self._get_skill_weight(m.skill) 
                for m in required_matches
            )
            matched_weight = sum(
                self._get_skill_weight(m.skill) * m.confidence
                for m in required_matches if m.matched
            )
            required_match_rate = matched_weight / max(total_weight, 1)
            required_score = required_match_rate * 60
        else:
            required_match_rate = 1.0  # No requirements = full match
            required_score = 60
        
        # Preferred skills score (10 points bonus)
        if preferred_matches:
            preferred_matched = len([m for m in preferred_matches if m.matched])
            preferred_match_rate = preferred_matched / len(preferred_matches)
            preferred_score = preferred_match_rate * 10
        else:
            preferred_match_rate = 0.0
            preferred_score = 0
        
        # Formatting score (15 points max)
        formatting_score = 0
        formatting_issues = []
        
        if resume.summary:
            formatting_score += 3
        else:
            formatting_issues.append("Missing professional summary")
        
        if resume.experience:
            formatting_score += 4
            avg_bullets = sum(len(e.description) for e in resume.experience) / len(resume.experience)
            if avg_bullets >= 3:
                formatting_score += 3
            elif avg_bullets >= 2:
                formatting_score += 1
                formatting_issues.append("Experience bullets could be more detailed")
        else:
            formatting_issues.append("No work experience listed")
        
        if resume.education:
            formatting_score += 2
        
        if resume.email and resume.phone:
            formatting_score += 2
        elif resume.email or resume.phone:
            formatting_score += 1
            formatting_issues.append("Missing complete contact info")
        
        if resume.skills and len(resume.skills) >= 5:
            formatting_score += 1
        
        # Experience alignment score (15 points max)
        experience_score = 0
        
        # Check if role keywords appear in experience
        role_words = [w.lower() for w in jd.role.split() if len(w) > 3]
        has_role_match = False
        for exp in resume.experience:
            exp_text = f"{exp.title} {exp.company} {' '.join(exp.description)}".lower()
            if any(word in exp_text for word in role_words):
                has_role_match = True
                break
        
        if has_role_match:
            experience_score += 8
        
        # Seniority check
        exp_count = len(resume.experience)
        seniority_map = {"entry": 0, "junior": 1, "mid": 2, "senior": 4, "lead": 5}
        required_exp = seniority_map.get(jd.seniority.value, 2)
        
        if exp_count >= required_exp:
            experience_score += 7
        elif exp_count >= required_exp - 1:
            experience_score += 4
        elif exp_count >= 1:
            experience_score += 2
        
        # Total score
        total_score = required_score + preferred_score + formatting_score + experience_score
        
        return {
            "total": round(total_score, 1),
            "breakdown": {
                "required_skills": round(required_score, 1),
                "preferred_skills": round(preferred_score, 1),
                "formatting": formatting_score,
                "experience": experience_score
            },
            "required_match_rate": round(required_match_rate, 3),
            "preferred_match_rate": round(preferred_match_rate, 3),
            "formatting_issues": formatting_issues
        }
    
    def _determine_bucket(self, scores: Dict) -> Tuple[str, str]:
        """
        Determine ATS bucket based on realistic thresholds
        
        Priority: Required skills match rate is the primary factor
        """
        required_rate = scores["required_match_rate"]
        total = scores["total"]
        
        # Strong: 70%+ required skills AND 75+ total
        if required_rate >= 0.70 and total >= 75:
            return "strong", f"Excellent match: {required_rate*100:.0f}% required skills, {total:.0f} total score"
        
        # Moderate: 50%+ required skills AND 55+ total
        if required_rate >= 0.50 and total >= 55:
            return "moderate", f"Good match: {required_rate*100:.0f}% required skills, {total:.0f} total score"
        
        # Weak: 30%+ required skills OR 40+ total
        if required_rate >= 0.30 or total >= 40:
            return "weak", f"Partial match: {required_rate*100:.0f}% required skills, {total:.0f} total score"
        
        # Not ATS-friendly
        return "not_ats_friendly", f"Low match: {required_rate*100:.0f}% required skills, {total:.0f} total score"
    
    def _calculate_confidence(
        self, 
        scores: Dict, 
        required_matches: List[SkillMatch]
    ) -> float:
        """
        Calculate classification confidence (independent of score)
        Based on match quality and consistency
        """
        if not required_matches:
            return 0.7  # Moderate confidence when no requirements
        
        # Average confidence of matched skills
        matched = [m for m in required_matches if m.matched]
        if not matched:
            return 0.5  # Low confidence if nothing matched
        
        avg_match_confidence = sum(m.confidence for m in matched) / len(matched)
        
        # Factor in match rate
        match_rate = scores["required_match_rate"]
        
        # Higher confidence when:
        # - Many skills matched with high confidence
        # - Match rate is clear (very high or very low, not borderline)
        
        # Borderline scores (40-60%) have lower confidence
        rate_clarity = abs(match_rate - 0.5) * 2  # 0 at 50%, 1 at 0% or 100%
        
        confidence = (avg_match_confidence * 0.6) + (rate_clarity * 0.4)
        
        return min(0.95, max(0.5, confidence))
    
    def _generate_recommendations(
        self,
        required_matches: List[SkillMatch],
        preferred_matches: List[SkillMatch],
        scores: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Missing required skills
        missing_required = [m for m in required_matches if not m.matched]
        if missing_required:
            skills_list = ", ".join(m.skill for m in missing_required[:3])
            if len(missing_required) <= 3:
                recommendations.append(
                    f"Highlight experience with: {skills_list}"
                )
            else:
                recommendations.append(
                    f"Consider adding relevant experience for: {skills_list} (+{len(missing_required)-3} more)"
                )
        
        # Low confidence matches
        low_conf = [m for m in required_matches if m.matched and m.confidence < 0.8]
        if low_conf:
            skills_list = ", ".join(m.skill for m in low_conf[:2])
            recommendations.append(
                f"More explicitly mention: {skills_list}"
            )
        
        # Formatting issues
        for issue in scores.get("formatting_issues", [])[:2]:
            recommendations.append(issue)
        
        # Preferred skills bonus
        missing_preferred = [m for m in preferred_matches if not m.matched]
        if missing_preferred and len(missing_preferred) <= 3:
            skills_list = ", ".join(m.skill for m in missing_preferred)
            recommendations.append(
                f"Nice-to-have skills to consider: {skills_list}"
            )
        
        return recommendations[:5]  # Max 5 recommendations
    
    def _skill_match_to_dict(self, match: SkillMatch) -> Dict:
        """Convert SkillMatch to dictionary for JSON serialization"""
        return {
            "skill": match.skill,
            "matched": match.matched,
            "matched_with": match.matched_with,
            "confidence": round(match.confidence, 2),
            "reason": match.reason.value,
            "importance": match.importance
        }


if __name__ == "__main__":
    # Test the classifier
    import json
    from models.schemas import ParsedResume, ParsedJobDescription, Seniority, Experience, Project
    
    # Mock resume
    resume = ParsedResume(
        name="Ayush Agrawal",
        email="test@email.com",
        phone="+91-1234567890",
        skills=["Python", "FastAPI", "PostgreSQL", "MongoDB", "Docker", "Git", "REST APIs"],
        experience=[
            Experience(
                title="Associate Software Engineer",
                company="Accenture",
                duration="July 2023 - Present",
                description=[
                    "Developed RESTful APIs using Python",
                    "Worked with SQL and NoSQL databases",
                    "Built microservices architecture"
                ],
                skills_used=["Python", "SQL", "REST"]
            )
        ],
        education=[],
        projects=[
            Project(
                name="Health Dashboard",
                description="Data analytics dashboard",
                technologies=["Python", "Pandas", "Matplotlib"]
            )
        ],
        certifications=["Google Cloud Associate"],
        raw_text="Python developer with experience in FastAPI, REST APIs, microservices..."
    )
    
    # Mock JD
    jd = ParsedJobDescription(
        role="Backend Developer",
        company="AgWise",
        required_skills=["Python", "FastAPI", "MongoDB", "REST API", "Microservices", "Git"],
        preferred_skills=["Kubernetes", "Azure", "gRPC"],
        tools=["Docker", "Git"],
        seniority=Seniority.JUNIOR,
        keywords=["backend", "api", "python"]
    )
    
    classifier = OumiATSClassifier()
    result = classifier.classify(resume, jd)
    
    print(json.dumps(result, indent=2))
