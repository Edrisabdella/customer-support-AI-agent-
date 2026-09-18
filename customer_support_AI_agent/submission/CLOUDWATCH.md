# CloudWatch Evidence Checklist

The project rubric requires an `ERROR` metric filter and an alarm that triggers when the error count exceeds 5 during a 5-minute period.

## Required configuration

- Log source: AgentCore Runtime log group for the deployed agent.
- Metric filter pattern: `ERROR` (or an equivalent pattern clearly matching the runtime error records).
- Metric: count of matching error log events.
- Alarm threshold: **> 5**.
- Evaluation period: **5 minutes**.
- Evidence: screenshot showing the alarm name, metric, threshold, period, and current configuration.

## Evidence files

Save the real screenshot as:

`submission/evidence/07_cloudwatch_alarm.png`

Optionally also save a terminal/exported configuration file as `07_cloudwatch_alarm.txt`.

Do not claim this requirement is complete until the alarm exists in the real AWS account and the screenshot is captured.
