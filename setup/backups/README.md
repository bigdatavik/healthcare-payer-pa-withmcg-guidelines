# Backup Files

This folder contains backup versions of notebooks before major changes.

## Files

### `07e_uc_answer_mcg_ORIGINAL.py`
- **Date:** December 24, 2025
- **Version:** Original simple prompt
- **Prompt:**
  ```
  You are a medical reviewer answering MCG questionnaire questions.
  Use ONLY the provided clinical records to answer. 
  Answer with YES or NO followed by brief evidence.
  ```
- **Why backed up:** Before implementing smart temporal prompt with:
  - Temporal awareness (most recent values)
  - Cumulative count handling
  - Keyword recognition
  - Question-type specific guidance

## How to Restore

To restore a backup version:

1. Copy the backup file to `setup/`
   ```bash
   cp setup/backups/07e_uc_answer_mcg_ORIGINAL.py setup/07e_uc_answer_mcg.py
   ```

2. Deploy and run
   ```bash
   databricks bundle deploy --target dev
   # Then run the notebook in Databricks UI
   ```

## Current Version Comparison

| Feature | Original | Smart Prompt |
|---------|----------|--------------|
| Temporal awareness | ❌ | ✅ Uses most recent values |
| Cumulative counts | ❌ | ✅ Finds highest count |
| Keyword recognition | ❌ | ✅ Confirms, shows, Grade X |
| Question-specific guidance | ❌ | ✅ PT, imaging, severity |
| Example answers | ❌ | ✅ Shows format |
| Real-world data handling | ❌ | ✅ Works with messy data |

## Version History

- **v1 (Original):** Basic prompt, fails with temporal data
- **v2 (Smart Prompt):** Enhanced prompt with temporal/contextual awareness

