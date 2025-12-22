# databricks.yml Fix Applied

## Issue Discovered

When deploying the PA project, encountered errors that didn't happen in the FraudDetection project:
```
Warning: required field "source_code_path" is not set
Error: Missing app source code path
```

## Root Cause

The PA project's `databricks.yml` had an **incorrect apps section** that is NOT supported by Databricks:

### ❌ What Was Wrong
```yaml
apps:
  pa_dashboard:
    resources:            # ← NOT SUPPORTED
      - name: pa-dashboard-job
        job:
          id: ${resources.jobs.pa_setup_job.id}
    config:              # ← NOT SUPPORTED
      command: ["streamlit", "run", "app.py"]
      env:               # ← NOT SUPPORTED
        - name: CATALOG_NAME
          value: ...
```

### ✅ What's Correct (From Fraud Project)
```yaml
apps:
  pa_dashboard:
    name: pa-dashboard-${var.environment}
    description: "Prior Authorization AI Agent Dashboard - ${var.environment}"
    source_code_path: ./dashboard
```

## The Fix

Apps section requires **only 3 fields**:
1. `name` - App name (use hyphens)
2. `description` - Description
3. `source_code_path` - Path to Streamlit folder

**No** `resources`, `config`, `command`, or `env` blocks!

## Where Do Environment Variables Go?

Environment variables belong in `dashboard/app.yaml`, which is **auto-generated** by:
```bash
python generate_app_yaml.py dev
```

This reads `config.yaml` and generates `dashboard/app.yaml` with all env vars.

## Changes Applied

1. ✅ Fixed apps section to 3-field pattern
2. ✅ Removed unsupported `resources` and `config` blocks
3. ✅ Added `environment` variable for consistency
4. ✅ Simplified job names to match fraud project
5. ✅ Removed unnecessary `include` and `auth_type`

## Updated Fraudtemplate

To prevent this mistake in future projects, added to fraudtemplate:

1. ✅ **`reference-files/databricks.yml`** - Correct template with comments
2. ✅ **`reference-files/DATABRICKS_YML_MISTAKES.md`** - Common mistakes guide
3. ✅ **Updated `PROJECT_BLUEPRINT.md`** - Critical rules section

## Key Takeaways

**For Apps:**
- Only 3 fields needed
- Environment variables go in `dashboard/app.yaml` (auto-generated)
- Use hyphens in app names

**For Jobs:**
- Use `${var.environment}` for environment suffix
- Pass variables via `base_parameters`

**Pattern Source:**
Follow the FraudDetectionForClaimsData project - it's the proven reference!

## Deployment Now Works

```bash
databricks bundle deploy --target dev
# ✅ Deployment complete!
```

No more "missing source_code_path" errors! 🎉
