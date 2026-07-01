# Bug bounty program profile

The program profile records policy context separately from campaign scope:

- alias and platform reference
- policy acceptance date
- authorization and safe-harbor references
- confidentiality reference when applicable
- in-scope and out-of-scope aliases
- prohibited and permitted categories
- rate limits, report format, disclosure rules, and stop conditions
- sensitive workflows that require human approval
- an explicit checklist confirming policy acceptance, safe-harbor review, disclosure-rule review,
  and stop-condition review

Copy `config/program-profile.example.yaml` to an ignored private path. Never commit a real profile. The profile cannot expand technical scope.

Live policy evaluation compares every configured scope alias, category, and prohibition with the
profile. A missing checklist confirmation or any scope that is broader than the profile denies
before execution.
