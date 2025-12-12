#!/usr/bin/env python3
"""
Analyze JD Task - Kestra Pipeline Task

Reads job description text and produces structured ParsedJobDescription JSON.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.base_task import BaseTask, validate_text_input
from agents.analyze_jd import JDAnalyzerAgent


def main():
    """Main entry point for the JD analysis task"""
    task = BaseTask("analyze_jd")
    
    def execute():
        input_file = os.getenv('JD_INPUT', 'jd.txt')
        output_file = os.getenv('JD_OUTPUT', 'parsed_jd.json')
        
        task.logger.info(f"Reading JD from: {input_file}")
        
        with open(input_file, 'r') as f:
            jd_text = f.read()
        
        jd_text = validate_text_input(jd_text, "Job Description", min_length=50)
        task.logger.info(f"JD length: {len(jd_text)} chars")
        
        # Analyze JD
        agent = JDAnalyzerAgent()
        result = agent.analyze(jd_text)
        
        # Log summary
        task.logger.info(f"Parsed: {result.role}")
        task.logger.info(f"  Required Skills: {len(result.required_skills)}")
        task.logger.info(f"  Preferred Skills: {len(result.preferred_skills)}")
        task.logger.info(f"  Keywords: {len(result.keywords)}")
        task.logger.info(f"  Seniority: {result.seniority.value}")
        
        # Validate
        if not result.required_skills:
            task.result.warnings.append("No required skills extracted")
        
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

