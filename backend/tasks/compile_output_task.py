#!/usr/bin/env python3
"""
Compile Output Task - Kestra Pipeline Task

Aggregates all results into final output, handling missing files gracefully.
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.base_task import BaseTask


def main():
    task = BaseTask("compile_output")
    
    def execute():
        output_file = os.getenv('OUTPUT_FILE', 'autoapply_result.json')
        
        # Define all expected files
        files = {
            'parsed_resume': os.getenv('RESUME_INPUT', 'parsed_resume.json'),
            'parsed_jd': os.getenv('JD_INPUT', 'parsed_jd.json'),
            'gap_analysis': os.getenv('GAP_INPUT', 'gap_analysis.json'),
            'oumi_classification': os.getenv('OUMI_INPUT', 'oumi_classification.json'),
            'ats_score': os.getenv('ATS_INPUT', 'ats_score.json'),
            'rewritten_resume': os.getenv('REWRITE_INPUT', 'rewritten_resume.json'),
            'cover_letter': os.getenv('COVER_INPUT', 'cover_letter.json'),
            'explanation': os.getenv('EXPLANATION_INPUT', 'explanation.json'),
            'project_recommendations': os.getenv('PROJECTS_INPUT', 'project_recommendations.json'),
        }
        
        # Build final output with graceful error handling
        final_output = {
            'status': 'complete',
            'timestamp': datetime.now().isoformat(),
            'pipeline_version': '2.0',
            'results': {},
            'errors': [],
            'warnings': []
        }
        
        # Load each file
        for key, filepath in files.items():
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        final_output['results'][key] = json.load(f)
                    task.logger.info(f"✓ Loaded: {key}")
                except json.JSONDecodeError as e:
                    error_msg = f"{key}: Invalid JSON - {e}"
                    final_output['errors'].append(error_msg)
                    task.logger.warning(f"⚠️ {error_msg}")
                except Exception as e:
                    error_msg = f"{key}: {str(e)}"
                    final_output['errors'].append(error_msg)
                    task.logger.warning(f"⚠️ {error_msg}")
            else:
                task.logger.info(f"- Skipped: {key} (file not found)")
        
        # Check minimum required files
        required = ['parsed_resume', 'parsed_jd', 'gap_analysis', 'ats_score']
        missing_required = [r for r in required if r not in final_output['results']]
        
        if missing_required:
            final_output['status'] = 'partial'
            final_output['warnings'].append(f"Missing required outputs: {missing_required}")
        
        # Extract summary
        if 'ats_score' in final_output['results']:
            ats = final_output['results']['ats_score']
            final_output['summary'] = {
                'ats_score': ats.get('overall_score', 0),
                'bucket': ats.get('bucket', 'unknown'),
                'issues_count': len(ats.get('issues', []))
            }
            task.logger.info(f"📊 ATS Score: {final_output['summary']['ats_score']}/100 ({final_output['summary']['bucket']})")
        
        # Save final output
        with open(output_file, 'w') as f:
            json.dump(final_output, f, indent=2)
        
        task.logger.info(f"✅ Final output: {output_file}")
        task.logger.info(f"  Status: {final_output['status']}")
        task.logger.info(f"  Results: {len(final_output['results'])}")
        task.logger.info(f"  Errors: {len(final_output['errors'])}")
        
        return final_output
    
    try:
        task.run_with_error_handling(execute)
        sys.exit(0)
    except Exception as e:
        task.logger.error(f"Task failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

