"""
Resume Parser Agent - Extracts structured data from resumes
"""
import json
import os
import re
from typing import Optional
from together import Together
from models.schemas import ParsedResume, Education, Experience, Project


class ResumeParserAgent:
    """Agent responsible for parsing resumes into structured data"""
    
    # Maximum characters to send to the model (~4 chars per token, leave room for prompt)
    MAX_RESUME_CHARS = 20000
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = Together(api_key=api_key or os.getenv("TOGETHER_API_KEY"))
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    
    def _clean_and_truncate(self, text: str) -> str:
        """Clean and truncate resume text to fit within token limits"""
        # Remove excessive whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # Remove common PDF artifacts
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        
        # If text is too long, truncate intelligently
        if len(text) > self.MAX_RESUME_CHARS:
            # Try to keep the most important parts (beginning has contact info, skills)
            text = text[:self.MAX_RESUME_CHARS]
            # Try to end at a sentence or section break
            last_period = text.rfind('.')
            last_newline = text.rfind('\n')
            cut_point = max(last_period, last_newline)
            if cut_point > self.MAX_RESUME_CHARS * 0.8:
                text = text[:cut_point + 1]
        
        return text.strip()
    
    def parse(self, resume_text: str) -> ParsedResume:
        """Parse resume text into structured format"""
        
        # Store original for raw_text field
        original_text = resume_text
        
        # Clean and truncate for API call
        resume_text = self._clean_and_truncate(resume_text)
        
        prompt = f"""You are an expert resume parser. Extract structured information from the following resume.
        
Return a valid JSON object with this exact structure:
{{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "phone number",
    "location": "City, State/Country",
    "linkedin": "linkedin url or null",
    "github": "github url or null",
    "summary": "Professional summary if present",
    "skills": ["skill1", "skill2", ...],
    "experience": [
        {{
            "title": "Job Title",
            "company": "Company Name",
            "duration": "Start - End",
            "description": ["bullet point 1", "bullet point 2"],
            "skills_used": ["skill1", "skill2"]
        }}
    ],
    "education": [
        {{
            "degree": "Degree Name",
            "institution": "University Name",
            "year": "Graduation Year",
            "gpa": "GPA if mentioned",
            "field_of_study": "Major/Field"
        }}
    ],
    "projects": [
        {{
            "name": "Project Name",
            "description": "Brief description",
            "technologies": ["tech1", "tech2"],
            "link": "project link or null",
            "impact": "quantified impact if any"
        }}
    ],
    "certifications": ["cert1", "cert2"],
    "languages": ["English", "Spanish"]
}}

Resume Text:
{resume_text}

Return ONLY valid JSON, no explanations."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise resume parser. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up the response
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            parsed_data = json.loads(result_text.strip())
            
            # Build structured objects
            experience = [
                Experience(
                    title=exp.get("title", ""),
                    company=exp.get("company", ""),
                    duration=exp.get("duration", ""),
                    description=exp.get("description", []),
                    skills_used=exp.get("skills_used", [])
                )
                for exp in parsed_data.get("experience", [])
            ]
            
            education = [
                Education(
                    degree=edu.get("degree", ""),
                    institution=edu.get("institution", ""),
                    year=edu.get("year"),
                    gpa=edu.get("gpa"),
                    field_of_study=edu.get("field_of_study")
                )
                for edu in parsed_data.get("education", [])
            ]
            
            projects = [
                Project(
                    name=proj.get("name", ""),
                    description=proj.get("description", ""),
                    technologies=proj.get("technologies", []),
                    link=proj.get("link"),
                    impact=proj.get("impact")
                )
                for proj in parsed_data.get("projects", [])
            ]
            
            return ParsedResume(
                name=parsed_data.get("name"),
                email=parsed_data.get("email"),
                phone=parsed_data.get("phone"),
                location=parsed_data.get("location"),
                linkedin=parsed_data.get("linkedin"),
                github=parsed_data.get("github"),
                summary=parsed_data.get("summary"),
                skills=parsed_data.get("skills", []),
                experience=experience,
                education=education,
                projects=projects,
                certifications=parsed_data.get("certifications", []),
                languages=parsed_data.get("languages", []),
                raw_text=resume_text  # Use cleaned/truncated version
            )
            
        except json.JSONDecodeError as e:
            # Fallback: return basic parsed resume with extracted skills
            return ParsedResume(
                raw_text=resume_text,
                skills=self._extract_skills_fallback(resume_text)
            )
        except Exception as e:
            # If API fails, try fallback parsing
            print(f"AI parsing failed: {str(e)}, using fallback")
            return self._fallback_parse(resume_text)
    
    def _fallback_parse(self, text: str) -> ParsedResume:
        """Fallback parsing without AI when text is too long or API fails"""
        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        email = email_match.group(0) if email_match else None
        
        # Extract phone
        phone_match = re.search(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{3,6}[-\s\.]?[0-9]{3,6}', text)
        phone = phone_match.group(0) if phone_match else None
        
        # Extract LinkedIn
        linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', text, re.IGNORECASE)
        linkedin = f"https://{linkedin_match.group(0)}" if linkedin_match else None
        
        # Extract GitHub
        github_match = re.search(r'github\.com/[\w-]+', text, re.IGNORECASE)
        github = f"https://{github_match.group(0)}" if github_match else None
        
        # Extract skills
        skills = self._extract_skills_fallback(text)
        
        return ParsedResume(
            email=email,
            phone=phone,
            linkedin=linkedin,
            github=github,
            skills=skills,
            raw_text=text[:self.MAX_RESUME_CHARS]
        )
    
    def _extract_skills_fallback(self, text: str) -> list:
        """Comprehensive skill extraction as fallback"""
        # Extensive skill list covering programming, frameworks, databases, cloud, etc.
        skill_patterns = [
            # Programming Languages
            "python", "javascript", "typescript", "java", "c\\+\\+", "c#", "go", "golang", "rust",
            "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl", "shell", "bash",
            
            # Web Frameworks
            "react", "react.js", "reactjs", "vue", "vue.js", "vuejs", "angular", "angularjs",
            "node.js", "nodejs", "express", "express.js", "fastapi", "fast api", "django", "flask",
            "spring", "spring boot", "springboot", "asp.net", ".net", "laravel", "rails",
            "next.js", "nextjs", "nuxt", "svelte", "gatsby",
            
            # Databases
            "sql", "postgresql", "postgres", "mysql", "sqlite", "oracle", "pl/sql", "plsql",
            "mongodb", "mongo", "redis", "cassandra", "dynamodb", "elasticsearch",
            "nosql", "neo4j", "firebase", "couchdb", "hive", "bigquery",
            
            # Cloud & DevOps
            "aws", "amazon web services", "azure", "microsoft azure", "gcp", "google cloud",
            "google cloud platform", "docker", "kubernetes", "k8s", "terraform", "ansible",
            "jenkins", "ci/cd", "cicd", "github actions", "gitlab ci", "circleci",
            "cloudformation", "helm", "istio", "prometheus", "grafana",
            
            # Data & ML
            "pandas", "numpy", "scipy", "scikit-learn", "sklearn", "tensorflow", "pytorch",
            "keras", "spark", "pyspark", "hadoop", "airflow", "kafka", "flink",
            "tableau", "power bi", "powerbi", "looker", "matplotlib", "seaborn", "plotly",
            "machine learning", "deep learning", "nlp", "computer vision",
            
            # Tools & Practices
            "git", "github", "gitlab", "bitbucket", "svn", "jira", "confluence",
            "linux", "unix", "windows server", "nginx", "apache",
            "agile", "scrum", "kanban", "devops", "sre", "microservices", "microservice",
            "rest", "restful", "rest api", "restful api", "graphql", "grpc", "protobuf",
            "api design", "api development", "oauth", "jwt", "websocket", "websockets",
            
            # Testing
            "testing", "unit testing", "integration testing", "pytest", "jest", "mocha",
            "selenium", "cypress", "postman", "debugging", "tdd", "bdd",
            
            # Architecture & Patterns
            "oop", "object-oriented", "design patterns", "solid", "mvc", "mvvm",
            "event-driven", "serverless", "lambda", "cloud functions",
            "orm", "odm", "sqlalchemy", "prisma", "mongoose", "sequelize",
            
            # Data Engineering
            "etl", "data pipeline", "data warehouse", "data lake", "data modeling",
            "dbt", "snowflake", "redshift", "databricks", "data transformation",
            
            # Soft Skills (often in JDs)
            "problem solving", "problem-solving", "critical thinking", "communication",
            "team collaboration", "teamwork", "leadership", "project management",
            "agile methodology", "fast-paced", "self-motivated"
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in skill_patterns:
            # Use word boundary matching for more accurate detection
            pattern = r'\b' + skill.replace('.', r'\.').replace('+', r'\+') + r'\b'
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Normalize skill name for display
                display_skill = skill.replace('\\', '').title()
                if display_skill not in found_skills:
                    found_skills.append(display_skill)
        
        # Also extract from TECHNICAL SKILLS section if present
        skills_section = re.search(
            r'(?:TECHNICAL\s*SKILLS?|SKILLS?|TECHNOLOGIES|TECH\s*STACK)[:\s]*(.+?)(?=\n[A-Z]{2,}|\n\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        if skills_section:
            section_text = skills_section.group(1)
            # Extract comma or bullet separated items
            items = re.split(r'[,•\n|]', section_text)
            for item in items:
                item = item.strip()
                if item and len(item) > 1 and len(item) < 50:
                    # Clean up common prefixes
                    item = re.sub(r'^[-•]\s*', '', item)
                    if item and item not in found_skills:
                        found_skills.append(item)
        
        return list(set(found_skills))[:50]  # Return up to 50 unique skills


if __name__ == "__main__":
    # CLI usage for Kestra
    import sys
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            resume_text = f.read()
    else:
        resume_text = sys.stdin.read()
    
    agent = ResumeParserAgent()
    result = agent.parse(resume_text)
    print(result.model_dump_json(indent=2))

