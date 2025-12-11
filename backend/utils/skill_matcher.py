"""
Intelligent Skill Matcher using Semantic Embeddings + Skill Ontology
Clean, maintainable, and scalable approach to skill matching
"""
import os
import json
import re
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Try to import sentence-transformers, fallback to simple matching if not available
try:
    from sentence_transformers import SentenceTransformer, util
    EMBEDDINGS_AVAILABLE = True
    logger.info("✓ sentence-transformers loaded successfully")
except ImportError as e:
    EMBEDDINGS_AVAILABLE = False
    logger.warning(f"sentence-transformers not available: {e}. Using ontology-based matching only.")


class SkillOntology:
    """
    Lightweight skill knowledge base for common equivalences.
    Easy to maintain - just update the JSON structure.
    """
    
    # Core skill ontology - covers common tech skills and their relationships
    ONTOLOGY = {
        # Programming Languages
        "python": {
            "category": "language",
            "aliases": ["python3", "py", "python programming"],
            "related": ["django", "fastapi", "flask", "pandas", "numpy"]
        },
        "javascript": {
            "category": "language",
            "aliases": ["js", "ecmascript", "es6"],
            "related": ["nodejs", "react", "vue", "typescript"]
        },
        "typescript": {
            "category": "language",
            "aliases": ["ts"],
            "related": ["javascript", "angular", "react"]
        },
        
        # Frameworks
        "fastapi": {
            "category": "framework",
            "aliases": ["fast api", "fast-api"],
            "related": ["python", "rest", "api"]
        },
        "django": {
            "category": "framework",
            "aliases": ["django framework"],
            "related": ["python", "orm", "web"]
        },
        "react": {
            "category": "framework",
            "aliases": ["reactjs", "react.js"],
            "related": ["javascript", "frontend", "jsx"]
        },
        "nodejs": {
            "category": "runtime",
            "aliases": ["node", "node.js"],
            "related": ["javascript", "express", "npm"]
        },
        
        # Databases
        "mongodb": {
            "category": "database",
            "aliases": ["mongo"],
            "related": ["nosql", "mongoose", "odm"]
        },
        "postgresql": {
            "category": "database",
            "aliases": ["postgres", "psql", "pg"],
            "related": ["sql", "relational", "orm"]
        },
        "mysql": {
            "category": "database",
            "aliases": ["my sql"],
            "related": ["sql", "relational"]
        },
        "redis": {
            "category": "database",
            "aliases": ["redis cache"],
            "related": ["caching", "nosql", "in-memory"]
        },
        "nosql": {
            "category": "database_type",
            "aliases": ["no-sql", "non-relational", "nosql databases"],
            "related": ["mongodb", "redis", "cassandra", "dynamodb"]
        },
        "sql": {
            "category": "language",
            "aliases": ["structured query language"],
            "related": ["postgresql", "mysql", "database", "rdbms"]
        },
        
        # Architecture & Patterns
        "microservices": {
            "category": "architecture",
            "aliases": ["microservice", "micro-services", "microservice architecture"],
            "related": ["distributed", "docker", "kubernetes", "api"]
        },
        "rest": {
            "category": "architecture",
            "aliases": ["restful", "rest api", "restful api", "restful apis", "restful architectural style"],
            "related": ["api", "http", "web services"]
        },
        "graphql": {
            "category": "architecture",
            "aliases": ["graph ql"],
            "related": ["api", "query language"]
        },
        "grpc": {
            "category": "architecture",
            "aliases": ["g-rpc", "grpc api"],
            "related": ["protobuf", "rpc", "microservices"]
        },
        "protobuf": {
            "category": "serialization",
            "aliases": ["protocol buffers", "proto", "protobuf with python"],
            "related": ["grpc", "serialization"]
        },
        
        # DevOps & Cloud
        "docker": {
            "category": "devops",
            "aliases": ["containerization", "docker containers"],
            "related": ["kubernetes", "containers", "devops"]
        },
        "kubernetes": {
            "category": "devops",
            "aliases": ["k8s", "kube"],
            "related": ["docker", "orchestration", "devops"]
        },
        "aws": {
            "category": "cloud",
            "aliases": ["amazon web services", "amazon aws"],
            "related": ["cloud", "ec2", "s3", "lambda"]
        },
        "azure": {
            "category": "cloud",
            "aliases": ["microsoft azure", "azure cloud"],
            "related": ["cloud", "microsoft"]
        },
        "gcp": {
            "category": "cloud",
            "aliases": ["google cloud", "google cloud platform"],
            "related": ["cloud", "google"]
        },
        "git": {
            "category": "vcs",
            "aliases": ["git version control", "version control"],
            "related": ["github", "gitlab", "bitbucket"]
        },
        "cicd": {
            "category": "devops",
            "aliases": ["ci/cd", "ci cd", "continuous integration", "continuous deployment"],
            "related": ["jenkins", "github actions", "devops"]
        },
        
        # Data & ORM
        "orm": {
            "category": "pattern",
            "aliases": ["object relational mapping", "orms"],
            "related": ["sqlalchemy", "prisma", "sequelize", "database"]
        },
        "odm": {
            "category": "pattern",
            "aliases": ["object document mapping", "odms"],
            "related": ["mongoose", "mongodb"]
        },
        
        # Testing & Quality
        "testing": {
            "category": "practice",
            "aliases": ["unit testing", "test", "automated testing"],
            "related": ["pytest", "jest", "tdd"]
        },
        "debugging": {
            "category": "practice",
            "aliases": ["debug", "troubleshooting"],
            "related": ["testing", "logging"]
        },
        
        # Methodologies
        "agile": {
            "category": "methodology",
            "aliases": ["agile methodology", "agile methodologies"],
            "related": ["scrum", "kanban", "sprint"]
        },
        
        # Soft Skills
        "problem_solving": {
            "category": "soft_skill",
            "aliases": ["problem solving", "problem-solving", "analytical thinking"],
            "related": ["critical thinking", "debugging"]
        },
        "communication": {
            "category": "soft_skill",
            "aliases": ["team communication", "collaboration"],
            "related": ["teamwork", "presentation"]
        }
    }
    
    def __init__(self):
        self._build_reverse_index()
    
    def _build_reverse_index(self):
        """Build reverse index for fast alias lookup"""
        self.alias_to_skill = {}
        for skill, data in self.ONTOLOGY.items():
            # Index the skill itself
            self.alias_to_skill[skill.lower()] = skill
            # Index all aliases
            for alias in data.get("aliases", []):
                self.alias_to_skill[alias.lower()] = skill
    
    def normalize(self, skill: str) -> str:
        """Normalize a skill to its canonical form"""
        skill_clean = skill.lower().strip()
        return self.alias_to_skill.get(skill_clean, skill_clean)
    
    def get_related(self, skill: str) -> List[str]:
        """Get related skills"""
        normalized = self.normalize(skill)
        if normalized in self.ONTOLOGY:
            return self.ONTOLOGY[normalized].get("related", [])
        return []
    
    def are_equivalent(self, skill1: str, skill2: str) -> bool:
        """Check if two skills are equivalent (same canonical form)"""
        return self.normalize(skill1) == self.normalize(skill2)


class SkillMatcher:
    """
    Intelligent skill matcher using:
    1. Exact match
    2. Ontology-based matching (aliases & equivalences)
    3. Semantic similarity (embeddings)
    """
    
    # Similarity thresholds
    EXACT_MATCH_SCORE = 1.0
    ONTOLOGY_MATCH_SCORE = 0.95
    SEMANTIC_THRESHOLD = 0.75  # Minimum similarity for semantic match
    
    def __init__(self, use_embeddings: bool = True):
        self.ontology = SkillOntology()
        self.use_embeddings = use_embeddings and EMBEDDINGS_AVAILABLE
        self.model = None
        self._embeddings_cache = {}

        # Only load model when actually needed
        if self.use_embeddings:
            logger.info("Semantic embeddings available (model will be loaded on first use)")
    
    def _get_embedding(self, text: str):
        """Get embedding with caching and lazy model loading"""
        # Lazy load the model
        if self.model is None and self.use_embeddings:
            try:
                # Use a lightweight, fast model
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✓ Semantic embeddings model loaded")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
                self.use_embeddings = False
                return None

        if text not in self._embeddings_cache:
            if self.model is not None:
                self._embeddings_cache[text] = self.model.encode(text, convert_to_tensor=True)
            else:
                return None
        return self._embeddings_cache[text]
    
    def match_skill(self, jd_skill: str, resume_skills: List[str], resume_text: str = "") -> Tuple[bool, float, Optional[str]]:
        """
        Match a JD skill against resume skills and text.
        
        Returns:
            Tuple of (is_match, confidence, matched_skill)
        """
        jd_skill_lower = jd_skill.lower().strip()
        jd_skill_normalized = self.ontology.normalize(jd_skill)
        
        # Normalize resume skills
        resume_skills_lower = [s.lower().strip() for s in resume_skills]
        resume_skills_normalized = [self.ontology.normalize(s) for s in resume_skills]
        
        # 1. EXACT MATCH
        if jd_skill_lower in resume_skills_lower:
            idx = resume_skills_lower.index(jd_skill_lower)
            return (True, self.EXACT_MATCH_SCORE, resume_skills[idx])
        
        # 2. ONTOLOGY MATCH (canonical form)
        if jd_skill_normalized in resume_skills_normalized:
            idx = resume_skills_normalized.index(jd_skill_normalized)
            return (True, self.ONTOLOGY_MATCH_SCORE, resume_skills[idx])
        
        # 3. CHECK ALIASES via ontology
        for i, rs_normalized in enumerate(resume_skills_normalized):
            if self.ontology.are_equivalent(jd_skill, resume_skills[i]):
                return (True, self.ONTOLOGY_MATCH_SCORE, resume_skills[i])
        
        # 4. CHECK IN RESUME TEXT (for skills mentioned but not listed)
        if resume_text:
            resume_text_lower = resume_text.lower()
            # Check canonical form in text
            if jd_skill_normalized in resume_text_lower:
                return (True, 0.85, f"[found in text: {jd_skill_normalized}]")
            # Check aliases in text
            if jd_skill_lower in resume_text_lower:
                return (True, 0.85, f"[found in text: {jd_skill_lower}]")
        
        # 5. SEMANTIC MATCHING (if embeddings available)
        if self.use_embeddings and resume_skills:
            try:
                jd_embedding = self._get_embedding(jd_skill)
                if jd_embedding is None:
                    logger.debug("Embeddings not available for semantic matching")
                else:
                    best_score = 0.0
                    best_match = None

                    for rs in resume_skills:
                        rs_embedding = self._get_embedding(rs)
                        if rs_embedding is not None:
                            similarity = float(util.pytorch_cos_sim(jd_embedding, rs_embedding)[0][0])

                            if similarity > best_score:
                                best_score = similarity
                                best_match = rs

                    if best_score >= self.SEMANTIC_THRESHOLD:
                        return (True, best_score, best_match)

            except Exception as e:
                logger.warning(f"Semantic matching error: {e}")
        
        # 6. RELATED SKILLS CHECK (lower confidence)
        related = self.ontology.get_related(jd_skill_normalized)
        for rel_skill in related:
            if rel_skill in resume_skills_normalized:
                idx = resume_skills_normalized.index(rel_skill)
                return (True, 0.7, f"{resume_skills[idx]} (related)")
        
        # No match found
        return (False, 0.0, None)
    
    def match_all_skills(
        self, 
        jd_skills: List[str], 
        resume_skills: List[str], 
        resume_text: str = ""
    ) -> Dict:
        """
        Match all JD skills against resume.
        
        Returns:
            Dict with matched_skills, missing_skills, and confidence scores
        """
        matched = []
        missing = []
        confidence_scores = {}
        
        for jd_skill in jd_skills:
            is_match, confidence, matched_with = self.match_skill(
                jd_skill, resume_skills, resume_text
            )
            
            if is_match:
                matched.append({
                    "skill": jd_skill,
                    "matched_with": matched_with,
                    "confidence": confidence
                })
                confidence_scores[jd_skill] = confidence
            else:
                missing.append(jd_skill)
                confidence_scores[jd_skill] = 0.0
        
        return {
            "matched": matched,
            "missing": missing,
            "match_rate": len(matched) / max(len(jd_skills), 1),
            "confidence_scores": confidence_scores,
            "average_confidence": sum(confidence_scores.values()) / max(len(jd_skills), 1)
        }


# Global instance for reuse
_matcher_instance = None

def get_skill_matcher() -> SkillMatcher:
    """Get or create global skill matcher instance"""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = SkillMatcher(use_embeddings=True)
    return _matcher_instance


# Simple function interface
def match_skills(
    jd_skills: List[str], 
    resume_skills: List[str], 
    resume_text: str = ""
) -> Dict:
    """
    Simple interface to match skills.
    
    Example:
        result = match_skills(
            jd_skills=["Python", "FastAPI", "MongoDB"],
            resume_skills=["Python", "Fast API", "Mongo"],
            resume_text="Experience with RESTful APIs..."
        )
        print(result["match_rate"])  # 1.0 (100% match)
    """
    matcher = get_skill_matcher()
    return matcher.match_all_skills(jd_skills, resume_skills, resume_text)


if __name__ == "__main__":
    # Test the matcher
    print("Testing Skill Matcher...")
    
    jd_skills = [
        "Python", "FastAPI", "MongoDB", "REST API", 
        "Microservice Architecture", "Docker", "Git"
    ]
    
    resume_skills = [
        "Python", "Fast API", "Mongo", "RESTful APIs",
        "Microservices", "Docker", "GitHub"
    ]
    
    result = match_skills(jd_skills, resume_skills)
    
    print(f"\nMatch Rate: {result['match_rate']*100:.1f}%")
    print(f"\nMatched Skills:")
    for m in result["matched"]:
        print(f"  ✓ {m['skill']} → {m['matched_with']} ({m['confidence']*100:.0f}%)")
    
    print(f"\nMissing Skills:")
    for m in result["missing"]:
        print(f"  ✗ {m}")

