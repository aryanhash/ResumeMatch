"""
Skill Agent - Ethically enhances and clarifies skill representation

IMPORTANT: This agent NEVER adds fake skills or fabricates experience

Fixed Issues:
1. ✅ Stronger validation with word boundaries (not substring)
2. ✅ Evidence tracking for skills
3. ✅ Skill level extraction (beginner/intermediate/advanced)
4. ✅ Synonym handling and deduplication
5. ✅ Skill-experience alignment checking
6. ✅ Better categorization with predefined categories
7. ✅ Validation of experience-extracted skills
"""
import json
import os
import re
import logging
from typing import Optional, Dict, List, Set, Any
from together import Together
from models.schemas import ParsedResume

logger = logging.getLogger(__name__)


class SkillAgent:
    """
    Agent responsible for ethical skill enhancement and clarity
    
    This agent:
    ✅ Improves clarity on existing skills
    ✅ Removes vague language
    ✅ Adds metrics where possible
    ✅ Standardizes skill names
    ✅ Tracks skill levels and evidence
    
    This agent NEVER:
    ❌ Adds fake skills
    ❌ Claims experience user doesn't have
    ❌ Invents certifications
    ❌ Inflates skill levels
    """
    
    # Skill synonyms for deduplication and standardization
    SKILL_SYNONYMS = {
        "javascript": ["js", "javascript", "ecmascript", "es6", "es2015"],
        "typescript": ["ts", "typescript"],
        "python": ["python", "python3", "py"],
        "kubernetes": ["k8s", "kubernetes", "kube"],
        "postgresql": ["postgres", "postgresql", "psql", "pg"],
        "mongodb": ["mongo", "mongodb", "mongo db"],
        "docker": ["docker", "containerization", "containers"],
        "react": ["react", "reactjs", "react.js"],
        "nodejs": ["node", "nodejs", "node.js"],
        "fastapi": ["fastapi", "fast api", "fast-api"],
        "rest api": ["rest", "restful", "rest api", "restful api"],
        "ci/cd": ["cicd", "ci/cd", "ci cd", "continuous integration", "continuous deployment"],
        "aws": ["aws", "amazon web services"],
        "azure": ["azure", "microsoft azure"],
        "gcp": ["gcp", "google cloud", "google cloud platform"],
        "git": ["git", "github", "gitlab", "version control"],
        "sql": ["sql", "structured query language"],
        "nosql": ["nosql", "no-sql", "non-relational"],
        "machine learning": ["ml", "machine learning"],
        "artificial intelligence": ["ai", "artificial intelligence"],
    }
    
    # Predefined skill categories
    SKILL_CATEGORIES = {
        "Programming Languages": [
            "python", "javascript", "typescript", "java", "go", "rust", 
            "c++", "c#", "ruby", "php", "swift", "kotlin", "scala"
        ],
        "Frontend Frameworks": [
            "react", "vue", "angular", "svelte", "next.js", "nuxt"
        ],
        "Backend Frameworks": [
            "fastapi", "django", "flask", "express", "spring", "rails", ".net", "nodejs"
        ],
        "Databases": [
            "postgresql", "mysql", "mongodb", "redis", "sqlite", "oracle", 
            "dynamodb", "cassandra", "elasticsearch"
        ],
        "Cloud Platforms": [
            "aws", "azure", "gcp", "heroku", "digitalocean"
        ],
        "DevOps & Tools": [
            "docker", "kubernetes", "jenkins", "terraform", "ansible",
            "ci/cd", "git", "linux", "nginx"
        ],
        "Data & ML": [
            "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
            "spark", "kafka", "airflow", "machine learning", "data analysis"
        ],
        "APIs & Architecture": [
            "rest api", "graphql", "grpc", "microservices", "websocket"
        ],
        "Soft Skills": [
            "communication", "leadership", "problem solving", "teamwork",
            "project management", "mentoring", "critical thinking"
        ],
    }
    
    # Valid skill patterns for extraction validation
    VALID_SKILL_PATTERNS = [
        # Programming languages
        r'\b(python|javascript|typescript|java|golang|go|rust|ruby|php|swift|kotlin|scala|c\+\+|c#)\b',
        # Frameworks
        r'\b(react|vue|angular|fastapi|django|flask|express|spring|rails|nodejs|next\.?js)\b',
        # Databases
        r'\b(postgresql|postgres|mysql|mongodb|redis|sqlite|dynamodb|cassandra)\b',
        # Cloud/DevOps
        r'\b(docker|kubernetes|k8s|aws|azure|gcp|jenkins|terraform|ansible)\b',
        # Tools
        r'\b(git|github|gitlab|linux|nginx|apache)\b',
        # Soft skills
        r'\b(leadership|mentoring|communication|teamwork|problem[\s-]?solving|critical[\s-]?thinking)\b',
        # Data/ML
        r'\b(pandas|numpy|tensorflow|pytorch|spark|kafka|machine[\s-]?learning|data[\s-]?analysis)\b',
        # APIs
        r'\b(rest|restful|graphql|grpc|microservices?|api)\b',
    ]
    
    # Skill level indicators
    LEVEL_PATTERNS = {
        "expert": [
            r"expert\s+in", r"mastery\s+of", r"deep\s+knowledge", 
            r"extensive\s+experience", r"\d+\+?\s*years?\s+of.*experience",
            r"architected", r"designed\s+and\s+built"
        ],
        "advanced": [
            r"advanced", r"proficient\s+in", r"strong\s+(?:background|skills?)",
            r"solid\s+experience", r"led\s+development", r"senior"
        ],
        "intermediate": [
            r"experience\s+with", r"worked\s+with", r"developed\s+using",
            r"built", r"implemented", r"created"
        ],
        "beginner": [
            r"learning", r"exploring", r"basic\s+knowledge", r"novice",
            r"familiar\s+with", r"exposure\s+to", r"coursework\s+in"
        ],
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = Together(api_key=api_key or os.getenv("TOGETHER_API_KEY"))
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self._build_synonym_index()
    
    def _build_synonym_index(self):
        """Build reverse index for synonym lookup"""
        self.synonym_to_canonical = {}
        for canonical, synonyms in self.SKILL_SYNONYMS.items():
            for syn in synonyms:
                self.synonym_to_canonical[syn.lower()] = canonical
    
    def enhance_skills(self, resume: ParsedResume) -> dict:
        """
        Enhance skill representation ethically.
        
        Returns comprehensive skill analysis with:
        - Standardized skills
        - Skill categories
        - Skill levels
        - Evidence for each skill
        - Warnings about potential issues
        """
        
        # Step 1: Extract skill levels from resume text
        skill_levels = self._extract_skill_levels(resume)
        
        # Step 2: Get skills from experience that aren't in skills list
        experience_skills = self._extract_experience_skills(resume)
        
        # Step 3: Validate and standardize existing skills
        standardized_skills = self._standardize_skills(resume.skills)
        
        # Step 4: Categorize all skills
        all_validated_skills = list(set(standardized_skills + experience_skills))
        categorized = self._categorize_skills(all_validated_skills)
        
        # Step 5: Check for alignment issues
        alignment_warnings = self._check_skill_experience_alignment(resume)
        
        # Step 6: Get LLM suggestions for improvement
        try:
            llm_suggestions = self._get_llm_enhancement(resume, skill_levels)
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
            llm_suggestions = {
                "vague_terms_to_clarify": [],
                "enhancement_notes": []
            }
        
        # Build final result
        result = {
            "standardized_skills": all_validated_skills,
            "skill_categories": categorized,
            "skill_levels": skill_levels,
            "skills_from_experience": experience_skills,
            "vague_terms_to_clarify": llm_suggestions.get("vague_terms_to_clarify", []),
            "enhancement_notes": llm_suggestions.get("enhancement_notes", []),
            "alignment_warnings": alignment_warnings,
            "skill_evidence": self._gather_skill_evidence(resume, all_validated_skills)
        }
        
        return result
    
    def _standardize_skills(self, skills: List[str]) -> List[str]:
        """Standardize skill names using synonym mapping"""
        standardized = set()
        
        for skill in skills:
            skill_lower = skill.lower().strip()
            
            # Check if it's a known synonym
            if skill_lower in self.synonym_to_canonical:
                canonical = self.synonym_to_canonical[skill_lower]
                standardized.add(canonical.title())
            else:
                # Keep original but properly cased
                standardized.add(skill.strip())
        
        return sorted(list(standardized))
    
    def _extract_skill_levels(self, resume: ParsedResume) -> Dict[str, str]:
        """Extract implied skill levels from resume language"""
        skill_levels = {}
        text_lower = resume.raw_text.lower()
        
        # Also include experience descriptions
        for exp in resume.experience:
            for desc in exp.description:
                text_lower += " " + desc.lower()
        
        for skill in resume.skills:
            skill_lower = skill.lower()
            skill_level = "intermediate"  # Default
            
            for level, patterns in self.LEVEL_PATTERNS.items():
                for pattern in patterns:
                    # Look for pattern near the skill mention
                    full_pattern = pattern + r'.*?' + re.escape(skill_lower)
                    alt_pattern = re.escape(skill_lower) + r'.*?' + pattern
                    
                    if re.search(full_pattern, text_lower, re.IGNORECASE) or \
                       re.search(alt_pattern, text_lower, re.IGNORECASE):
                        skill_level = level
                        break
                
                if skill_level != "intermediate":
                    break
            
            skill_levels[skill] = skill_level
        
        return skill_levels
    
    def _extract_experience_skills(self, resume: ParsedResume) -> List[str]:
        """Extract skills mentioned in experience but not in skills list"""
        existing_skills_lower = {s.lower() for s in resume.skills}
        found_skills = set()
        
        # Compile all experience text
        experience_text = ""
        for exp in resume.experience:
            experience_text += " " + exp.title + " "
            experience_text += " ".join(exp.description) + " "
            for skill in exp.skills_used:
                # Add skills_used directly
                skill_std = self._standardize_skill_single(skill)
                if skill_std.lower() not in existing_skills_lower:
                    found_skills.add(skill_std)
        
        # Add project technologies
        for proj in resume.projects:
            for tech in proj.technologies:
                tech_std = self._standardize_skill_single(tech)
                if tech_std.lower() not in existing_skills_lower:
                    found_skills.add(tech_std)
        
        # Search for skills using patterns
        experience_text_lower = experience_text.lower()
        for pattern in self.VALID_SKILL_PATTERNS:
            matches = re.findall(pattern, experience_text_lower, re.IGNORECASE)
            for match in matches:
                match_std = self._standardize_skill_single(match)
                if match_std.lower() not in existing_skills_lower:
                    # Validate it's a real skill mention
                    if self._is_valid_skill(match, experience_text_lower):
                        found_skills.add(match_std)
        
        return sorted(list(found_skills))
    
    def _standardize_skill_single(self, skill: str) -> str:
        """Standardize a single skill name"""
        skill_lower = skill.lower().strip()
        if skill_lower in self.synonym_to_canonical:
            return self.synonym_to_canonical[skill_lower].title()
        return skill.strip().title()
    
    def _is_valid_skill(self, skill: str, text: str) -> bool:
        """Validate that a skill is mentioned as a skill, not just a word"""
        skill_lower = skill.lower()
        
        # Use word boundaries to ensure it's a complete skill
        pattern = r'\b' + re.escape(skill_lower) + r'\b'
        
        # Check if it appears in skill-like context
        skill_contexts = [
            r'(?:used?|using|with|in|experience|knowledge|proficient|familiar|skilled)\s+' + pattern,
            pattern + r'\s+(?:development|programming|framework|database|platform)',
            r'(?:developed?|built|created|implemented)\s+(?:with\s+|using\s+|in\s+)?' + pattern,
        ]
        
        for context_pattern in skill_contexts:
            if re.search(context_pattern, text, re.IGNORECASE):
                return True
        
        # If it's a known tech skill, accept it
        for syn_list in self.SKILL_SYNONYMS.values():
            if skill_lower in syn_list:
                return True
        
        return False
    
    def _categorize_skills(self, skills: List[str]) -> Dict[str, List[str]]:
        """Categorize skills using predefined categories"""
        categorized = {cat: [] for cat in self.SKILL_CATEGORIES.keys()}
        categorized["Other"] = []
        
        for skill in skills:
            skill_lower = skill.lower()
            found = False
            
            for category, category_skills in self.SKILL_CATEGORIES.items():
                if skill_lower in category_skills or \
                   any(skill_lower in cs or cs in skill_lower for cs in category_skills):
                    categorized[category].append(skill)
                    found = True
                    break
            
            if not found:
                categorized["Other"].append(skill)
        
        # Remove empty categories
        return {k: sorted(v) for k, v in categorized.items() if v}
    
    def _check_skill_experience_alignment(self, resume: ParsedResume) -> List[Dict]:
        """Check if claimed skills match actual experience"""
        warnings = []
        
        exp_count = len(resume.experience)
        
        # Senior skills that need experience to back them up
        senior_skills = {
            "leadership": 3,
            "system architecture": 4,
            "technical leadership": 4,
            "mentoring": 3,
            "team management": 4,
            "project management": 3,
        }
        
        for skill in resume.skills:
            skill_lower = skill.lower()
            
            for senior_skill, min_exp in senior_skills.items():
                if senior_skill in skill_lower:
                    if exp_count < min_exp:
                        warnings.append({
                            "skill": skill,
                            "warning": f"Claims '{skill}' but has {exp_count} experience entries (typically needs {min_exp}+)",
                            "suggestion": f"Consider rephrasing to match actual experience level",
                            "severity": "medium"
                        })
        
        # Check for "expert" level claims
        text_lower = resume.raw_text.lower()
        for skill in resume.skills:
            skill_lower = skill.lower()
            
            expert_patterns = [r"expert\s+in\s+" + re.escape(skill_lower), 
                             re.escape(skill_lower) + r"\s+expert"]
            
            for pattern in expert_patterns:
                if re.search(pattern, text_lower):
                    # Check if there's evidence for expert level
                    has_evidence = False
                    for exp in resume.experience:
                        exp_text = " ".join(exp.description).lower()
                        if skill_lower in exp_text:
                            has_evidence = True
                            break
                    
                    if not has_evidence:
                        warnings.append({
                            "skill": skill,
                            "warning": f"Claims expert in '{skill}' but no supporting evidence in experience",
                            "suggestion": "Add specific achievements or quantified results with this skill",
                            "severity": "high"
                        })
        
        return warnings
    
    def _gather_skill_evidence(
        self, 
        resume: ParsedResume, 
        skills: List[str]
    ) -> Dict[str, List[str]]:
        """Gather evidence for each skill from resume"""
        evidence = {}
        
        for skill in skills:
            skill_lower = skill.lower()
            skill_evidence = []
            
            # Check in experience descriptions
            for exp in resume.experience:
                exp_text = f"{exp.title} at {exp.company}: " + " | ".join(exp.description)
                if skill_lower in exp_text.lower():
                    # Extract relevant bullet point
                    for desc in exp.description:
                        if skill_lower in desc.lower():
                            skill_evidence.append(f"Experience: {desc[:100]}...")
                            break
                    else:
                        skill_evidence.append(f"Role: {exp.title} at {exp.company}")
            
            # Check in projects
            for proj in resume.projects:
                if skill_lower in proj.description.lower() or \
                   skill_lower in [t.lower() for t in proj.technologies]:
                    skill_evidence.append(f"Project: {proj.name}")
            
            # Check in certifications
            for cert in resume.certifications:
                if skill_lower in cert.lower():
                    skill_evidence.append(f"Certification: {cert}")
            
            if skill_evidence:
                evidence[skill] = skill_evidence[:3]  # Top 3 pieces of evidence
            else:
                evidence[skill] = ["Listed in skills section"]
        
        return evidence
    
    def _get_llm_enhancement(
        self, 
        resume: ParsedResume,
        skill_levels: Dict[str, str]
    ) -> Dict:
        """Get LLM suggestions for skill presentation improvement"""
        
        prompt = f"""You are an ethical resume skill enhancer. Review these skills and suggest improvements.

CURRENT SKILLS: {json.dumps(resume.skills, indent=2)}

SKILL LEVELS DETECTED: {json.dumps(skill_levels, indent=2)}

EXPERIENCE SUMMARY:
{chr(10).join(f"- {exp.title} at {exp.company}" for exp in resume.experience[:3])}

Your task:
1. Identify vague terms that should be made specific
2. Suggest better ways to present existing skills
3. Note any skills that could be combined or reorganized

IMPORTANT RULES:
- Do NOT suggest adding new skills
- Do NOT invent experience
- ONLY work with what's already in the resume
- Be specific about improvements

Return JSON:
{{
    "vague_terms_to_clarify": [
        {{"vague": "proficient in coding", "specific": "5 years Python development", "reason": "Add years and specific language"}}
    ],
    "enhancement_notes": [
        "Group related skills together",
        "Lead with your strongest skill based on experience"
    ]
}}

Return ONLY valid JSON."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an ethical skill enhancement agent. Never fabricate skills."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up response
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        
        return json.loads(result_text.strip())


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            resume_data = json.load(f)
    else:
        resume_data = json.loads(sys.stdin.read())
    
    resume = ParsedResume(**resume_data)
    agent = SkillAgent()
    result = agent.enhance_skills(resume)
    print(json.dumps(result, indent=2))
