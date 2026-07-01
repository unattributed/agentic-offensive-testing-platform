# Repository safety review for v0.1

## Result

The Sprint 11 slice-boundary audit passed. No prohibited tracked or historical path, tracked
symlink, or likely secret pattern was found.

```text
repository safety validation passed
repository release audit passed
tracked_files=295
history_commits=75
historical_paths=292
tracked_symlinks=0
history_secret_findings=0
```

The tracked-file count includes the staged slice 11.5 validator, audit, tests, and evidence note.
Later release documentation changes require the same audit to be rerun at closeout.

## Review scope

- current tracked path names;
- current tracked text using the repository secret-pattern boundary;
- every unique path appearing in reachable Git history;
- every reachable commit's text content using the same likely-secret patterns;
- tracked symlink inventory;
- ignored generated and local-only path policy; and
- regression behavior for deleted historical secrets.

## Finding remediated during review

The current-tree validator used uppercase `-I`, which controls binary-file handling, where
case-insensitive `-i` was intended. The scan therefore did not detect capitalized marker variants.
The option is corrected and a regression test proves an uppercase cookie marker in a normal file
fails validation.

## Deliberate exclusions

The validators and synthetic redaction or repository-safety fixtures contain pattern fragments or
known inert marker strings. Those specific files are excluded from content matching and remain
covered by focused behavior tests. Generated caches and `.aotp` local outputs remain excluded from
non-Git archive scans.

## Limitation

Pattern matching cannot prove that arbitrary data is non-sensitive. Release discipline still
requires human diff review, alias-only examples, ignored private and generated paths, and rejection
of unexpected files.
