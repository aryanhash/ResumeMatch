#!/usr/bin/env python3
"""
Gap Analysis Task - Kestra Pipeline Task

Compares resume against job requirements to identify skill gaps.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.base_task import BaseTask
from agents.gap_analysis import GapAnalysisAgent
from models.schemas import ParsedResume, ParsedJobDescription


def main():
    task = BaseTask("gap_analysis")
    
    def execute():
        resume_file = os.getenv('RESUME_INPUT', 'parsed_resume.json')
        jd_file = os.getenv('JD_INPUT', 'parsed_jd.json')
        output_file = os.getenv('GAP_OUTPUT', 'gap_analysis.json')
        
        # Load inputs with validation
        resume = task.load_json(resume_file, ParsedResume)
        jd = task.load_json(jd_file, ParsedJobDescription)
        
        task.logger.info(f"Analyzing: {resume.name} vs {jd.role}")
        
        # Run gap analysis
        agent = GapAnalysisAgent()
        result = agent.analyze(resume, jd)
        
        # Log summary
        matching_count = len(result.matching_skills) if hasattr(result, 'matching_skills') else 0
        missing_count = len(result.missing_skills) if hasattr(result, 'missing_skills') else 0
        
        task.logger.info(f"  Matching skills: {matching_count}")
        task.logger.info(f"  Missing skills: {missing_count}")
        
        if hasattr(result, 'overall_match_percentage'):
            task.logger.info(f"  Match rate: {result.overall_match_percentage:.1f}%")
        
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

