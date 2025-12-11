"""
Gap Analysis Agent - Fixed SQL Matching
Enhanced with proper skill equivalences for database systems
"""
import os
import re
from enum import Enum
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass
from together import Together
from models.schemas import ParsedResume, ParsedJobDescription, GapAnalysis, SkillGap


class SkillImportance(Enum):
    """Skill importance levels for gap prioritization"""
    CRITICAL = "critical"      # Deal-breaker - auto-reject without this
    HIGH = "high"              # Heavily evaluated in interviews
    MEDIUM = "medium"          # Nice to have, won't reject
    LOW = "low"                # Minor bonus


class ReadinessLevel(Enum):
    """Overall job readiness assessment"""
    NOT_READY = "not_ready"                # Has critical gaps
    NEEDS_PREPARATION = "needs_preparation" # < 60% required skills
    MODERATELY_READY = "moderately_ready"   # 60-79% required skills
    READY = "ready"                         # 80%+ required, max 2 high gaps
    STRONG_FIT = "strong_fit"               # 90%+ match


@dataclass
class SkillMatchResult:
    """Detailed skill match result"""
    skill: str
    matched: bool
    matched_with: Optional[str]
    confidence: float
    match_strategy: str
    importance: SkillImportance


class GapAnalysisAgent:
    """
    Intelligent Gap Analysis Agent with Enhanced Skill Matching
    
    Features:
    - Skill criticality framework
    - Multi-strategy matching
    - Categorized gaps (critical/high/medium/low)
    - Readiness assessment
    - Actionable recommendations
    - **NEW:** SQL family matching (SQL → PostgreSQL/MySQL/MariaDB/SQLite)
    """
    
    # Skill importance mapping for tech roles
    SKILL_IMPORTANCE = {
        # Programming Languages - Usually Critical for role
        "python": SkillImportance.CRITICAL,
        "javascript": SkillImportance.CRITICAL,
        "typescript": SkillImportance.CRITICAL,
        "java": SkillImportance.CRITICAL,
        "go": SkillImportance.CRITICAL,
        "rust": SkillImportance.HIGH,
        "c++": SkillImportance.HIGH,
        
        # Frameworks - High to Critical based on role
        "fastapi": SkillImportance.HIGH,
        "django": SkillImportance.HIGH,
        "flask": SkillImportance.HIGH,
        "react": SkillImportance.HIGH,
        "nodejs": SkillImportance.HIGH,
        "express": SkillImportance.MEDIUM,
        "spring": SkillImportance.HIGH,
        
        # Databases - High importance
        "postgresql": SkillImportance.HIGH,
        "mysql": SkillImportance.HIGH,
        "mariadb": SkillImportance.HIGH,
        "mongodb": SkillImportance.HIGH,
        "redis": SkillImportance.MEDIUM,
        "sql": SkillImportance.HIGH,
        "nosql": SkillImportance.MEDIUM,
        "sqlite": SkillImportance.MEDIUM,
        
        # Architecture - Medium to High
        "rest": SkillImportance.HIGH,
        "rest api": SkillImportance.HIGH,
        "restful": SkillImportance.HIGH,
        "microservices": SkillImportance.MEDIUM,
        "graphql": SkillImportance.MEDIUM,
        "grpc": SkillImportance.MEDIUM,
        
        # DevOps - Medium importance
        "docker": SkillImportance.MEDIUM,
        "kubernetes": SkillImportance.MEDIUM,
        "aws": SkillImportance.MEDIUM,
        "azure": SkillImportance.MEDIUM,
        "gcp": SkillImportance.MEDIUM,
        "git": SkillImportance.HIGH,
        "cicd": SkillImportance.MEDIUM,
        
        # Tools/Patterns - Medium
        "orm": SkillImportance.MEDIUM,
        "odm": SkillImportance.MEDIUM,
        "testing": SkillImportance.MEDIUM,
        "debugging": SkillImportance.MEDIUM,
        "agile": SkillImportance.LOW,
        
        # Soft Skills - Low (shouldn't reject for these)
        "communication": SkillImportance.LOW,
        "teamwork": SkillImportance.LOW,
        "problem solving": SkillImportance.LOW,
        "leadership": SkillImportance.LOW,
    }
    
    # ENHANCED: Skill equivalences for smart matching
    # Now includes SQL → Database variants mapping
    EQUIVALENCES = {
        # SQL Database Family - CRITICAL FIX
        # "sql" maps to all SQL-based databases
        "sql": [
            "postgresql", "postgres", "psql", "pg",
            "mysql", "mariadb",
            "sqlite",
            "sql server", "mssql", "tsql",
            "oracle",
            "pl/sql", "plsql"
        ],
        
        # PostgreSQL variants
        "postgresql": ["postgres", "psql", "pg"],
        "postgres": ["postgresql", "psql", "pg"],
        "psql": ["postgresql", "postgres", "pg"],
        "pg": ["postgresql", "postgres", "psql"],
        
        # MySQL variants
        "mysql": ["mariadb", "my-sql"],
        "mariadb": ["mysql"],
        
        # SQLite
        "sqlite": ["sqlite3", "sqlite 3"],
        
        # JavaScript/TypeScript
        "javascript": ["js", "ecmascript"],
        "typescript": ["ts"],
        "nodejs": ["node", "node.js"],
        
        # Frameworks
        "fastapi": ["fast api", "fast-api"],
        
        # API Architecture
        "rest api": ["rest", "restful", "restful api", "restful apis"],
        
        # Microservices
        "microservices": ["microservice", "microservice architecture"],
        
        # Container Orchestration
        "kubernetes": ["k8s"],
        
        # CI/CD
        "cicd": ["ci/cd", "ci cd", "continuous integration"],
        
        # NoSQL
        "nosql": ["no-sql", "non-relational"],
        
        # Version Control
        "git": ["github", "gitlab", "version control", "git flow"],
        
        # Cloud Providers
        "aws": ["amazon web services", "amazon aws"],
        "azure": ["microsoft azure", "azure"],
        "gcp": ["google cloud", "google cloud platform"],
        
        # ORMs
        "orm": ["sqlalchemy", "prisma", "sequelize", "typeorm", "eloquent", "jpa"],
        "odm": ["mongoose"],
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = Together(api_key=api_key or os.getenv("TOGETHER_API_KEY"))
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self._build_equivalence_index()
    
    def _build_equivalence_index(self):
        """Build reverse index for equivalence lookup"""
        self.equiv_to_canonical = {}
        for canonical, equivalents in self.EQUIVALENCES.items():
            self.equiv_to_canonical[canonical.lower()] = canonical.lower()
            for equiv in equivalents:
                self.equiv_to_canonical[equiv.lower()] = canonical.lower()
    
    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill to canonical form"""
        skill_lower = skill.lower().strip()
        return self.equiv_to_canonical.get(skill_lower, skill_lower)
    
    def _get_skill_importance(self, skill: str) -> SkillImportance:
        """Get importance level for a skill"""
        normalized = self._normalize_skill(skill)
        return self.SKILL_IMPORTANCE.get(normalized, SkillImportance.MEDIUM)
    
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
    
    def _match_skill(
        self,
        jd_skill: str,
        resume_skills: List[str],
        resume_text: str,
        importance_type: str
    ) -> SkillMatchResult:
        """
        5-Strategy Skill Matching:
        1. Exact match → 100% confidence
        2. Equivalence match → 95% confidence
        3. Text appearance → 80% confidence
        4. Partial match → 65% confidence
        5. Related skill → 50% confidence
        
        **NEW:** Handles SQL → Database variants matching
        """
        jd_skill_lower = jd_skill.lower().strip()
        jd_normalized = self._normalize_skill(jd_skill)
        resume_skills_lower = {s.lower(): s for s in resume_skills}
        resume_skills_normalized = {self._normalize_skill(s): s for s in resume_skills}
        resume_text_lower = resume_text.lower()
        
        importance = self._get_skill_importance(jd_skill)
        
        # Strategy 1: EXACT MATCH (100% confidence)
        if jd_skill_lower in resume_skills_lower:
            return SkillMatchResult(
                skill=jd_skill,
                matched=True,
                matched_with=resume_skills_lower[jd_skill_lower],
                confidence=1.0,
                match_strategy="exact_match",
                importance=importance
            )
        
        # Strategy 2: EQUIVALENCE MATCH (95% confidence)
        if jd_normalized in resume_skills_normalized:
            return SkillMatchResult(
                skill=jd_skill,
                matched=True,
                matched_with=resume_skills_normalized[jd_normalized],
                confidence=0.95,
                match_strategy="equivalence_match",
                importance=importance
            )
        
        # Check all equivalences - INCLUDING SQL FAMILY MATCHING
        equivalents = self.EQUIVALENCES.get(jd_normalized, [])
        for equiv in equivalents:
            equiv_lower = equiv.lower()
            
            # Check in resume skills list
            if equiv_lower in resume_skills_lower:
                return SkillMatchResult(
                    skill=jd_skill,
                    matched=True,
                    matched_with=resume_skills_lower[equiv_lower],
                    confidence=0.95,
                    match_strategy="equivalence_match",
                    importance=importance
                )
            
            # Check in resume text
            if self._skill_in_text(equiv, resume_text_lower):
                return SkillMatchResult(
                    skill=jd_skill,
                    matched=True,
                    matched_with=f"[{equiv} found in resume]",
                    confidence=0.90,
                    match_strategy="equivalence_match",
                    importance=importance
                )
        
        # **SQL-SPECIFIC MATCHING** - If JD asks for SQL, check for ANY SQL database variant
        if jd_normalized == "sql":
            sql_variants = [
                "postgresql", "postgres", "psql", "pg",
                "mysql", "mariadb",
                "sqlite", "sqlite3",
                "sql server", "mssql", "oracle"
            ]
            
            for variant in sql_variants:
                # Check in resume skills
                if variant in resume_skills_lower:
                    return SkillMatchResult(
                        skill=jd_skill,
                        matched=True,
                        matched_with=resume_skills_lower[variant],
                        confidence=0.95,
                        match_strategy="sql_family_match",
                        importance=importance
                    )
                
                # Check normalized equivalents
                if self._normalize_skill(variant) in resume_skills_normalized:
                    matched_skill = resume_skills_normalized[self._normalize_skill(variant)]
                    return SkillMatchResult(
                        skill=jd_skill,
                        matched=True,
                        matched_with=matched_skill,
                        confidence=0.95,
                        match_strategy="sql_family_match",
                        importance=importance
                    )
                
                # Check in text
                if self._skill_in_text(variant, resume_text_lower):
                    return SkillMatchResult(
                        skill=jd_skill,
                        matched=True,
                        matched_with=f"[{variant.upper()}]",
                        confidence=0.90,
                        match_strategy="sql_family_match",
                        importance=importance
                    )
        
        # Strategy 3: TEXT APPEARANCE (80% confidence)
        if self._skill_in_text(jd_skill_lower, resume_text_lower):
            return SkillMatchResult(
                skill=jd_skill,
                matched=True,
                matched_with="[found in resume text]",
                confidence=0.80,
                match_strategy="text_appearance",
                importance=importance
            )
        
        # Strategy 4: PARTIAL MATCH (65% confidence)
        skill_parts = jd_skill_lower.replace('-', ' ').replace('/', ' ').split()
        main_parts = [p for p in skill_parts if len(p) >= 4 and p not in ['with', 'and', 'the', 'for']]
        
        for part in main_parts:
            if part in resume_skills_lower:
                return SkillMatchResult(
                    skill=jd_skill,
                    matched=True,
                    matched_with=resume_skills_lower[part],
                    confidence=0.65,
                    match_strategy="partial_match",
                    importance=importance
                )
            if self._skill_in_text(part, resume_text_lower):
                return SkillMatchResult(
                    skill=jd_skill,
                    matched=True,
                    matched_with=f"[{part} found in text]",
                    confidence=0.65,
                    match_strategy="partial_match",
                    importance=importance
                )
        
        # No match
        return SkillMatchResult(
            skill=jd_skill,
            matched=False,
            matched_with=None,
            confidence=0.0,
            match_strategy="no_match",
            importance=importance
        )
    
    def _skill_in_text(self, skill: str, text: str) -> bool:
        """Check if skill appears in text with word boundaries"""
        escaped = re.escape(skill)
        pattern = r'\b' + escaped + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def analyze(self, resume: ParsedResume, jd: ParsedJobDescription) -> GapAnalysis:
        """Perform comprehensive gap analysis"""
        resume_text = self._get_full_resume_text(resume)
        
        # Match required skills
        required_matches = [
            self._match_skill(skill, resume.skills, resume_text, "required")
            for skill in jd.required_skills
        ]
        
        # Match preferred skills
        preferred_matches = [
            self._match_skill(skill, resume.skills, resume_text, "preferred")
            for skill in jd.preferred_skills
        ]
        
        # Match tools
        tools_matches = [
            self._match_skill(tool, resume.skills, resume_text, "tool")
            for tool in jd.tools
        ]
        
        # Match keywords
        keywords_matches = [
            self._match_skill(kw, resume.skills, resume_text, "keyword")
            for kw in jd.keywords
        ]
        
        # Categorize gaps
        gaps = self._categorize_gaps(required_matches, preferred_matches)
        
        # Calculate readiness
        readiness = self._assess_readiness(required_matches, gaps)
        
        # Build standard GapAnalysis response
        matching_skills = [m.skill for m in required_matches if m.matched]
        matching_skills += [m.skill for m in preferred_matches if m.matched and m.skill not in matching_skills]
        
        missing_skill_gaps = []
        for m in required_matches:
            if not m.matched:
                missing_skill_gaps.append(SkillGap(
                    skill=m.skill,
                    importance="required",
                    category=m.importance.value
                ))
        for m in preferred_matches:
            if not m.matched:
                missing_skill_gaps.append(SkillGap(
                    skill=m.skill,
                    importance="preferred",
                    category=m.importance.value
                ))
        
        matching_tools = [m.skill for m in tools_matches if m.matched]
        missing_tools = [m.skill for m in tools_matches if not m.matched]
        
        matching_keywords = [m.skill for m in keywords_matches if m.matched]
        missing_keywords = [m.skill for m in keywords_matches if not m.matched]
        
        # Calculate overall match (weighted by importance)
        overall_match = self._calculate_weighted_match(required_matches, preferred_matches)
        
        # Experience check
        experience_match = len(resume.experience) > 0
        seniority_match = self._check_seniority(resume, jd)
        
        # Generate insights
        strengths = self._generate_strengths(resume, required_matches, matching_skills)
        weaknesses = self._generate_weaknesses(gaps, missing_skill_gaps)
        
        return GapAnalysis(
            matching_skills=matching_skills,
            missing_skills=missing_skill_gaps,
            matching_tools=matching_tools,
            missing_tools=missing_tools,
            matching_keywords=matching_keywords,
            missing_keywords=missing_keywords,
            experience_match=experience_match,
            seniority_match=seniority_match,
            overall_match_percentage=round(overall_match, 1),
            strengths=strengths,
            weaknesses=weaknesses
        )
    
    def _categorize_gaps(
        self,
        required_matches: List[SkillMatchResult],
        preferred_matches: List[SkillMatchResult]
    ) -> Dict[str, List[str]]:
        """Categorize missing skills by priority"""
        gaps = {
            "critical": [],
            "high_priority": [],
            "medium_priority": [],
            "low_priority": []
        }
        
        for match in required_matches:
            if not match.matched:
                if match.importance == SkillImportance.CRITICAL:
                    gaps["critical"].append(match.skill)
                elif match.importance == SkillImportance.HIGH:
                    gaps["high_priority"].append(match.skill)
                elif match.importance == SkillImportance.MEDIUM:
                    gaps["medium_priority"].append(match.skill)
                else:
                    gaps["low_priority"].append(match.skill)
        
        for match in preferred_matches:
            if not match.matched:
                if match.importance in [SkillImportance.CRITICAL, SkillImportance.HIGH]:
                    gaps["medium_priority"].append(match.skill)
                else:
                    gaps["low_priority"].append(match.skill)
        
        return gaps
    
    def _assess_readiness(
        self,
        required_matches: List[SkillMatchResult],
        gaps: Dict[str, List[str]]
    ) -> ReadinessLevel:
        """Assess overall job readiness"""
        if not required_matches:
            return ReadinessLevel.MODERATELY_READY
        
        if gaps["critical"]:
            return ReadinessLevel.NOT_READY
        
        matched = len([m for m in required_matches if m.matched])
        match_rate = matched / len(required_matches)
        
        if match_rate >= 0.9 and len(gaps["high_priority"]) <= 1:
            return ReadinessLevel.STRONG_FIT
        
        if match_rate >= 0.8 and len(gaps["high_priority"]) <= 2:
            return ReadinessLevel.READY
        
        if match_rate >= 0.6:
            return ReadinessLevel.MODERATELY_READY
        
        return ReadinessLevel.NEEDS_PREPARATION
    
    def _calculate_weighted_match(
        self,
        required_matches: List[SkillMatchResult],
        preferred_matches: List[SkillMatchResult]
    ) -> float:
        """Calculate weighted match percentage"""
        importance_weights = {
            SkillImportance.CRITICAL: 1.0,
            SkillImportance.HIGH: 0.8,
            SkillImportance.MEDIUM: 0.5,
            SkillImportance.LOW: 0.2
        }
        
        total_weight = 0
        matched_weight = 0
        
        for m in required_matches:
            weight = importance_weights.get(m.importance, 0.5)
            total_weight += weight
            if m.matched:
                matched_weight += weight * m.confidence
        
        for m in preferred_matches:
            weight = importance_weights.get(m.importance, 0.5) * 0.3
            total_weight += weight
            if m.matched:
                matched_weight += weight * m.confidence
        
        if total_weight == 0:
            return 70.0
        
        return (matched_weight / total_weight) * 100
    
    def _check_seniority(self, resume: ParsedResume, jd: ParsedJobDescription) -> bool:
        """Check if experience level matches seniority requirement"""
        exp_count = len(resume.experience)
        seniority_requirements = {
            "entry": 0,
            "junior": 1,
            "mid": 2,
            "senior": 4,
            "lead": 5,
            "principal": 7
        }
        required = seniority_requirements.get(jd.seniority.value, 2)
        return exp_count >= max(0, required - 1)
    
    def _generate_strengths(
        self,
        resume: ParsedResume,
        required_matches: List[SkillMatchResult],
        matching_skills: List[str]
    ) -> List[str]:
        """Generate meaningful strengths list"""
        strengths = []
        
        high_conf_matches = [m for m in required_matches if m.matched and m.confidence >= 0.9]
        if len(high_conf_matches) >= 3:
            strengths.append(f"Strong match on {len(high_conf_matches)} core skills")
        
        critical_matched = [m for m in required_matches 
                          if m.matched and m.importance == SkillImportance.CRITICAL]
        if critical_matched:
            skills_str = ", ".join(m.skill for m in critical_matched[:3])
            strengths.append(f"Has critical skills: {skills_str}")
        
        if resume.experience:
            total_bullets = sum(len(exp.description) for exp in resume.experience)
            if total_bullets >= 10:
                strengths.append("Detailed work experience with quantified achievements")
            elif total_bullets >= 5:
                strengths.append("Solid work experience")
        
        if resume.certifications:
            strengths.append(f"Professional certifications: {', '.join(resume.certifications[:2])}")
        
        if len(resume.projects) >= 2:
            strengths.append("Demonstrated hands-on project experience")
        
        if resume.summary and resume.linkedin:
            strengths.append("Complete professional profile")
        
        if not strengths:
            strengths.append("Resume shows relevant background")
        
        return strengths[:5]
    
    def _generate_weaknesses(
        self,
        gaps: Dict[str, List[str]],
        missing_skills: List[SkillGap]
    ) -> List[str]:
        """Generate actionable weaknesses/recommendations"""
        weaknesses = []
        
        if gaps["critical"]:
            skills_str = ", ".join(gaps["critical"][:3])
            weaknesses.append(f"🔴 Critical: Missing {skills_str} - required for role")
        
        if gaps["high_priority"]:
            skills_str = ", ".join(gaps["high_priority"][:3])
            weaknesses.append(f"🟠 High Priority: Strengthen {skills_str}")
        
        if gaps["medium_priority"] and not gaps["critical"]:
            skills_str = ", ".join(gaps["medium_priority"][:2])
            weaknesses.append(f"🟡 Consider highlighting: {skills_str}")
        
        if not weaknesses:
            if gaps["low_priority"]:
                weaknesses.append("Minor gaps in preferred skills - mention in cover letter")
            else:
                weaknesses.append("Strong match - focus on demonstrating experience in interviews")
        
        return weaknesses[:4]


if __name__ == "__main__":
    import sys
    import json
    
    # CLI usage for Kestra
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    else:
        data = json.loads(sys.stdin.read())
    
    resume = ParsedResume(**data["resume"])
    jd = ParsedJobDescription(**data["jd"])
    
    agent = GapAnalysisAgent()
    result = agent.analyze(resume, jd)
    print(result.model_dump_json(indent=2))