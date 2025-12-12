#!/bin/bash

# Simple commit review script using Cline
COMMIT=${1:-HEAD}

echo "🔍 Reviewing commit: $COMMIT"

git show "$COMMIT" | cline "Review this commit for:
- Bugs and logic errors
- Security vulnerabilities
- Performance issues
- Code smells
- Best practice violations

Format response as JSON with fields:
- severity: critical|high|medium|low
- file: filename
- issue: description
- suggestion: fix recommendation
- line: line number (if applicable)"
