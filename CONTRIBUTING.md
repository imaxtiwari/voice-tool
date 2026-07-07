## Branch naming
phase-{n}/{short-description}

## PR rules
- One issue per PR
- PR title format: [P{n}] {issue title}
- Link the issue in PR body with "Closes #N"
- No PR merges to main until phase gate passes 
  (see README for gate criteria per phase)

## Phase gates
- Phase 1 gate: both ChromaDB collections populated, 
  audit_gate.py exits 0
- Phase 2A gate: ft_version_log.json has a valid Azure file ID
- Phase 2B gate: curl localhost:8433/health returns 200
- Phase 3 gate: curl -X POST localhost:8433/rewrite returns 
  real diff (not stub)
- Phase 4 gate: panel renders in Gmail compose, 
  accept/reject writes to edit_log.db
- Phase 5 gate: /health shows ft_endpoint_active: true, 
  model_used: "ft" appears in edit_log
