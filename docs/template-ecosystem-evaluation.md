# External YAML and YARA template evaluation

AOTP can benefit from mature template ecosystems, but executable community content is supply-chain input, not trusted application code. No external template or rule is vendored by default.

## Decisions

| Project | Useful capability | License and safety decision | AOTP use |
|---|---|---|---|
| [ProjectDiscovery Nuclei templates](https://github.com/projectdiscovery/nuclei-templates) | YAML identity, metadata, protocol categories, matchers, template signing, validation, and community coverage | MIT repository, but individual templates can send active requests or use code, JavaScript, headless, fuzzing, discovery, and high concurrency | Candidate external source only. Pin a commit and bundle hash, require signatures, explicitly allow template IDs and passive capabilities, deny code and discovery, and pass every execution through AOTP policy and rate limits |
| [OWASP ZAP Automation Framework](https://www.zaproxy.org/docs/automate/automation-framework/) | YAML plan structure, ordered jobs, environment scoping, job tests, and exit status | Use official documentation and generate AOTP-owned plans. Do not copy unknown community plans | Adopt ordered job and explicit environment concepts in the future ZAP adapter |
| [VirusTotal YARA](https://github.com/virustotal/yara) | Local pattern matching for provided files | BSD-3-Clause engine is a candidate dependency after review. YARA classifies content and does not establish exploitability | Candidate for offline scanning of explicitly provided SBOM, configuration, archive, or evidence artifacts |
| [Yara-Rules community rules](https://github.com/Yara-Rules/rules) | Large community rule collection | GPL-2.0 ruleset conflicts with simple proprietary vendoring and contains mixed operational quality | Do not vendor. An operator may reference a separately managed ruleset only after legal, provenance, and false-positive review |
| YARA Forge and other aggregated feeds | Curated bundles from many sources | Per-rule provenance and license obligations vary | Do not vendor or auto-download until every included source is inventoried |

## Controls implemented

`config/template-sources.example.yaml` and `aotp template-source-verify` provide a real local provenance gate:

- canonical HTTPS GitHub repository URL;
- exact 40-character source commit;
- local-only bundle path that cannot escape the registry directory;
- verified SHA256 over a file or deterministic directory tree;
- recorded SPDX license and completed-license-review flag;
- explicit enable flag;
- allowed template or rule identifiers;
- allowed capabilities;
- mandatory denial of code execution, credential attacks, destructive payloads, and target discovery; and
- mandatory signature enforcement for Nuclei sources.

The registry never downloads, updates, or executes a source. A future adapter must separately enforce scope, target, action, rate, approval, and evidence policy.

## Operational recommendation

Start with a very small private Nuclei allowlist limited to passive HTTP metadata and TLS observations. Validate upstream syntax with the pinned Nuclei version, disable unsigned templates, disable code and JavaScript protocols, keep concurrency at one, and map every template ID to an AOTP case and approval class.

Use YARA only against sponsor-provided artifacts stored in the configured evidence workspace. Treat a rule match as an observation requiring provenance, artifact hash, rule hash, and human verification.
