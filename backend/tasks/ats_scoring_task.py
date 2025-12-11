#!/usr/bin/env python3
"""
ATS Scoring Task - Kestra Pipeline Task

Calculates ATS score with OUMI integration.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.base_task import BaseTask
from agents.ats_scorer import ATSScorerAgent
from models.schemas import ParsedResume, ParsedJobDescription, GapAnalysis


def main():
    task = BaseTask("ats_scoring")
    
    def execute():
        resume_file = os.getenv('RESUME_INPUT', 'parsed_resume.json')
        jd_file = os.getenv('JD_INPUT', 'parsed_jd.json')
        gap_file = os.getenv('GAP_INPUT', 'gap_analysis.json')
        oumi_file = os.getenv('OUMI_INPUT', 'oumi_classification.json')
        output_file = os.getenv('ATS_OUTPUT', 'ats_score.json')
        
        # Load inputs
        resume = task.load_json(resume_file, ParsedResume)
        jd = task.load_json(jd_file, ParsedJobDescription)
        gap_analysis = task.load_json(gap_file, GapAnalysis)
        
        # Load OUMI classification if available (for signal integration)
        oumi_data = None
        if os.path.exists(oumi_file):
            oumi_data = task.load_json(oumi_file)
            task.logger.info(f"OUMI signals loaded: bucket={oumi_data.get('ats_bucket')}")
        
        task.logger.info(f"Scoring: {resume.name} for {jd.role}")
        
        # Run ATS scoring
        agent = ATSScorerAgent()
        result = agent.score(resume, jd, gap_analysis)
        
        # Log summary
        task.logger.info(f"  Overall Score: {result.overall_score}/100")
        task.logger.info(f"  Bucket: {result.bucket.value}")
        task.logger.info(f"  Skill Match: {result.skill_match_score}")
        task.logger.info(f"  Issues: {len(result.issues)}")
        
        # Check for critical issues
        critical_issues = [i for i in result.issues if i.severity == "critical"]
        if critical_issues:
            task.result.warnings.append(f"{len(critical_issues)} critical issues found")
            for issue in critical_issues:
                task.logger.warning(f"  ⚠️ CRITICAL: {issue.issue}")
        
        task.save_json(result, output_file)
        
        # Save score for conditional logic
        with open('ats_score_value.txt', 'w') as f:
            f.write(str(result.overall_score))
        
        return result
    
    try:
        task.run_with_error_handling(execute)
        sys.exit(0)
    except Exception as e:
        task.logger.error(f"Task failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

