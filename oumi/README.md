# 🧠 OUMI ATS Classifier

Fine-tuned model for accurate ATS (Applicant Tracking System) classification.

## Overview

OUMI provides deterministic, consistent ATS scoring before Together AI performs the resume rewrite. This ensures:

- **Accurate Classification**: Resumes are classified into ATS buckets (Strong, Moderate, Weak, Not ATS-friendly)
- **Consistent Signals**: Structured data feeds into Together AI for better rewrites
- **Missing Category Detection**: Identifies formatting issues, skill mismatches, keyword gaps

## Installation

```bash
pip install oumi
```

## Dataset Structure

```
oumi/sample_dataset/
├── train.jsonl     # 50 training examples
├── val.jsonl       # 10 validation examples
└── test.jsonl      # 10 test examples
```

### Distribution (Balanced for Training)

| Bucket | Train | Val | Test | Total |
|--------|-------|-----|------|-------|
| **Strong** | 22 | 4 | 4 | 30 |
| **Moderate** | 12 | 3 | 2 | 17 |
| **Weak** | 8 | 2 | 2 | 12 |
| **Not ATS-friendly** | 8 | 1 | 2 | 11 |
| **Total** | 50 | 10 | 10 | 70 |

## Training Data Format

Each line in the JSONL files follows this comprehensive schema:

```json
{
  "resume": {
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
    "experience_count": 4,
    "years_total": 5,
    "has_summary": true,
    "has_projects": true,
    "has_education": true,
    "has_certifications": true,
    "certifications_count": 2,
    "raw_text_length": 3300,
    "contact_info_complete": true
  },
  "jd": {
    "role": "Backend Developer",
    "company": "TechStartup",
    "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "preferred_skills": ["Kubernetes", "AWS"],
    "seniority": "mid",
    "keywords": ["REST API", "microservices", "database design", "testing"],
    "experience_years": "3-5"
  },
  "feature_scores": {
    "skill_match_required": 100,
    "skill_match_preferred": 100,
    "keyword_match": 90,
    "formatting_score": 95,
    "experience_alignment": 100
  },
  "labels": {
    "ats_score": 96,
    "bucket": "strong",
    "confidence": 1.0,
    "source": "calculated"
  }
}
```

### Field Explanations

#### Resume Features
| Field | Type | Description |
|-------|------|-------------|
| `skills` | list[str] | Technical skills extracted from resume |
| `experience_count` | int | Number of job experiences |
| `years_total` | float | Total years of experience |
| `has_summary` | bool | Whether resume has a summary section |
| `has_projects` | bool | Whether resume has a projects section |
| `has_education` | bool | Whether resume has education section |
| `has_certifications` | bool | Whether resume has certifications |
| `certifications_count` | int | Number of certifications |
| `raw_text_length` | int | Length of resume text |
| `contact_info_complete` | bool | Whether contact info (email, phone) is complete |

#### Job Description Features
| Field | Type | Description |
|-------|------|-------------|
| `role` | str | Job title |
| `company` | str | Company name |
| `required_skills` | list[str] | Must-have skills |
| `preferred_skills` | list[str] | Nice-to-have skills |
| `seniority` | str | entry/junior/mid/senior/lead/principal |
| `keywords` | list[str] | ATS keywords to match |
| `experience_years` | str | Required experience range |

#### Feature Scores (Intermediate Calculations)
| Field | Type | Description |
|-------|------|-------------|
| `skill_match_required` | int | % of required skills matched (0-100) |
| `skill_match_preferred` | int | % of preferred skills matched (0-100) |
| `keyword_match` | int | % of keywords matched (0-100) |
| `formatting_score` | int | Resume formatting quality (0-100) |
| `experience_alignment` | int | Experience relevance to role (0-100) |

#### Labels (Training Targets)
| Field | Type | Description |
|-------|------|-------------|
| `ats_score` | int | Overall ATS score (0-100) |
| `bucket` | str | Classification: strong/moderate/weak/not_ats_friendly |
| `confidence` | float | Label confidence (0.0-1.0) |
| `source` | str | How label was generated: "calculated", "human" |

## How Scores Are Calculated

Each training example has transparent, reproducible scoring:

```python
# Score calculation formula
overall_score = (
    skill_match_required * 0.35 +
    skill_match_preferred * 0.10 +
    keyword_match * 0.25 +
    formatting_score * 0.15 +
    experience_alignment * 0.15
)

# Bucket assignment
if overall_score >= 80:
    bucket = "strong"
elif overall_score >= 60:
    bucket = "moderate"
elif overall_score >= 40:
    bucket = "weak"
else:
    bucket = "not_ats_friendly"
```

## Training the Model

### 1. Install OUMI

```bash
pip install oumi
```

### 2. Train on Classification Task

```bash
oumi train \
  --dataset ./sample_dataset \
  --model llama-3-8b \
  --task classification \
  --target-field labels.bucket \
  --epochs 5 \
  --batch-size 8 \
  --learning-rate 2e-5 \
  --output ./models/finetuned_ats
```

**Important**: Train on `bucket` (classification), not `ats_score` (regression).

### 3. Evaluate on Test Set

```bash
oumi eval \
  --model ./models/finetuned_ats \
  --dataset ./sample_dataset/test.jsonl \
  --metrics accuracy,f1,confusion_matrix
```

### 4. Export for Inference

```bash
oumi export \
  --model ./models/finetuned_ats \
  --format onnx \
  --output ./models/ats_classifier.onnx
```

## Integration with AutoApply AI

The OUMI classifier is integrated into the pipeline:

```
Resume + JD → OUMI Classifier → Signals → Together AI Rewriter
```

### Python Usage

```python
from agents.oumi_ats_classifier import OumiATSClassifier

classifier = OumiATSClassifier(model_path="./models/finetuned_ats")
result = classifier.classify(parsed_resume, parsed_jd)

print(result)
# {
#   "ats_bucket": "moderate",
#   "ats_score": 72,
#   "confidence": 0.85,
#   "missing_categories": [...],
#   "signals": {...},
#   "recommendations": [...]
# }
```

### Kestra Pipeline Usage

```yaml
- id: oumi_classification
  type: io.kestra.plugin.scripts.python.Commands
  inputFiles:
    parsed_resume.json: "{{ outputs.parse_resume.outputFiles['parsed_resume.json'] }}"
    parsed_jd.json: "{{ outputs.analyze_jd.outputFiles['parsed_jd.json'] }}"
  commands:
    - python -c "
      from agents.oumi_ats_classifier import OumiATSClassifier
      classifier = OumiATSClassifier()
      result = classifier.classify(resume, jd)
      "
```

## Classification Buckets

| Bucket | Score Range | Description |
|--------|-------------|-------------|
| **Strong** | 80-100 | Excellent ATS compatibility, likely to pass |
| **Moderate** | 60-79 | Good compatibility, minor improvements needed |
| **Weak** | 40-59 | Significant gaps, needs optimization |
| **Not ATS-friendly** | 0-39 | Major issues, requires substantial rewrite |

## Edge Cases in Training Data

The dataset includes important edge cases:

| Scenario | Count | Purpose |
|----------|-------|---------|
| Wrong tech stack (COBOL → Cloud) | 2 | Test stack mismatch detection |
| Overqualified (35 years exp) | 1 | Test experience mismatch |
| Underqualified (0 experience) | 2 | Test entry-level detection |
| Minimal resume (< 500 chars) | 3 | Test formatting penalty |
| Missing contact info | 4 | Test completeness check |
| Career changer (QA → Dev) | 2 | Test cross-domain matching |
| Legacy skills (Perl, COBOL) | 2 | Test obsolete tech detection |

## Missing Categories Detected

- `skills_mismatch` - Required skills not found in resume
- `keyword_density` - Low keyword match with job description
- `formatting_issues` - Missing sections (summary, contact, etc.)
- `role_alignment` - Experience doesn't match role level
- `experience_gap` - Years of experience too low/high

## Fallback Mode

If OUMI is not installed or model not available, the classifier falls back to a rule-based system that provides similar functionality using the same scoring heuristics:

```python
class OumiATSClassifier:
    def classify(self, resume, jd):
        if self.oumi_available:
            return self._oumi_inference(resume, jd)
        else:
            return self._rule_based_fallback(resume, jd)
```

## Generating More Training Data

To expand the dataset, use the data generator script:

```python
from oumi.data_generator import generate_training_examples

# Generate 500 examples with realistic distributions
examples = generate_training_examples(
    count=500,
    bucket_distribution={
        "strong": 0.30,
        "moderate": 0.30,
        "weak": 0.25,
        "not_ats_friendly": 0.15
    },
    include_edge_cases=True
)

# Save to JSONL
with open("train_expanded.jsonl", "w") as f:
    for ex in examples:
        f.write(json.dumps(ex) + "\n")
```

## Metrics to Track

| Metric | Target | Description |
|--------|--------|-------------|
| Accuracy | > 85% | Overall bucket prediction accuracy |
| F1 (macro) | > 0.80 | Balanced performance across buckets |
| Confusion Matrix | - | Identify misclassification patterns |
| Calibration | < 0.10 ECE | Confidence matches accuracy |

## License

MIT License - see root LICENSE file
