"""
Cover Letter Agent - Generates personalized cover letters
"""
import json
import os
from typing import Optional
from together import Together
from models.schemas import (
    ParsedResume, ParsedJobDescription, GapAnalysis, CoverLetter
)


class CoverLetterAgent:
    """Agent responsible for generating personalized cover letters"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = Together(api_key=api_key or os.getenv("TOGETHER_API_KEY"))
        self.model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    
    def generate(
        self,
        resume: ParsedResume,
        jd: ParsedJobDescription,
        gap_analysis: GapAnalysis,
        tone: str = "professional"
    ) -> CoverLetter:
        """Generate a personalized cover letter"""
        
        prompt = f"""Write a professional cover letter for this job application.

CANDIDATE INFORMATION:
- Name: {resume.name or 'Candidate'}
- Current Role: {resume.experience[0].title if resume.experience else 'Professional'}
- Years of Experience: Approximately {len(resume.experience)} positions
- Key Skills: {', '.join(resume.skills[:8])}
- Matching Skills for Role: {', '.join(gap_analysis.matching_skills[:6])}
- Notable Projects: {', '.join(p.name for p in resume.projects[:3]) if resume.projects else 'Various technical projects'}

JOB INFORMATION:
- Role: {jd.role}
- Company: {jd.company or 'the company'}
- Required Skills: {', '.join(jd.required_skills[:6])}
- Key Responsibilities: {', '.join(jd.responsibilities[:4])}

TONE: {tone}

Write a cover letter that:
1. Opens with enthusiasm for the specific role and company
2. Highlights 2-3 key qualifications matching the job requirements
3. Includes a specific example of a relevant achievement
4. Addresses why you're interested in this company/role
5. Closes with a call to action

Format:
- 3-4 paragraphs
- 250-350 words
- Professional but personable tone
- Include specific, quantified achievements where possible

Return ONLY the cover letter text, no explanations."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert cover letter writer. Write compelling, personalized cover letters."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract key highlights
            highlights = self._extract_highlights(content, gap_analysis)
            
            return CoverLetter(
                content=content,
                tone=tone,
                word_count=len(content.split()),
                key_highlights=highlights
            )
            
        except Exception as e:
            # Generate fallback cover letter
            fallback = self._generate_fallback(resume, jd)
            return CoverLetter(
                content=fallback,
                tone=tone,
                word_count=len(fallback.split()),
                key_highlights=["Relevant experience highlighted", "Skills alignment mentioned"]
            )
    
    def _extract_highlights(self, content: str, gap_analysis: GapAnalysis) -> list:
        """Extract key highlights from the cover letter"""
        highlights = []
        
        # Check for skills mentioned
        matching = [s for s in gap_analysis.matching_skills if s.lower() in content.lower()]
        if matching:
            highlights.append(f"Emphasized matching skills: {', '.join(matching[:3])}")
        
        # Check for quantified achievements
        if any(char.isdigit() for char in content):
            highlights.append("Includes quantified achievements")
        
        # Check for company mention
        if "company" in content.lower() or "organization" in content.lower():
            highlights.append("Demonstrates company interest")
        
        return highlights if highlights else ["Personalized for the role", "Professional tone maintained"]
    
    def _generate_fallback(self, resume: ParsedResume, jd: ParsedJobDescription) -> str:
        """Generate a basic cover letter as fallback"""
        name = resume.name or "Candidate"
        role = jd.role
        company = jd.company or "your company"
        skills = ', '.join(resume.skills[:4]) if resume.skills else "relevant skills"
        
        return f"""Dear Hiring Manager,

I am writing to express my strong interest in the {role} position at {company}. With my background in {skills}, I am confident in my ability to contribute effectively to your team.

Throughout my career, I have developed expertise in technologies and methodologies that align closely with your requirements. My experience has equipped me with both technical proficiency and the collaborative skills necessary to deliver impactful results.

I am particularly drawn to this opportunity because it aligns with my passion for building innovative solutions. I am excited about the prospect of bringing my skills and enthusiasm to {company}.

Thank you for considering my application. I look forward to the opportunity to discuss how my background and skills would be an asset to your team.

Sincerely,
{name}"""


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
    tone = data.get("tone", "professional")
    
    agent = CoverLetterAgent()
    result = agent.generate(resume, jd, gap_analysis, tone)
    print(result.model_dump_json(indent=2))

