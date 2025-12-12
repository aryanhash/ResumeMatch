"""
LaTeX-based PDF Resume Generator - Creates professional PDF resumes using LaTeX
Based on Jake's Resume template: https://www.overleaf.com/latex/templates/jakes-resume/syzfjbzwjncs
"""
import os
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from io import BytesIO
import re

logger = logging.getLogger(__name__)


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters"""
    if not text:
        return ""
    # Escape special characters
    text = text.replace('\\', '\\textbackslash{}')
    text = text.replace('&', '\\&')
    text = text.replace('%', '\\%')
    text = text.replace('$', '\\$')
    text = text.replace('#', '\\#')
    text = text.replace('^', '\\textasciicircum{}')
    text = text.replace('_', '\\_')
    text = text.replace('{', '\\{')
    text = text.replace('}', '\\}')
    text = text.replace('~', '\\textasciitilde{}')
    return text


def format_phone(phone: str) -> str:
    """Format phone number for display"""
    if not phone:
        return ""
    # Remove non-digits
    digits = re.sub(r'\D', '', phone)
    # Format as XXX-XXX-XXXX if 10 digits
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return phone


class LaTeXResumeGenerator:
    """Generates professional PDF resumes using LaTeX (Jake's Resume template)"""
    
    def __init__(self, template_path: Optional[str] = None):
        """Initialize the generator with template path"""
        if template_path is None:
            # Default to the template in the same directory
            template_path = Path(__file__).parent / "latex_resume_template.tex"
        self.template_path = Path(template_path)
        
    def _check_latex_available(self) -> bool:
        """Check if pdflatex is available"""
        try:
            result = subprocess.run(
                ['pdflatex', '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _generate_education_entries(self, education: list) -> str:
        """Generate LaTeX code for education section"""
        if not education:
            return ""
        
        entries = []
        for edu in education:
            institution = escape_latex(edu.get('institution', ''))
            location = escape_latex(edu.get('location', ''))
            
            # Build degree text
            degree_parts = []
            if edu.get('degree'):
                degree_parts.append(escape_latex(edu['degree']))
            if edu.get('field_of_study'):
                degree_parts.append(f"in {escape_latex(edu['field_of_study'])}")
            degree_text = ", ".join(degree_parts) if degree_parts else ""
            
            # Format dates
            year = escape_latex(edu.get('year', ''))
            if not year and edu.get('start_date') and edu.get('end_date'):
                start = escape_latex(edu['start_date'])
                end = escape_latex(edu['end_date'])
                year = f"{start} -- {end}"
            
            if institution and degree_text:
                entries.append(
                    f"    \\resumeSubheading\n"
                    f"      {{{institution}}}{{{location}}}\n"
                    f"      {{{degree_text}}}{{{year}}}"
                )
        
        return "\n".join(entries)
    
    def _generate_experience_entries(self, experience: list, improved_bullets: dict) -> str:
        """Generate LaTeX code for experience section"""
        if not experience:
            return ""
        
        entries = []
        for exp in experience:
            title = escape_latex(exp.get('title', ''))
            company = escape_latex(exp.get('company', ''))
            location = escape_latex(exp.get('location', ''))
            duration = escape_latex(exp.get('duration', ''))
            
            # Format entry - title on left, duration on right
            # Company and location on second line
            entry = (
                f"    \\resumeSubheading\n"
                f"      {{{title}}}{{{duration}}}\n"
                f"      {{{company}}}{{{location}}}"
            )
            
            # Add bullet points
            bullets = exp.get('description', [])
            if bullets:
                entry += "\n      \\resumeItemListStart"
                for bullet in bullets:
                    # Use improved bullet if available
                    improved = improved_bullets.get(bullet, bullet)
                    bullet_text = escape_latex(improved)
                    entry += f"\n        \\resumeItem{{{bullet_text}}}"
                entry += "\n      \\resumeItemListEnd"
            
            entries.append(entry)
        
        return "\n".join(entries)
    
    def _generate_project_entries(self, projects: list) -> str:
        """Generate LaTeX code for projects section"""
        if not projects:
            return ""
        
        entries = []
        for proj in projects:
            name = escape_latex(proj.get('name', ''))
            technologies = proj.get('technologies', [])
            tech_str = ", ".join([escape_latex(t) for t in technologies[:5]])
            duration = escape_latex(proj.get('duration', ''))
            
            # Format project heading
            if tech_str:
                heading = f"\\textbf{{{name}}} $|$ \\emph{{{tech_str}}}"
            else:
                heading = f"\\textbf{{{name}}}"
            
            entry = f"      \\resumeProjectHeading\n          {{{heading}}}{{{duration}}}"
            
            # Add project description
            if proj.get('description'):
                entry += "\n          \\resumeItemListStart"
                desc = escape_latex(proj['description'])
                entry += f"\n            \\resumeItem{{{desc}}}"
                if proj.get('impact'):
                    impact = escape_latex(proj['impact'])
                    entry += f"\n            \\resumeItem{{Impact: {impact}}}"
                entry += "\n          \\resumeItemListEnd"
            
            entries.append(entry)
        
        return "\n".join(entries)
    
    def _generate_skills_content(self, skills: list) -> str:
        """Generate LaTeX code for technical skills section"""
        if not skills:
            return ""
        
        # Group skills into categories if possible
        # For now, just create a simple list
        skills_text = ", ".join([escape_latex(s) for s in skills[:30]])
        
        # Try to categorize common skills
        languages = []
        frameworks = []
        tools = []
        libraries = []
        other = []
        
        # Simple categorization (can be improved)
        for skill in skills[:30]:
            skill_lower = skill.lower()
            if any(x in skill_lower for x in ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 'ruby', 'php', 'sql', 'r', 'swift', 'kotlin', 'scala']):
                languages.append(skill)
            elif any(x in skill_lower for x in ['react', 'vue', 'angular', 'django', 'flask', 'fastapi', 'express', 'spring', 'node', 'next', 'laravel', 'rails']):
                frameworks.append(skill)
            elif any(x in skill_lower for x in ['git', 'docker', 'kubernetes', 'aws', 'gcp', 'azure', 'jenkins', 'ci/cd', 'linux', 'unix']):
                tools.append(skill)
            elif any(x in skill_lower for x in ['pandas', 'numpy', 'matplotlib', 'tensorflow', 'pytorch', 'scikit', 'junit', 'jest']):
                libraries.append(skill)
            else:
                other.append(skill)
        
        categories = []
        if languages:
            categories.append(f"\\textbf{{Languages}}{{: {', '.join([escape_latex(s) for s in languages[:10]])}}}")
        if frameworks:
            categories.append(f"\\textbf{{Frameworks}}{{: {', '.join([escape_latex(s) for s in frameworks[:10]])}}}")
        if tools:
            categories.append(f"\\textbf{{Developer Tools}}{{: {', '.join([escape_latex(s) for s in tools[:10]])}}}")
        if libraries:
            categories.append(f"\\textbf{{Libraries}}{{: {', '.join([escape_latex(s) for s in libraries[:10]])}}}")
        if other:
            categories.append(f"\\textbf{{Other}}{{: {', '.join([escape_latex(s) for s in other[:10]])}}}")
        
        if categories:
            return " \\\\\n     ".join(categories)
        else:
            return f"\\textbf{{Skills}}{{: {skills_text}}}"
    
    def generate(self, result: Dict[str, Any]) -> BytesIO:
        """Generate PDF resume from the processing result using LaTeX"""
        parsed_resume = result.get('parsed_resume', {})
        rewritten_resume = result.get('rewritten_resume', {})
        
        # Check if LaTeX is available
        if not self._check_latex_available():
            logger.warning("pdflatex not available, falling back to ReportLab")
            raise RuntimeError("LaTeX (pdflatex) is not available. Please install a LaTeX distribution.")
        
        # Read template
        if not self.template_path.exists():
            raise FileNotFoundError(f"LaTeX template not found: {self.template_path}")
        
        with open(self.template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Auto-replace fullpage with geometry if fullpage is not available
        # fullpage is deprecated and not in TeX Live basic, geometry produces same result
        if '\\usepackage[empty]{fullpage}' in template:
            template = template.replace(
                '\\usepackage[empty]{fullpage}',
                '\\usepackage[margin=0.5in]{geometry}'
            )
            # Remove manual margin adjustments since geometry handles it
            # Match from "% Adjust margins" through all \addtolength commands
            template = re.sub(
                r'% Adjust margins\s*\n(?:\s*\\addtolength\{[^}]+\}\{[^}]+\}\s*\n)+',
                '% Margins handled by geometry package (replaces fullpage)\n',
                template,
                flags=re.MULTILINE
            )
        
        # Make glyphtounicode conditional (may not be available in all distributions)
        if '\\input{glyphtounicode}' in template:
            template = template.replace(
                '\\input{glyphtounicode}',
                '\\IfFileExists{glyphtounicode.tex}{\\input{glyphtounicode}}{}'
            )
        
        # Prepare data
        name = escape_latex(parsed_resume.get('name', 'CANDIDATE NAME'))
        phone = format_phone(parsed_resume.get('phone', ''))
        email = escape_latex(parsed_resume.get('email', 'email@example.com'))
        
        # Extract LinkedIn and GitHub usernames
        linkedin_raw = parsed_resume.get('linkedin', '')
        linkedin_username = ''
        if linkedin_raw:
            linkedin_username = linkedin_raw.replace('https://linkedin.com/in/', '').replace('http://linkedin.com/in/', '').replace('linkedin.com/in/', '').replace('www.linkedin.com/in/', '').strip('/')
        
        github_raw = parsed_resume.get('github', '')
        github_username = ''
        if github_raw:
            github_username = github_raw.replace('https://github.com/', '').replace('http://github.com/', '').replace('github.com/', '').replace('www.github.com/', '').strip('/')
        
        # Build contact info line
        contact_parts = []
        if phone:
            contact_parts.append(phone)
        if email:
            contact_parts.append(f"\\href{{mailto:{email}}}{{\\underline{{{email}}}}}")
        if linkedin_username:
            contact_parts.append(f"\\href{{https://linkedin.com/in/{linkedin_username}}}{{\\underline{{linkedin.com/in/{linkedin_username}}}}}")
        if github_username:
            contact_parts.append(f"\\href{{https://github.com/{github_username}}}{{\\underline{{github.com/{github_username}}}}}")
        
        contact_info = " $|$ ".join(contact_parts) if contact_parts else email
        
        # Generate sections
        education_entries = self._generate_education_entries(parsed_resume.get('education', []))
        
        # Build improved bullets map
        improved_bullets = {}
        for item in rewritten_resume.get('improved_bullets', []):
            original = item.get('original', '')
            improved = item.get('improved', '')
            improved_bullets[original] = improved
        
        # Use enhanced experience if available
        experience_data = rewritten_resume.get('enhanced_experience', parsed_resume.get('experience', []))
        # Convert to dict format if needed
        if experience_data and hasattr(experience_data[0], 'model_dump'):
            experience_data = [exp.model_dump() if hasattr(exp, 'model_dump') else exp for exp in experience_data]
        experience_entries = self._generate_experience_entries(experience_data, improved_bullets)
        
        # Projects
        projects = parsed_resume.get('projects', [])
        if projects and hasattr(projects[0], 'model_dump'):
            projects = [p.model_dump() if hasattr(p, 'model_dump') else p for p in projects]
        project_entries = self._generate_project_entries(projects)
        
        # Skills
        skills = rewritten_resume.get('reordered_skills', parsed_resume.get('skills', []))
        skills_content = self._generate_skills_content(skills)
        
        # Fill template - conditionally include sections
        latex_content = template.replace('{{NAME}}', name)
        latex_content = latex_content.replace('{{CONTACT_INFO}}', contact_info)
        
        # Handle education section
        if education_entries:
            latex_content = latex_content.replace('{{EDUCATION_ENTRIES}}', education_entries)
        else:
            # Remove entire education section if empty
            latex_content = re.sub(
                r'%-----------EDUCATION-----------.*?\\resumeSubHeadingListEnd\s*%-----------EXPERIENCE-----------',
                '%-----------EXPERIENCE-----------',
                latex_content,
                flags=re.DOTALL
            )
        
        # Handle experience section
        if experience_entries:
            latex_content = latex_content.replace('{{EXPERIENCE_ENTRIES}}', experience_entries)
        else:
            # Remove entire experience section if empty
            latex_content = re.sub(
                r'%-----------EXPERIENCE-----------.*?\\resumeSubHeadingListEnd\s*%-----------PROJECTS-----------',
                '%-----------PROJECTS-----------',
                latex_content,
                flags=re.DOTALL
            )
        
        # Handle projects section
        if project_entries:
            latex_content = latex_content.replace('{{PROJECT_ENTRIES}}', project_entries)
        else:
            # Remove entire projects section if empty
            latex_content = re.sub(
                r'%-----------PROJECTS-----------.*?\\resumeSubHeadingListEnd\s*%-----------TECHNICAL SKILLS-----------',
                '%-----------TECHNICAL SKILLS-----------',
                latex_content,
                flags=re.DOTALL
            )
        
        latex_content = latex_content.replace('{{SKILLS_CONTENT}}', skills_content if skills_content else '\\textbf{Skills}{: None listed}')
        
        # Create temporary directory for LaTeX compilation
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = Path(tmpdir) / "resume.tex"
            pdf_file = Path(tmpdir) / "resume.pdf"
            
            # Write LaTeX file
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(latex_content)
            
            # Compile LaTeX to PDF
            try:
                # Run pdflatex (twice for proper references and cross-references)
                for i in range(2):
                    result = subprocess.run(
                        ['pdflatex', '-interaction=nonstopmode', '-output-directory', str(tmpdir), str(tex_file)],
                        capture_output=True,
                        timeout=30,
                        cwd=tmpdir,
                        text=True
                    )
                    if result.returncode != 0:
                        error_output = result.stderr or result.stdout
                        logger.error(f"LaTeX compilation error (attempt {i+1}): {error_output}")
                        
                        # Detect missing package errors and provide helpful message
                        if "File `" in error_output and ".sty' not found" in error_output:
                            # Extract package name from error message
                            package_match = re.search(r"File `([^']+)\.sty' not found", error_output)
                            if package_match:
                                package_name = package_match.group(1)
                                error_msg = (
                                    f"LaTeX package '{package_name}' is missing. "
                                    f"Install it with: sudo tlmgr install {package_name} "
                                    f"or install full TeX Live: brew install --cask mactex"
                                )
                                logger.error(error_msg)
                                if i == 1:
                                    raise RuntimeError(error_msg)
                            else:
                                if i == 1:
                                    raise RuntimeError(f"LaTeX compilation failed: Missing package detected. {error_output[:500]}")
                        else:
                            # On first attempt, try to continue; on second, fail
                            if i == 1:
                                raise RuntimeError(f"LaTeX compilation failed after 2 attempts: {error_output[:1000]}")
                
                # Read PDF
                if not pdf_file.exists():
                    raise FileNotFoundError("PDF was not generated")
                
                with open(pdf_file, 'rb') as f:
                    pdf_bytes = f.read()
                
                return BytesIO(pdf_bytes)
                
            except subprocess.TimeoutExpired:
                raise RuntimeError("LaTeX compilation timed out")
            except Exception as e:
                logger.error(f"Error compiling LaTeX: {str(e)}")
                raise
