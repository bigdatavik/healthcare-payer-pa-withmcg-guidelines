-- Check if PT00001 exists in the table
SELECT 
    COUNT(*) as record_count,
    COUNT(DISTINCT record_type) as record_types
FROM healthcare_payer_pa_withmcg_guidelines_dev.main.patient_clinical_records
WHERE patient_id = 'PT00001';

-- Show sample records for PT00001
SELECT patient_id, record_type, record_id, LEFT(content, 100) as content_preview
FROM healthcare_payer_pa_withmcg_guidelines_dev.main.patient_clinical_records
WHERE patient_id = 'PT00001'
LIMIT 5;
