# Slice 14.2: Bounded Campaign Workspace

Implemented `.aotp/campaigns/<program>/<run-id>/` with safe lowercase path components, path and
symlink containment, mode-0700 directories, mode-0600 files, atomic JSON and Markdown writes, and
separate evidence, state, and report areas.

Proof: workspace tests cover permissions, atomic replacement, traversal, absolute paths, unsafe
components, symlinked paths, and unapproved artifact areas.
