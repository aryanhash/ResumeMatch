"""
Job Description Analyzer Agent - Extracts structured requirements from JD

Fixed Issues:
1. ✅ Uses skill vocabulary instead of broad regex
2. ✅ Proper skill name mapping (no broken extraction)
3. ✅ Clear distinction between skills vs keywords
4. ✅ Seniority inferred from experience_years
5. ✅ Better truncation (keeps end of JD)
6. ✅ Useful keyword fallback
7. ✅ Proper error logging
8. ✅ Output validation and normalization
"""
import json
import os
import re
import logging
from typing import Optional, Dict, List, Any
from together import Together
from models.schemas import ParsedJobDescription, Seniority

logger = logging.getLogger(__name__)


class JDAnalyzerAgent:
    """Agent responsible for analyzing job descriptions"""
    
    MAX_JD_CHARS = 15000
    
    # Known skills vocabulary - maps display name to aliases
    KNOWN_SKILLS = {
        # Programming Languages
        "Python": ["python", "python3", "py"],
        "JavaScript": ["javascript", "js", "ecmascript"],
        "TypeScript": ["typescript", "ts"],
        "Java": ["java"],  # Note: NOT 'javascript'
        "Go": ["golang", "go programming"],
        "Rust": ["rust"],
        "C++": ["c++", "cpp"],
        "C#": ["c#", "csharp", "c sharp"],
        "Ruby": ["ruby"],
        "PHP": ["php"],
        "Swift": ["swift"],
        "Kotlin": ["kotlin"],
        "Scala": ["scala"],
        
        # Frameworks - Backend
        "FastAPI": ["fastapi", "fast api", "fast-api"],
        "Django": ["django"],
        "Flask": ["flask"],
        "Express": ["express", "express.js", "expressjs"],
        "Spring": ["spring boot", "spring framework", "springboot"],
        "Node.js": ["node.js", "nodejs", "node"],
        "Rails": ["ruby on rails", "rails"],
        ".NET": [".net", "dotnet", "asp.net"],
        
        # Frameworks - Frontend
        "React": ["react", "reactjs", "react.js"],
        "Vue": ["vue", "vuejs", "vue.js"],
        "Angular": ["angular", "angularjs"],
        "Next.js": ["next.js", "nextjs", "next"],
        "Svelte": ["svelte"],
        
        # Databases
        "PostgreSQL": ["postgresql", "postgres", "psql"],
        "MySQL": ["mysql"],
        "MongoDB": ["mongodb", "mongo"],
        "Redis": ["redis"],
        "SQLite": ["sqlite"],
        "Oracle": ["oracle database", "oracle db"],
        "DynamoDB": ["dynamodb", "dynamo"],
        "Cassandra": ["cassandra"],
        "Elasticsearch": ["elasticsearch", "elastic search"],
        
        # Cloud & DevOps
        "AWS": ["aws", "amazon web services"],
        "Azure": ["azure", "microsoft azure"],
        "GCP": ["gcp", "google cloud", "google cloud platform"],
        "Docker": ["docker", "containerization"],
        "Kubernetes": ["kubernetes", "k8s"],
        "Terraform": ["terraform"],
        "Jenkins": ["jenkins"],
        "GitHub Actions": ["github actions"],
        "GitLab CI": ["gitlab ci", "gitlab-ci"],
        
        # Tools
        "Git": ["git", "version control"],
        "Linux": ["linux", "unix"],
        "Nginx": ["nginx"],
        "Apache": ["apache"],
        
        # Data
        "SQL": ["sql", "structured query language"],
        "NoSQL": ["nosql", "no-sql"],
        "Pandas": ["pandas"],
        "PySpark": ["pyspark", "spark"],
        "Kafka": ["kafka", "apache kafka"],
        "Airflow": ["airflow", "apache airflow"],
        
        # APIs & Architecture
        "REST API": ["rest api", "restful api", "restful apis", "rest apis"],
        "GraphQL": ["graphql"],
        "gRPC": ["grpc", "g-rpc"],
        "Protobuf": ["protobuf", "protocol buffers"],
        "WebSocket": ["websocket", "websockets"],
        
        # Patterns & Practices
        "Microservices": ["microservices", "microservice", "microservice architecture"],
        "ORM": ["orm", "object relational mapping"],
        "ODM": ["odm", "object document mapping"],
        "TDD": ["tdd", "test driven development"],
        "CI/CD": ["ci/cd", "cicd", "continuous integration", "continuous deployment"],
        
        # Testing
        "Pytest": ["pytest"],
        "Jest": ["jest"],
        "Selenium": ["selenium"],
        "Cypress": ["cypress"],
    }
    
    # Keywords that are NOT skills but important for ATS
    ATS_KEYWORDS = [
        # Methodologies
        "Agile", "Scrum", "Kanban", "Waterfall", "Sprint",
        # Practices
        "Code Review", "Pair Programming", "Documentation",
        # Soft Skills (as keywords, not skills)
        "Problem Solving", "Critical Thinking", "Communication",
        "Teamwork", "Collaboration", "Leadership", "Mentoring",
        # Domain Terms
        "Backend", "Frontend", "Full Stack", "DevOps", "SRE",
        "Data Engineering", "Machine Learning", "AI", "IoT",
        # Architecture Terms
        "Distributed Systems", "Scalability", "High Availability",
        "Event Driven", "Serverless", "Cloud Native",
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = Together(api_key=api_key or os.getenv("TOGETHER_API_KEY"))
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self._build_skill_index()
    
    def _build_skill_index(self):
        """Build reverse index for fast skill lookup"""
        self.alias_to_skill = {}
        for skill_name, aliases in self.KNOWN_SKILLS.items():
            for alias in aliases:
                self.alias_to_skill[alias.lower()] = skill_name
    
    def _clean_and_truncate(self, text: str) -> str:
        """
        Clean and truncate JD - prefers keeping END of JD
        (requirements/qualifications usually at the end)
        """
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        
        if len(text) <= self.MAX_JD_CHARS:
            return text.strip()
        
        # Keep the last MAX_JD_CHARS characters (requirements usually at end)
        text = text[-self.MAX_JD_CHARS:]
        
        # Find first sentence boundary to start cleanly
        first_period = text.find('. ')
        if 50 < first_period < 500:
            text = text[first_period + 2:]
        
        return text.strip()
    
    def analyze(self, jd_text: str) -> ParsedJobDescription:
        """Analyze job description and extract structured requirements"""
        
        # Clean and truncate
        jd_text_clean = self._clean_and_truncate(jd_text)
        
        prompt = self._build_prompt(jd_text_clean)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise job description analyzer. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up markdown backticks
            result_text = self._clean_json_response(result_text)
            
            try:
                parsed_data = json.loads(result_text)
            except json.JSONDecodeError as e:
                logger.warning(f"LLM returned invalid JSON: {e}")
                logger.debug(f"Response preview: {result_text[:300]}")
                return self._fallback_parse(jd_text)
            
            # Validate and normalize LLM output
            parsed_data = self._validate_and_normalize(parsed_data)
            
            # Determine seniority (from seniority field OR experience_years)
            seniority = self._determine_seniority(
                parsed_data.get("seniority"),
                parsed_data.get("experience_years")
            )
            
            return ParsedJobDescription(
                role=parsed_data.get("role", "Unknown Role"),
                company=parsed_data.get("company"),
                required_skills=parsed_data.get("required_skills", []),
                preferred_skills=parsed_data.get("preferred_skills", []),
                tools=parsed_data.get("tools", []),
                seniority=seniority,
                soft_skills=parsed_data.get("soft_skills", []),
                keywords=parsed_data.get("keywords", []),
                responsibilities=parsed_data.get("responsibilities", []),
                qualifications=parsed_data.get("qualifications", []),
                experience_years=parsed_data.get("experience_years"),
                raw_text=jd_text
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return self._fallback_parse(jd_text)
        except Exception as e:
            logger.error(f"JD analysis failed: {e}")
            return self._fallback_parse(jd_text)
    
    def _build_prompt(self, jd_text: str) -> str:
        """Build clear, unambiguous prompt for LLM"""
        return f"""Analyze this job description and extract structured information.

Return a JSON object with these fields:

{{
    "role": "Job Title (e.g., 'Backend Developer', 'Data Engineer')",
    "company": "Company name or null if not mentioned",
    
    "required_skills": [
        "ONLY technical skills marked as REQUIRED/MUST-HAVE",
        "Examples: 'Python', 'PostgreSQL', 'Docker'",
        "Do NOT include soft skills or methodologies here"
    ],
    
    "preferred_skills": [
        "Technical skills marked as PREFERRED/NICE-TO-HAVE",
        "Examples: 'Kubernetes', 'GraphQL'"
    ],
    
    "tools": [
        "Specific tools, platforms, services mentioned",
        "Examples: 'AWS', 'Jenkins', 'Jira', 'Confluence'"
    ],
    
    "seniority": "entry|junior|mid|senior|lead|principal",
    
    "soft_skills": [
        "Non-technical skills",
        "Examples: 'Communication', 'Problem Solving', 'Teamwork'"
    ],
    
    "keywords": [
        "ATS matching terms that are NOT programming languages/frameworks",
        "Include: methodologies, architecture patterns, domain terms",
        "Examples: 'Agile', 'Microservices', 'REST API', 'CI/CD', 'Backend Development'"
    ],
    
    "responsibilities": ["Key job responsibilities"],
    "qualifications": ["Required qualifications/education"],
    "experience_years": "e.g., '1-2 years' or '3+ years' or null"
}}

IMPORTANT RULES:
1. required_skills = ONLY technical skills explicitly marked as required
2. keywords = methodology/architecture terms, NOT programming languages
3. If something is both a skill and keyword (like 'REST API'), put in required_skills
4. seniority: infer from experience_years (0-1=entry, 1-2=junior, 2-4=mid, 4-6=senior, 6+=lead)

Job Description:
{jd_text}

Return ONLY valid JSON, no explanations."""
    
    def _clean_json_response(self, text: str) -> str:
        """Clean markdown formatting from LLM response"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
    
    def _validate_and_normalize(self, parsed_data: Dict) -> Dict:
        """Validate and normalize LLM output to prevent type errors"""
        
        # Ensure list fields are actually lists
        list_fields = [
            'required_skills', 'preferred_skills', 'tools', 
            'soft_skills', 'keywords', 'responsibilities', 'qualifications'
        ]
        
        for field in list_fields:
            value = parsed_data.get(field)
            
            if value is None:
                parsed_data[field] = []
            elif isinstance(value, str):
                # Split comma-separated strings into lists
                parsed_data[field] = [s.strip() for s in value.split(',') if s.strip()]
            elif not isinstance(value, list):
                parsed_data[field] = []
            else:
                # Ensure all items are strings
                parsed_data[field] = [str(item).strip() for item in value if item]
        
        # Normalize seniority
        seniority_str = str(parsed_data.get("seniority", "mid")).lower().strip()
        
        # Map common variations
        seniority_variations = {
            "entry level": "entry",
            "entry-level": "entry",
            "junior level": "junior",
            "junior developer": "junior",
            "mid level": "mid",
            "mid-level": "mid",
            "intermediate": "mid",
            "senior level": "senior",
            "senior developer": "senior",
            "staff": "senior",
            "lead developer": "lead",
            "tech lead": "lead",
            "principal engineer": "principal",
            "architect": "principal",
        }
        
        parsed_data["seniority"] = seniority_variations.get(seniority_str, seniority_str)
        
        # Normalize role
        if not parsed_data.get("role"):
            parsed_data["role"] = "Unknown Role"
        
        return parsed_data
    
    def _determine_seniority(
        self, 
        seniority_str: Optional[str], 
        experience_years: Optional[str]
    ) -> Seniority:
        """
        Determine seniority from both seniority field AND experience_years
        """
        seniority_map = {
            "entry": Seniority.ENTRY,
            "junior": Seniority.JUNIOR,
            "mid": Seniority.MID,
            "senior": Seniority.SENIOR,
            "lead": Seniority.LEAD,
            "principal": Seniority.PRINCIPAL
        }
        
        # First try direct seniority field
        if seniority_str:
            seniority_key = seniority_str.lower().strip()
            if seniority_key in seniority_map:
                return seniority_map[seniority_key]
        
        # Fallback: infer from experience_years
        if experience_years:
            return self._infer_seniority_from_years(experience_years)
        
        return Seniority.MID  # Default
    
    def _infer_seniority_from_years(self, experience_years: str) -> Seniority:
        """Infer seniority level from years of experience string"""
        # Extract numbers from strings like "3-5 years", "3+ years", "3 years"
        numbers = re.findall(r'\d+', experience_years)
        
        if not numbers:
            return Seniority.MID
        
        # Use the first number as minimum requirement
        years = int(numbers[0])
        
        if years < 1:
            return Seniority.ENTRY
        elif years < 2:
            return Seniority.JUNIOR
        elif years < 4:
            return Seniority.MID
        elif years < 7:
            return Seniority.SENIOR
        else:
            return Seniority.LEAD
    
    def _fallback_parse(self, jd_text: str) -> ParsedJobDescription:
        """Fallback parsing when LLM fails - uses skill vocabulary"""
        logger.info("Using fallback JD parsing")
        
        # Extract skills using vocabulary
        found_skills = self._extract_skills_from_vocabulary(jd_text)
        
        # Extract keywords
        found_keywords = self._extract_keywords(jd_text)
        
        # Infer seniority from text
        seniority = self._infer_seniority_from_text(jd_text)
        
        # Try to extract role from first line or common patterns
        role = self._extract_role(jd_text)
        
        return ParsedJobDescription(
            role=role,
            required_skills=found_skills[:10],  # Top skills as required
            preferred_skills=found_skills[10:15],  # Rest as preferred
            tools=found_skills[:8],  # Overlap is OK for fallback
            seniority=seniority,
            soft_skills=[],
            keywords=found_keywords,
            responsibilities=[],
            qualifications=[],
            experience_years=None,
            raw_text=jd_text
        )
    
    def _extract_skills_from_vocabulary(self, text: str) -> List[str]:
        """
        Extract skills using known vocabulary - ACCURATE matching
        """
        text_lower = text.lower()
        found_skills = []
        found_set = set()  # Avoid duplicates
        
        for skill_name, aliases in self.KNOWN_SKILLS.items():
            if skill_name in found_set:
                continue
                
            for alias in aliases:
                # Use word boundaries to avoid false matches
                # Special handling for skills with special chars
                escaped_alias = re.escape(alias)
                pattern = r'\b' + escaped_alias + r'\b'
                
                # Special case: "Java" should not match "JavaScript"
                if alias == "java":
                    # Negative lookahead for 'script'
                    pattern = r'\bjava\b(?!script)'
                
                if re.search(pattern, text_lower, re.IGNORECASE):
                    found_skills.append(skill_name)
                    found_set.add(skill_name)
                    break  # Don't double-count from multiple aliases
        
        return found_skills
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract ATS keywords (non-skill technical terms)"""
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.ATS_KEYWORDS:
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, text_lower):
                if keyword not in found_keywords:
                    found_keywords.append(keyword)
        
        return found_keywords[:15]  # Limit to top 15
    
    def _infer_seniority_from_text(self, text: str) -> Seniority:
        """Infer seniority from JD text patterns"""
        text_lower = text.lower()
        
        # Check for years pattern
        years_match = re.search(r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?', text_lower)
        if years_match:
            years = int(years_match.group(1))
            if years < 1:
                return Seniority.ENTRY
            elif years < 2:
                return Seniority.JUNIOR
            elif years < 4:
                return Seniority.MID
            elif years < 7:
                return Seniority.SENIOR
            else:
                return Seniority.LEAD
        
        # Check for seniority keywords
        if any(kw in text_lower for kw in ["entry level", "entry-level", "graduate", "fresh"]):
            return Seniority.ENTRY
        if any(kw in text_lower for kw in ["junior", "associate", "i ", " i,"]):
            return Seniority.JUNIOR
        if any(kw in text_lower for kw in ["senior", "sr.", "sr "]):
            return Seniority.SENIOR
        if any(kw in text_lower for kw in ["lead", "principal", "staff", "architect"]):
            return Seniority.LEAD
        
        return Seniority.MID  # Default
    
    def _extract_role(self, text: str) -> str:
        """Try to extract job title from JD"""
        # Common patterns for job titles
        patterns = [
            r'(?:position|role|title)[:\s]+([^\n]+)',
            r'^([A-Z][a-zA-Z\s]+(?:Developer|Engineer|Designer|Manager|Analyst))',
            r'(?:hiring|looking for)[:\s]+(?:a\s+)?([^\n]+(?:developer|engineer|designer))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                role = match.group(1).strip()
                if 5 < len(role) < 60:  # Reasonable title length
                    return role
        
        return "Software Developer"  # Generic fallback


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            jd_text = f.read()
    else:
        jd_text = sys.stdin.read()
    
    agent = JDAnalyzerAgent()
    result = agent.analyze(jd_text)
    print(result.model_dump_json(indent=2))
