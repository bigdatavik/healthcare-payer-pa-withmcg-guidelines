# Timestamp Fields Fix

## Issue

When running `setup/01_create_catalog_schema.py`, got error:
```
[WRONG_COLUMN_DEFAULTS_FOR_DELTA_FEATURE_NOT_ENABLED] 
Failed to execute CREATE TABLE command because it assigned a column DEFAULT value,
but the corresponding table feature was not enabled.
```

## Root Cause

Tables had `DEFAULT CURRENT_TIMESTAMP()` in the schema, but:
1. This Delta feature isn't enabled by default
2. The data generation notebooks weren't setting `created_at`/`updated_at` values anyway

## Fix Applied

### 1. Removed DEFAULT from Table Schemas (`01_create_catalog_schema.py`)
Changed from:
```sql
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
```

To:
```sql
created_at TIMESTAMP
```

### 2. Added Timestamp Values in Data Generation

**`02_generate_clinical_data.py`** - Added `created_at` to:
- Clinical notes (line 359)
- Lab results (lines 136, 161)
- Imaging reports (line 427)
- PT notes (line 483)

**`03_generate_guidelines_data.py`** - Added `created_at` to:
- All MCG guidelines
- All InterQual guidelines  
- All Medicare policies

**`04_generate_pa_requests.py`** - Added both:
- `created_at`
- `updated_at`

## Result

✅ All three tables now have proper timestamp fields:
- `patient_clinical_records` → `created_at`
- `clinical_guidelines` → `created_at`
- `authorization_requests` → `created_at`, `updated_at`

✅ All data generation notebooks populate these fields with `datetime.now()`

## Run the Notebooks Again

The setup should now work without errors!
