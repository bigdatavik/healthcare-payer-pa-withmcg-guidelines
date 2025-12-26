from databricks.sdk import WorkspaceClient
import json

w = WorkspaceClient()

# Query patient clinical records
query = """
SELECT patient_id, record_type, content
FROM healthcare_payer_pa_withmcg_guidelines_dev.main.patient_clinical_records
WHERE patient_id = 'PT00001'
ORDER BY record_type
"""

result = w.statement_execution.execute_statement(
    warehouse_id="148ccb90800933a1",
    statement=query,
    wait_timeout="30s"
)

print("Patient PT00001 Clinical Records:")
print("=" * 80)

if result.result and result.result.data_array:
    for row in result.result.data_array:
        patient_id = row[0]
        record_type = row[1]
        content = row[2]
        print(f"\n{record_type}:")
        print(f"  {content[:200]}...")
else:
    print("No records found!")
