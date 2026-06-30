# Full-access engineering agent SOP

## Standing authority

An AI engineering agent assigned to this repository operates as a full-access agent with standing approval to perform all non-destructive work needed to complete the assigned sprint or slice. This includes reading repository files, creating and editing code and documentation, installing project-local dependencies, writing and conducting tests, running safety and quality checks, using Git and GitHub tooling, writing commit commentary, committing completed work, pushing development branches, merging approved work, and synchronizing `origin/main`.

This standing approval is limited to this repository and the assigned work. It does not authorize live security testing, scope expansion, disclosure, secret handling outside policy, destructive Git operations, repository deletion, branch deletion, credential changes, global configuration changes, or modification of unrelated projects. The agent must stop and ask before any destructive or materially out-of-scope action.

## Sprint and slice workflow

1. Start each development sprint from current `origin/main`.
2. Use a sprint branch named `sprint/<number>-<short-name>`.
3. For independently reviewable work, use slice branches named `slice/<number>.<number>-<short-name>` from the sprint branch.
4. Revalidate scope, policy, safety, and current code before implementation.
5. Write tests with the implementation, including negative fail-closed cases for security boundaries.
6. Run the slice validation commands and capture concise evidence in commit commentary or the sprint record.
7. Commit each completed slice with a lowercase message that describes the result.
8. Push the slice or sprint branch and review the complete diff.
9. Merge only after required checks pass and human review requirements are satisfied.
10. Synchronize `origin/main`, verify the remote commit, and leave the local worktree clean.

## Required validation

At minimum:

```bash
python3 -m compileall src tests
python3 -m pytest
./scripts/validate-repository-safety.sh
make test
```

Changes to policy, redaction, evidence, campaign control, adapters, or live-readiness require focused negative tests in addition to the full suite.

## Commit commentary

Each commit or associated review note records:

- sprint and slice identifier;
- intended behavior and safety boundary;
- important implementation choices;
- tests and commands run;
- result and evidence location;
- known limitations or deferred work; and
- confirmation that no private scope, target, secret, or evidence was committed.

Commit messages remain concise and lowercase. Commentary must not contain private assessment material.

## Closeout

The agent is expected to finish authorized engineering work end to end. Closeout requires passing checks, committed changes, remote synchronization, confirmed `origin/main` state, and a clean worktree. A local-only result is incomplete unless an external blocker prevents publication.

Once all scoped changes are properly reviewed, vetted, and tested, the agent must:

1. stage every scoped change and exclude unrelated work;
2. write a concise lowercase commit message and complete commit commentary;
3. create a signed commit and verify its signature;
4. push a development branch and open the required pull request;
5. wait for required CI checks, merge only after they pass, and verify post-merge CI;
6. synchronize local `main` with `origin/main`; and
7. verify matching commits and a clean worktree.

Do not stop at an uncommitted or branch-only result after validation has passed. If publication is
blocked, preserve the work and report the exact external blocker.
