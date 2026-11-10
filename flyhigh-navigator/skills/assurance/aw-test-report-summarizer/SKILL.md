---
name: aw-test-report-summarizer
description: "Summarize test results for a release: user-story coverage, results, feature readiness, hotspots (critical, flaky, stable), defects by severity, most-failed tests with root cause, and the impact × likelihood grid."
---

# Test report summarizer (assurance)

## Measures

- **Coverage:** stories with at least one test case ÷ all stories; tested = stories with an executed case.
- **Results:** planned (cases in the release's plans), executed (latest result per case), passed, failed, skipped, self-healed.
- **Feature readiness:** features whose latest results have no failure.
- **Hotspots:** critical = always failing and high priority or ≥ 50% failure; flaky = mixed results or self-healed; stable = always passing.
- **Defects:** by status and severity, overall and by feature.
- **Impact × likelihood:** impact from the case priority; likelihood from failure rate and whether the case maps to changed code. Run High-High first.

## Output

`test_report.md`, ready for the gate review and the PMO steering pack.
