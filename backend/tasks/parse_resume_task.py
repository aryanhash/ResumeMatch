#!/usr/bin/env python3
"""
Parse Resume Task - Kestra Pipeline Task

Reads resume text from input file and produces structured ParsedResume JSON.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.base_task import BaseTask, validate_text_input
from agents.parse_resume import ResumeParserAgent


def main():
    task = BaseTask("parse_resume")
    
    def execute():
        # Get input file from environment or default
        input_file = os.getenv('RESUME_INPUT', 'resume.txt')
        output_file = os.getenv('RESUME_OUTPUT', 'parsed_resume.json')
        
        # Load and validate input
        task.logger.info(f"Reading resume from: {input_file}")
        
        with open(input_file, 'r') as f:
            resume_text = f.read()
        
        resume_text = validate_text_input(resume_text, "Resume", min_length=100)
        task.logger.info(f"Resume length: {len(resume_text)} chars")
        
        # Parse resume
        agent = ResumeParserAgent()
        result = agent.parse(resume_text)
        
        # Validate required fields
        if not result.email:
            task.result.warnings.append("No email found - ATS may reject")
        if not result.skills:
            task.result.warnings.append("No skills section - check experience")
        
        # Log summary
        task.logger.info(f"Parsed: {result.name}")
        task.logger.info(f"  Skills: {len(result.skills)}")
        task.logger.info(f"  Experience: {len(result.experience)} entries")
        task.logger.info(f"  Education: {len(result.education)} entries")
        
        # Save output
        task.save_json(result, output_file)
        
        return result
    
    try:
        task.run_with_error_handling(execute)
        sys.exit(0)
    except Exception as e:
        task.logger.error(f"Task failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

