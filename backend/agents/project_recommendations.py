"""
Project Recommendation Agent - Intelligent, Tailored Project Suggestions

Fixed Issues:
1. ✅ Real learning resources with URLs (not templates)
2. ✅ Specific open-source project suggestions
3. ✅ Tailored fallback projects based on gap type
4. ✅ Better LLM prompt with constraints
5. ✅ Input validation
6. ✅ Structured resources with types
7. ✅ Skill difficulty progression
8. ✅ Context for why each recommendation
"""
import json
import os
import logging
from typing import Optional, List, Dict, Any
from together import Together
from models.schemas import (
    GapAnalysis, ProjectRecommendations, ProjectRecommendation, LearningPath
)

logger = logging.getLogger(__name__)


class ProjectRecommendationAgent:
    """
    Intelligent project recommendation agent
    
    Features:
    - Real learning resources with URLs
    - Difficulty-based skill progression
    - Tailored projects based on gap type
    - Specific open-source project suggestions
    """
    
    # Real learning resources for skills
    SKILL_RESOURCES = {
        "python": {
            "resources": [
                {"title": "Python Official Tutorial", "url": "https://docs.python.org/3/tutorial/", "type": "documentation"},
                {"title": "Real Python Tutorials", "url": "https://realpython.com/", "type": "tutorial"},
                {"title": "Codecademy Python Course", "url": "https://www.codecademy.com/learn/learn-python-3", "type": "course"},
                {"title": "Python Crash Course (Book)", "url": "https://nostarch.com/pythoncrashcourse2e", "type": "book"},
            ],
            "timeline": "2-4 weeks",
            "difficulty": 1,
            "projects": ["CLI tool", "Web scraper", "Data analysis script"]
        },
        "fastapi": {
            "resources": [
                {"title": "FastAPI Official Docs", "url": "https://fastapi.tiangolo.com/tutorial/", "type": "documentation"},
                {"title": "Real Python FastAPI Guide", "url": "https://realpython.com/fastapi-python-web-apis/", "type": "tutorial"},
                {"title": "TestDriven.io FastAPI Course", "url": "https://testdriven.io/courses/tdd-fastapi/", "type": "course"},
            ],
            "timeline": "1-3 weeks",
            "difficulty": 2,
            "projects": ["REST API", "CRUD app", "Authentication system"]
        },
        "mongodb": {
            "resources": [
                {"title": "MongoDB University", "url": "https://university.mongodb.com/", "type": "course"},
                {"title": "MongoDB Manual", "url": "https://www.mongodb.com/docs/manual/", "type": "documentation"},
                {"title": "Real Python MongoDB Guide", "url": "https://realpython.com/introduction-to-mongodb-and-python/", "type": "tutorial"},
            ],
            "timeline": "1-2 weeks",
            "difficulty": 2,
            "projects": ["Document store", "Blog backend", "User management"]
        },
        "postgresql": {
            "resources": [
                {"title": "PostgreSQL Tutorial", "url": "https://www.postgresqltutorial.com/", "type": "tutorial"},
                {"title": "PostgreSQL Docs", "url": "https://www.postgresql.org/docs/", "type": "documentation"},
                {"title": "Mode SQL Tutorial", "url": "https://mode.com/sql-tutorial/", "type": "tutorial"},
            ],
            "timeline": "1-2 weeks",
            "difficulty": 2,
            "projects": ["Database design", "Query optimization", "Data modeling"]
        },
        "docker": {
            "resources": [
                {"title": "Docker Getting Started", "url": "https://docs.docker.com/get-started/", "type": "documentation"},
                {"title": "Docker for Beginners", "url": "https://docker-curriculum.com/", "type": "tutorial"},
                {"title": "Play with Docker", "url": "https://labs.play-with-docker.com/", "type": "interactive"},
            ],
            "timeline": "1-2 weeks",
            "difficulty": 2,
            "projects": ["Containerize an app", "Multi-container setup", "Docker Compose project"]
        },
        "kubernetes": {
            "resources": [
                {"title": "Kubernetes Basics", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/", "type": "documentation"},
                {"title": "KodeKloud K8s Course", "url": "https://kodekloud.com/courses/kubernetes-for-the-absolute-beginners/", "type": "course"},
                {"title": "Katacoda K8s Labs", "url": "https://www.katacoda.com/courses/kubernetes", "type": "interactive"},
            ],
            "timeline": "3-6 weeks",
            "difficulty": 3,
            "projects": ["Deploy app to K8s", "Helm charts", "CI/CD pipeline"]
        },
        "aws": {
            "resources": [
                {"title": "AWS Free Tier", "url": "https://aws.amazon.com/free/", "type": "platform"},
                {"title": "AWS Skill Builder", "url": "https://skillbuilder.aws/", "type": "course"},
                {"title": "A Cloud Guru AWS", "url": "https://acloudguru.com/", "type": "course"},
            ],
            "timeline": "4-8 weeks",
            "difficulty": 3,
            "projects": ["Deploy to EC2", "S3 static site", "Lambda functions"]
        },
        "git": {
            "resources": [
                {"title": "Git Official Book", "url": "https://git-scm.com/book/en/v2", "type": "documentation"},
                {"title": "Learn Git Branching", "url": "https://learngitbranching.js.org/", "type": "interactive"},
                {"title": "GitHub Skills", "url": "https://skills.github.com/", "type": "course"},
            ],
            "timeline": "1 week",
            "difficulty": 1,
            "projects": ["Contribute to OSS", "Manage a project", "PR workflow"]
        },
        "rest api": {
            "resources": [
                {"title": "RESTful API Design", "url": "https://restfulapi.net/", "type": "documentation"},
                {"title": "REST API Tutorial", "url": "https://www.restapitutorial.com/", "type": "tutorial"},
                {"title": "Postman Learning Center", "url": "https://learning.postman.com/", "type": "tutorial"},
            ],
            "timeline": "1-2 weeks",
            "difficulty": 2,
            "projects": ["Build REST API", "API documentation", "API testing"]
        },
        "microservices": {
            "resources": [
                {"title": "Microservices.io", "url": "https://microservices.io/", "type": "documentation"},
                {"title": "Martin Fowler on Microservices", "url": "https://martinfowler.com/microservices/", "type": "article"},
                {"title": "Building Microservices (Book)", "url": "https://www.oreilly.com/library/view/building-microservices-2nd/9781492034018/", "type": "book"},
            ],
            "timeline": "4-6 weeks",
            "difficulty": 3,
            "projects": ["Split monolith", "Service mesh", "Event-driven system"]
        },
        "grpc": {
            "resources": [
                {"title": "gRPC Official Docs", "url": "https://grpc.io/docs/", "type": "documentation"},
                {"title": "gRPC Python Quickstart", "url": "https://grpc.io/docs/languages/python/quickstart/", "type": "tutorial"},
            ],
            "timeline": "2-3 weeks",
            "difficulty": 3,
            "projects": ["gRPC service", "Protobuf schemas", "Streaming APIs"]
        },
    }
    
    # Popular open-source projects for contribution
    OPEN_SOURCE_PROJECTS = {
        "python": [
            {"name": "FastAPI", "url": "https://github.com/tiangolo/fastapi", "label": "good first issue"},
            {"name": "Requests", "url": "https://github.com/psf/requests", "label": "help wanted"},
            {"name": "Django", "url": "https://github.com/django/django", "label": "easy pickings"},
        ],
        "fastapi": [
            {"name": "FastAPI", "url": "https://github.com/tiangolo/fastapi", "label": "good first issue"},
            {"name": "FastAPI-Users", "url": "https://github.com/fastapi-users/fastapi-users", "label": "help wanted"},
            {"name": "SQLModel", "url": "https://github.com/tiangolo/sqlmodel", "label": "good first issue"},
        ],
        "mongodb": [
            {"name": "PyMongo", "url": "https://github.com/mongodb/mongo-python-driver", "label": "good first issue"},
            {"name": "MongoEngine", "url": "https://github.com/MongoEngine/mongoengine", "label": "help wanted"},
            {"name": "Motor", "url": "https://github.com/mongodb/motor", "label": "good first issue"},
        ],
        "docker": [
            {"name": "Docker Compose", "url": "https://github.com/docker/compose", "label": "good first issue"},
            {"name": "Awesome Docker", "url": "https://github.com/veggiemonk/awesome-docker", "label": "help wanted"},
        ],
        "kubernetes": [
            {"name": "Kubernetes", "url": "https://github.com/kubernetes/kubernetes", "label": "good first issue"},
            {"name": "Helm", "url": "https://github.com/helm/helm", "label": "good first issue"},
            {"name": "K9s", "url": "https://github.com/derailed/k9s", "label": "help wanted"},
        ],
    }
    
    # Skill difficulty levels (1=easy, 2=medium, 3=hard)
    SKILL_DIFFICULTY = {
        "python": 1, "javascript": 1, "git": 1, "sql": 1, "html": 1, "css": 1,
        "rest api": 2, "fastapi": 2, "django": 2, "flask": 2, "mongodb": 2,
        "postgresql": 2, "docker": 2, "react": 2, "nodejs": 2, "typescript": 2,
        "kubernetes": 3, "aws": 3, "azure": 3, "gcp": 3, "microservices": 3,
        "grpc": 3, "kafka": 3, "terraform": 3, "ci/cd": 2,
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = Together(api_key=api_key or os.getenv("TOGETHER_API_KEY"))
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    
    def recommend(self, gap_analysis: GapAnalysis) -> ProjectRecommendations:
        """Generate tailored project recommendations based on skill gaps"""
        
        # Input validation
        if not gap_analysis:
            return ProjectRecommendations(
                recommended_projects=[],
                learning_paths=[],
                open_source_ideas=["Complete a gap analysis first to get personalized recommendations"]
            )
        
        # Safely extract skills
        missing_skills = [s.skill for s in (gap_analysis.missing_skills or [])]
        missing_tools = gap_analysis.missing_tools or []
        
        if not missing_skills and not missing_tools:
            return ProjectRecommendations(
                recommended_projects=[],
                learning_paths=[],
                open_source_ideas=[
                    "Great job! No significant skill gaps identified.",
                    "Consider contributing to open-source projects in your area of expertise",
                    "Build portfolio projects to showcase your existing skills"
                ]
            )
        
        # Categorize gaps by priority
        categorized_gaps = self._categorize_gaps(missing_skills, missing_tools, gap_analysis)
        
        # Generate recommendations
        projects = self._get_project_recommendations(missing_skills, missing_tools, categorized_gaps)
        learning_paths = self._get_learning_paths(missing_skills, missing_tools)
        open_source = self._get_open_source_ideas(missing_skills, missing_tools)
        
        return ProjectRecommendations(
            recommended_projects=projects,
            learning_paths=learning_paths,
            open_source_ideas=open_source
        )
    
    def _categorize_gaps(
        self, 
        missing_skills: List[str], 
        missing_tools: List[str],
        gap_analysis: GapAnalysis
    ) -> Dict[str, List[str]]:
        """Categorize gaps by priority"""
        
        critical = []
        important = []
        nice_to_have = []
        
        for skill_gap in (gap_analysis.missing_skills or []):
            skill = skill_gap.skill
            if skill_gap.importance == "required":
                # Check if it's a critical skill
                if skill_gap.category == "critical":
                    critical.append(skill)
                else:
                    important.append(skill)
            else:
                nice_to_have.append(skill)
        
        # Tools are generally important but not critical
        for tool in missing_tools:
            important.append(tool)
        
        return {
            "critical": critical,
            "important": important,
            "nice_to_have": nice_to_have
        }
    
    def _get_project_recommendations(
        self, 
        missing_skills: List[str], 
        missing_tools: List[str],
        categorized_gaps: Dict[str, List[str]]
    ) -> List[ProjectRecommendation]:
        """Get tailored project recommendations"""
        
        all_gaps = missing_skills[:5] + missing_tools[:3]
        
        if not all_gaps:
            return []
        
        # Try LLM first
        try:
            projects = self._get_llm_projects(all_gaps, categorized_gaps)
            if projects:
                return projects
        except Exception as e:
            logger.warning(f"LLM project generation failed: {e}")
        
        # Fallback to tailored projects
        return self._get_tailored_fallback_projects(missing_skills, missing_tools, categorized_gaps)
    
    def _fix_json_formatting(self, text: str) -> str:
        """
        Fix common JSON formatting issues from LLM output:
        - Remove markdown code blocks
        - Remove comments
        - Remove trailing commas
        - Fix single quotes in property names
        - Handle common formatting issues
        """
        import re

        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        # Remove comments (// and /* */)
        text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

        # Remove trailing commas before closing brackets/braces
        text = re.sub(r',(\s*[}\]])', r'\1', text)

        # Fix single quotes around property names (conservative approach)
        # Match patterns like 'name': or 'description':
        text = re.sub(r"'(\w+)'(\s*:)", r'"\1"\2', text)

        # Fix single quotes around string values, but be careful with apostrophes
        # Only fix quotes at start/end of values, not in the middle
        text = re.sub(r':\s*"([^"]*?\'[^"]*?)"', r': "\1"', text)  # Handle apostrophes in quoted strings
        text = re.sub(r"'([^']*?)'(\s*[,}])", r'"\1"\2', text)  # Fix remaining single quotes

        return text.strip()
    
    def _get_llm_projects(
        self, 
        all_gaps: List[str],
        categorized_gaps: Dict[str, List[str]]
    ) -> List[ProjectRecommendation]:
        """Get AI-generated project recommendations"""
        
        critical_str = ", ".join(categorized_gaps.get("critical", [])[:3]) or "None"
        important_str = ", ".join(categorized_gaps.get("important", [])[:3]) or "None"
        
        prompt = f"""Suggest 3 practical coding projects to help someone build portfolio pieces while learning these skills.

SKILL GAPS:
- Critical (must learn): {critical_str}
- Important: {important_str}
- All skills: {', '.join(all_gaps[:6])}

REQUIREMENTS:
1. Projects should be achievable in 2-4 weeks each
2. Focus on 2-3 skills per project (not overwhelming)
3. Each project should be portfolio-worthy
4. Include practical, real-world applications

CREATE A PROGRESSION:
- Project 1: Easiest (1-2 weeks), covers most critical skill
- Project 2: Medium (2-3 weeks), combines multiple skills
- Project 3: Ambitious (3-4 weeks), demonstrates mastery

Return a JSON array with exactly 3 projects. Use DOUBLE QUOTES for all strings:

[
  {{
    "name": "Project Name",
    "description": "What it does and why it's useful (2 sentences)",
    "skills_covered": ["skill1", "skill2"],
    "difficulty": "intermediate",
    "estimated_time": "2 weeks",
    "why_useful": "How this helps get the job",
    "resources": ["Resource 1", "Resource 2"],
    "github_ideas": ["Extension 1", "Extension 2"]
  }}
]

CRITICAL INSTRUCTIONS:
- Return ONLY valid JSON with double quotes, no single quotes
- No trailing commas
- No comments or explanations
- Ensure all property names and string values use double quotes
- Make sure the JSON is properly formatted and parseable"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a technical mentor helping developers build portfolio projects. Always return valid JSON with double quotes, no trailing commas, and no comments."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent JSON
            max_tokens=1500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean JSON - remove markdown code blocks
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        
        result_text = result_text.strip()
        
        # Fix common JSON issues
        result_text = self._fix_json_formatting(result_text)
        
        try:
            projects_data = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error at position {e.pos}: {e.msg}")

            # Log the problematic section for debugging
            start = max(0, e.pos - 100)
            end = min(len(result_text), e.pos + 100)
            problematic_snippet = result_text[start:end]
            logger.debug(f"Problematic JSON snippet (char {start}-{end}):\n{problematic_snippet}")

            # Try multiple fallback approaches
            success = False

            # Approach 1: Extract JSON array using regex
            import re
            json_match = re.search(r'\[[\s\S]*\]', result_text)
            if json_match and not success:
                try:
                    extracted = json_match.group(0)
                    # Clean extracted JSON
                    extracted = self._fix_json_formatting(extracted)
                    projects_data = json.loads(extracted)
                    logger.info("Successfully extracted JSON array using regex fallback")
                    success = True
                except Exception as e2:
                    logger.debug(f"Regex extraction failed: {e2}")

            # Approach 2: Try to fix the entire text and parse again
            if not success:
                try:
                    fixed_text = self._fix_json_formatting(result_text)
                    if fixed_text != result_text:  # Only try if something changed
                        projects_data = json.loads(fixed_text)
                        logger.info("Successfully parsed JSON after additional formatting fixes")
                        success = True
                except Exception as e3:
                    logger.debug(f"Additional formatting fixes failed: {e3}")

            # Approach 3: Try to extract individual objects
            if not success:
                try:
                    # Look for JSON objects within the text
                    object_matches = re.findall(r'\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}', result_text)
                    if object_matches and len(object_matches) >= 3:
                        # Try to reconstruct as array
                        array_text = '[' + ','.join(object_matches[:3]) + ']'
                        array_text = self._fix_json_formatting(array_text)
                        projects_data = json.loads(array_text)
                        logger.info("Successfully reconstructed JSON array from individual objects")
                        success = True
                except Exception as e4:
                    logger.debug(f"Object extraction failed: {e4}")

            # If all approaches failed, raise the original error
            if not success:
                logger.error(f"All JSON parsing attempts failed. Raw response: {result_text[:500]}...")
                raise e
        
        projects = []
        for i, p in enumerate(projects_data[:3]):
            priority = ["critical", "important", "nice_to_have"][min(i, 2)]
            
            projects.append(ProjectRecommendation(
                name=p.get("name", f"Project {i+1}"),
                description=p.get("description", "Build a practical project"),
                skills_covered=p.get("skills_covered", all_gaps[:3]),
                difficulty=p.get("difficulty", "intermediate"),
                estimated_time=p.get("estimated_time", "2-3 weeks"),
                resources=p.get("resources", []),
                github_ideas=p.get("github_ideas", [])
            ))
        
        return projects
    
    def _get_tailored_fallback_projects(
        self,
        missing_skills: List[str],
        missing_tools: List[str],
        categorized_gaps: Dict[str, List[str]]
    ) -> List[ProjectRecommendation]:
        """Generate fallback projects based on actual gap types"""
        
        projects = []
        skills_lower = [s.lower() for s in missing_skills]
        tools_lower = [t.lower() for t in missing_tools]
        
        # Check gap categories
        has_backend_gaps = any(s in skills_lower for s in ["python", "fastapi", "django", "flask", "nodejs"])
        has_database_gaps = any(s in skills_lower for s in ["mongodb", "postgresql", "sql", "nosql"])
        has_api_gaps = any(s in skills_lower for s in ["rest api", "graphql", "grpc"])
        has_devops_gaps = any(t in tools_lower for t in ["docker", "kubernetes", "aws", "azure"])
        
        # Project 1: Backend/API focused (if relevant)
        if has_backend_gaps or has_api_gaps:
            covered_skills = [s for s in missing_skills if s.lower() in ["python", "fastapi", "rest api", "mongodb", "postgresql"]][:3]
            projects.append(ProjectRecommendation(
                name="RESTful API with Authentication",
                description="Build a production-ready REST API with user authentication, CRUD operations, and database integration. This demonstrates core backend skills that every developer needs.",
                skills_covered=covered_skills or missing_skills[:3],
                difficulty="intermediate",
                estimated_time="2-3 weeks",
                resources=[
                    "FastAPI Documentation - https://fastapi.tiangolo.com/",
                    "Real Python REST API Guide",
                    "JWT Authentication Tutorial"
                ],
                github_ideas=[
                    "Add rate limiting and caching",
                    "Implement role-based access control",
                    "Add comprehensive API tests",
                    "Create OpenAPI documentation"
                ]
            ))
        
        # Project 2: Full-stack or Database focused
        if has_database_gaps or (has_backend_gaps and len(projects) < 2):
            covered_skills = [s for s in missing_skills if s.lower() in ["mongodb", "postgresql", "sql", "fastapi", "python"]][:3]
            projects.append(ProjectRecommendation(
                name="Task Management System",
                description="Build a complete task management application with database, user management, and CRUD operations. Perfect for demonstrating database design and backend architecture skills.",
                skills_covered=covered_skills or missing_skills[:3],
                difficulty="intermediate",
                estimated_time="3-4 weeks",
                resources=[
                    "Database Design Tutorial",
                    "SQLAlchemy or MongoEngine docs",
                    "Full Stack Python guide"
                ],
                github_ideas=[
                    "Add real-time notifications",
                    "Implement task sharing/collaboration",
                    "Add analytics dashboard",
                    "Deploy to cloud platform"
                ]
            ))
        
        # Project 3: DevOps or Microservices
        if has_devops_gaps or len(projects) < 3:
            covered_skills = [s for s in (missing_skills + missing_tools) if s.lower() in ["docker", "kubernetes", "microservices", "aws", "ci/cd"]][:3]
            projects.append(ProjectRecommendation(
                name="Containerized Microservice Application",
                description="Create a multi-service application with Docker containers, demonstrating modern deployment practices and microservice architecture.",
                skills_covered=covered_skills or (missing_skills + missing_tools)[:3],
                difficulty="intermediate",
                estimated_time="3-4 weeks",
                resources=[
                    "Docker Getting Started - https://docs.docker.com/get-started/",
                    "Docker Compose Tutorial",
                    "Microservices.io patterns"
                ],
                github_ideas=[
                    "Add Kubernetes deployment files",
                    "Set up CI/CD pipeline",
                    "Add monitoring with Prometheus",
                    "Implement service mesh"
                ]
            ))
        
        # If still no projects, add generic one
        if not projects:
            projects.append(ProjectRecommendation(
                name="Portfolio Project",
                description="Build a project that demonstrates your target skills. Focus on clean code, documentation, and real-world applicability.",
                skills_covered=missing_skills[:3] + missing_tools[:2],
                difficulty="intermediate",
                estimated_time="3-4 weeks",
                resources=["GitHub", "Your preferred learning platform"],
                github_ideas=["Add comprehensive tests", "Write clear documentation", "Deploy to production"]
            ))
        
        return projects[:3]
    
    def _get_learning_paths(
        self, 
        missing_skills: List[str], 
        missing_tools: List[str]
    ) -> List[LearningPath]:
        """Generate learning paths with real resources and difficulty progression"""
        
        all_skills = missing_skills + missing_tools
        
        # Sort by difficulty (learn easier skills first)
        sorted_skills = sorted(
            all_skills,
            key=lambda s: self.SKILL_DIFFICULTY.get(s.lower(), 2)
        )
        
        paths = []
        
        for skill in sorted_skills[:5]:
            skill_lower = skill.lower()
            skill_info = self.SKILL_RESOURCES.get(skill_lower, {})
            
            difficulty_level = self.SKILL_DIFFICULTY.get(skill_lower, 2)
            difficulty_name = ["beginner", "intermediate", "advanced"][difficulty_level - 1]
            timeline = ["1-2 weeks", "2-4 weeks", "4-6 weeks"][difficulty_level - 1]
            
            # Get real resources or generate sensible defaults
            if skill_info:
                resources = [r["title"] + " - " + r["url"] for r in skill_info.get("resources", [])[:3]]
                projects = skill_info.get("projects", [f"Build a project using {skill}"])
            else:
                resources = [
                    f"Official {skill} documentation",
                    f"YouTube: {skill} tutorials for beginners",
                    f"Udemy/Coursera: {skill} courses"
                ]
                projects = [f"Build a small project using {skill}"]
            
            paths.append(LearningPath(
                skill=skill,
                resources=resources,
                timeline=skill_info.get("timeline", timeline),
                projects=projects[:2]
            ))
        
        return paths
    
    def _get_open_source_ideas(
        self, 
        missing_skills: List[str], 
        missing_tools: List[str]
    ) -> List[str]:
        """Generate specific open-source contribution ideas"""
        
        ideas = []
        all_gaps = missing_skills + missing_tools
        
        # Add specific project recommendations
        for tech in all_gaps[:4]:
            tech_lower = tech.lower()
            if tech_lower in self.OPEN_SOURCE_PROJECTS:
                for proj in self.OPEN_SOURCE_PROJECTS[tech_lower][:2]:
                    ideas.append(
                        f"🔗 {proj['name']} ({tech}) - Look for '{proj['label']}' issues at {proj['url']}"
                    )
        
        # Add general advice
        ideas.extend([
            "📝 Improve documentation on projects using your target technologies",
            "🧪 Write tests for open-source projects (always needed!)",
            "🐛 Fix 'good first issue' bugs to build experience and reputation",
            "💡 Create tutorials or examples for libraries you're learning"
        ])
        
        return ideas[:8]


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
        gap_analysis = GapAnalysis(**data)
    else:
        # Test with mock data
        from models.schemas import SkillGap
        gap_analysis = GapAnalysis(
            matching_skills=["Python", "Git"],
            missing_skills=[
                SkillGap(skill="FastAPI", importance="required", category="high"),
                SkillGap(skill="MongoDB", importance="required", category="high"),
                SkillGap(skill="Docker", importance="preferred", category="medium"),
            ],
            matching_tools=["Git"],
            missing_tools=["Kubernetes"],
            matching_keywords=["Backend"],
            missing_keywords=["Microservices"],
            experience_match=True,
            seniority_match=True,
            overall_match_percentage=60.0,
            strengths=["Python experience"],
            weaknesses=["Missing FastAPI"]
        )
    
    agent = ProjectRecommendationAgent()
    result = agent.recommend(gap_analysis)
    print(result.model_dump_json(indent=2))
