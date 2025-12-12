#!/usr/bin/env python3
"""
PR Review Generator using OpenRouter API
Generates CodeRabbit-style PR reviews with Cline branding
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
import subprocess

# OpenRouter API configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Default model - you can change this to any model supported by OpenRouter
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"  # or "openai/gpt-4", "google/gemini-pro", etc.


def get_pr_diff(base_ref: str, head_ref: str) -> str:
    """Get the diff between base and head branches."""
    try:
        result = subprocess.run(
            ["git", "diff", f"{base_ref}...{head_ref}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error getting diff: {e}", file=sys.stderr)
        return ""


def get_changed_files(base_ref: str, head_ref: str) -> List[str]:
    """Get list of changed files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"],
            capture_output=True,
            text=True,
            check=True
        )
        return [f.strip() for f in result.stdout.split("\n") if f.strip()]
    except subprocess.CalledProcessError:
        return []


def categorize_files(files: List[str]) -> Dict[str, List[str]]:
    """Categorize files by type."""
    categories = {
        "Documentation": [],
        "Backend": [],
        "Frontend": [],
        "Configuration": [],
        "Tests": [],
        "Other": []
    }
    
    for file in files:
        if any(file.endswith(ext) for ext in [".md", ".txt", ".rst"]):
            categories["Documentation"].append(file)
        elif file.startswith("backend/") or file.endswith(".py"):
            categories["Backend"].append(file)
        elif file.startswith("frontend/") or any(file.endswith(ext) for ext in [".tsx", ".ts", ".jsx", ".js", ".css"]):
            categories["Frontend"].append(file)
        elif any(file.endswith(ext) for ext in [".yml", ".yaml", ".json", ".toml", ".ini", ".config"]):
            categories["Configuration"].append(file)
        elif "test" in file.lower() or file.endswith("_test.py"):
            categories["Tests"].append(file)
        else:
            categories["Other"].append(file)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def generate_review(diff: str, changed_files: List[str], pr_title: str = "", pr_description: str = "") -> str:
    """Generate PR review using OpenRouter API."""
    
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")
    
    # Categorize files
    file_categories = categorize_files(changed_files)
    
    # Build the prompt for CodeRabbit-style review
    prompt = f"""You are Cline Bot, an AI code reviewer providing comprehensive PR reviews. Analyze the following pull request and provide a detailed review in the exact format specified below.

Pull Request Title: {pr_title or 'N/A'}
Pull Request Description: {pr_description or 'N/A'}

Changed Files ({len(changed_files)} files):
{chr(10).join(f"- {f}" for f in changed_files)}

File Categories:
{chr(10).join(f"- {cat}: {', '.join(files)}" for cat, files in file_categories.items())}

Diff:
```
{diff[:45000]}
```

IMPORTANT: You must format your response EXACTLY as follows. Do not include any markdown code blocks around the response - output the raw markdown directly:

## 🤖 Summary by Cline Bot

Provide a high-level summary with bullet points describing:
- The main changes and their purpose
- Key improvements or additions
- Any concerns or areas that need attention
- Overall assessment of the PR

💡 Tip: You can customize this high-level summary in your review settings.

## Walkthrough

Provide a narrative overview (2-4 sentences) explaining:
- What was modified and why
- The overall impact of the changes
- How the changes fit into the codebase

## Changes

Create a table with exactly two columns. Group files by category when appropriate:

| Cohort / File(s) | Summary |
|------------------|---------|
| Category or file path | Brief description of what changed in this category/file |

For example:
| Documentation | New comprehensive guide documenting... |
| `backend/agents/parse_resume.py` | Updated resume parsing logic to... |

## Estimated code review effort

🎯 [Complexity Level: 1-5] (Simple/Low/Medium/High/Very High) | ⏱️ ~[X] minutes

Provide a bulleted list of specific review tasks:
- Verify [specific aspect]
- Check [specific concern]
- Ensure [specific requirement]
- Review [specific area]

Focus your review on:
- Code quality, best practices, and maintainability
- Potential bugs, edge cases, or logic errors
- Security vulnerabilities or unsafe patterns
- Performance implications and optimizations
- Test coverage and testing needs
- Documentation completeness and accuracy
- Breaking changes or migration needs

Be thorough, constructive, and professional. Use emojis only in the estimated effort section."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",  # Optional: for analytics
        "X-Title": "Cline PR Review Bot"  # Optional: for analytics
    }
    
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are Cline Bot, an AI code reviewer that provides comprehensive, professional PR reviews. You are thorough, constructive, and focus on code quality, security, and best practices. Always format your reviews exactly as specified, using the exact section headers and structure provided. Never include markdown code blocks around your response - output raw markdown directly."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1200  # Set to work within free tier credit limits
    }
    
    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        review_content = result["choices"][0]["message"]["content"]
        
        return review_content
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenRouter API: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        raise


def format_review_for_github(review_content: str) -> str:
    """Format the review content for GitHub comment."""
    # The review_content should already have the proper format from the LLM
    # Just ensure it starts with the right header if it doesn't
    if not review_content.strip().startswith("##"):
        header = "## 🤖 Summary by Cline Bot\n\n"
        formatted = header + review_content
    else:
        formatted = review_content
    
    # Ensure the header says "Cline Bot" not "CodeRabbit"
    formatted = formatted.replace("Summary by CodeRabbit", "Summary by Cline Bot")
    formatted = formatted.replace("CodeRabbit", "Cline Bot")
    
    # Clean problematic Unicode characters that can cause encoding issues
    # Replace line separator (U+2028) and paragraph separator (U+2029) with standard newlines
    formatted = formatted.replace('\u2028', '\n').replace('\u2029', '\n\n')
    
    return formatted


def main():
    """Main function."""
    if len(sys.argv) < 3:
        print("Usage: pr_review.py <base_ref> <head_ref> [output_file]")
        sys.exit(1)
    
    base_ref = sys.argv[1]
    head_ref = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else "/tmp/review.md"
    
    # Get PR info from environment (set by GitHub Actions)
    pr_title = os.getenv("PR_TITLE", "")
    pr_description = os.getenv("PR_DESCRIPTION", "")
    
    print(f"Generating review for {base_ref}...{head_ref}", file=sys.stderr)
    
    # Get diff and changed files
    diff = get_pr_diff(base_ref, head_ref)
    changed_files = get_changed_files(base_ref, head_ref)
    
    if not diff:
        print("Warning: No diff found", file=sys.stderr)
        review_content = "⚠️ No changes detected in this PR."
    else:
        print(f"Found {len(changed_files)} changed files", file=sys.stderr)
        print(f"Diff size: {len(diff)} characters", file=sys.stderr)
        
        # Generate review
        try:
            review_content = generate_review(diff, changed_files, pr_title, pr_description)
            review_content = format_review_for_github(review_content)
        except Exception as e:
            print(f"Error generating review: {e}", file=sys.stderr)
            review_content = f"⚠️ Error generating review: {str(e)}"
    
    # Write to output file with explicit UTF-8 encoding
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(review_content, encoding='utf-8')
    
    print(f"Review written to {output_file}", file=sys.stderr)
    print(review_content)


if __name__ == "__main__":
    main()

