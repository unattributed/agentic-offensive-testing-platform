# External template evaluation evidence

## Functional result

AOTP now has a tested, non-executing provenance registry for external Nuclei YAML, ZAP plan, and YARA sources. It verifies canonical repository identity, exact source commit, local path containment, deterministic file or directory SHA256, license review, enable state, template allowlists, capability allowlists, mandatory dangerous-capability denials, and Nuclei signature requirements.

The implementation deliberately does not download, update, or execute community templates.

## Validation

Command:

```bash
python3 -m pytest tests/test_template_registry.py tests/test_cli.py
./scripts/validate-repository-safety.sh
```

Result:

```text
8 passed in 0.05s
repository safety validation passed
```

Tests verify a pinned local YAML bundle, detect modification after review, reject an escaping path, reject incomplete safety declarations, prove disabled example sources remain unusable, and exercise `aotp template-source-verify` against a local YARA file.

## Reuse decision

- Nuclei template metadata, signatures, exact template IDs, and strict protocol filtering are suitable for a future external adapter.
- ZAP ordered YAML jobs and explicit environment scoping are suitable design inputs for generated AOTP plans.
- VirusTotal YARA is suitable for future offline review of provided artifacts after dependency review.
- GPL-2.0 and mixed-license community rules are not vendored into the proprietary repository.
