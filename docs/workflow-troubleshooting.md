# Workflow Troubleshooting

## Workflow Not Found

**Symptom:** `Workflow '<name>' not found at <path>`

**Causes:**

1. The workflow JSON file does not exist in `WORKFLOW_DIR`.
2. `CLAUDE_WORKFLOWS_DIR` is set to the wrong path.

**Fix:**

- Check available workflows in the default directory.
- Set `CLAUDE_WORKFLOWS_DIR` to the correct path if workflows live elsewhere:

```bash
export CLAUDE_WORKFLOWS_DIR=/path/to/your/workflows
claude-dispatch my-workflow
```

## Validation Failed

**Symptom:** `Workflow '<name>' validation failed: ... (see src/claude_cli/_workflow_schema.json for the expected schema)`

**Common mistakes:**

| Error | Cause | Fix |
| --- | --- | --- |
| `non-empty 'workflow' string` | Missing or empty top-level `workflow` key | Add `"workflow": "my-workflow-name"` |
| `'stages' array` | `stages` is missing or not a list | Ensure `"stages": [...]` exists |
| `Duplicate stage name` | Two stages share the same `name` | Rename one stage |
| `'parallel' must be bool` | `parallel` is a string like `"true"` | Use JSON `true` or `false` |
| `'max_concurrent' must be int` | `max_concurrent` is a string | Use an integer without quotes |
| `'depends_on' must be a list of strings` | `depends_on` is a string or contains non-strings | Use `["stage-a", "stage-b"]` |
| `'isolation' must be one of none|worktree|container` | Invalid isolation value | Use `"none"`, `"worktree"`, or `"container"` |

## Circular Dependency

**Symptom:** `Circular dependency detected: stage-a -> stage-b -> stage-a`

**Fix:** Remove or break the cycle by restructuring `depends_on` entries.

## Unknown Dependency

**Symptom:** `Stage 'stage-b' depends on unknown stage 'stage-a'. Available stages: stage-b, stage-c`

**Fix:** Check the `depends_on` list for typos. Stage names are case-sensitive.

## Tier Gate Skipped

**Symptom:** A stage shows `⏭️ skip` in the execution plan.

**Fix:** The current tier is below the gate threshold. Check your tier with:

```bash
claude-dispatch my-workflow --dry-run
```

The `Tier:` line shows your current level. To raise it, update `state.json` or set the appropriate hardware profile.
