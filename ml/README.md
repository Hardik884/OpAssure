# OpAssure — AI/ML

**Owner:** AI/ML developer
**Stack:** Python

> Status: skeleton only. No models are implemented yet.

## Structure

| Path                  | Purpose                                                          |
| --------------------- | ---------------------------------------------------------------- |
| `src/operator_twin/`  | Operator digital twin — models an operator's working patterns.   |
| `src/eta/`            | Task time estimation.                                            |
| `src/anomaly/`        | Unusual machine/operator behaviour detection.                    |
| `src/safety/`         | Safety risk scoring and alert logic.                             |
| `src/training/`       | Operator training / coaching recommendations.                   |
| `src/features/`       | Shared feature engineering from telemetry.                       |
| `src/evaluation/`     | Metrics and evaluation against `data/ground_truth/`.             |
| `src/common/`         | Shared utilities.                                                |
| `notebooks/`          | Exploration notebooks.                                           |
| `models/`             | Trained model artifacts (git-ignored).                           |
| `experiments/`        | Experiment configs and results.                                  |
| `tests/`              | ML unit tests.                                                   |

## Local development

```bash
cd ml
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```
