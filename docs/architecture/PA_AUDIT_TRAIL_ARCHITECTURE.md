# PA Audit Trail Architecture

**Date:** 2026-01-01  
**Status:** ✅ IMPLEMENTED

---

## 🎯 Overview

The **PA Audit Trail** system provides detailed question-by-question tracking of MCG/InterQual guideline evaluations for each prior authorization request. This enables:

- **Compliance & Traceability**: Complete audit trail for regulatory requirements
- **Transparency**: Detailed evidence for each decision
- **Quality Assurance**: Review agent reasoning and accuracy
- **Clinical Review**: Support manual reviews with detailed breakdown

---

## 📊 Table Schema

### **Table: `pa_audit_trail`**

```sql
CREATE TABLE {catalog}.{schema}.pa_audit_trail (
  audit_id STRING NOT NULL 
    COMMENT 'Unique identifier: request_id_Q1, request_id_Q2, etc',
  request_id STRING NOT NULL 
    COMMENT 'Links to authorization_requests.request_id',
  question_number INT NOT NULL 
    COMMENT 'Sequential number: 1, 2, 3, 4...',
  question_text STRING NOT NULL 
    COMMENT 'MCG/InterQual question text',
  answer STRING NOT NULL 
    COMMENT 'YES or NO',
  evidence STRING 
    COMMENT 'Clinical evidence used to answer',
  evidence_source STRING 
    COMMENT 'CLINICAL_NOTE, LAB_RESULT, XRAY, PT_NOTE, etc',
  confidence DOUBLE 
    COMMENT 'AI confidence for this answer (0.0-1.0)',
  created_at TIMESTAMP 
    COMMENT 'When this Q&A was recorded'
)
USING DELTA
COMMENT 'Detailed audit trail showing MCG Q&A breakdown with evidence for each PA request'
```

### **Key Fields:**

| Field | Type | Purpose |
|-------|------|---------|
| `audit_id` | STRING | Composite key: `{request_id}_Q{question_number}` (e.g., "PA000001_Q1") |
| `request_id` | STRING | Links to parent PA request |
| `question_number` | INT | Sequential order (1, 2, 3, 4...) |
| `question_text` | STRING | Full MCG question text |
| `answer` | STRING | "YES", "NO", or "UNCLEAR" |
| `evidence` | STRING | Clinical evidence snippet used |
| `evidence_source` | STRING | Source type (CLINICAL_NOTE, IMAGING_REPORT, etc.) |
| `confidence` | DOUBLE | AI confidence score (0.0-1.0) |
| `created_at` | TIMESTAMP | When question was answered |

---

## 🔄 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PA Request Arrives                                       │
│    request_id: PA000001                                     │
│    patient_id: PT00001                                      │
│    procedure_code: 29881 (Knee Arthroscopy)                 │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. LangGraph Agent Loads MCG Guideline                      │
│    MCG-A-0398: Knee Arthroscopy - Meniscal Procedures       │
│    Questions:                                                │
│      Q1: Conservative treatment ≥6 weeks?                    │
│      Q2: Failed PT and NSAIDs?                              │
│      Q3: MRI confirming meniscal tear?                      │
│      Q4: Severe (Grade 3-4) osteoarthritis?                 │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Agent Answers Each Question (Loop)                       │
│                                                              │
│    Q1: "Conservative treatment ≥6 weeks?"                    │
│    ├→ Agent searches patient records                        │
│    ├→ Finds: "14 weeks of conservative management..."       │
│    ├→ Answer: YES                                           │
│    └→ SAVE TO AUDIT TRAIL ✅                                 │
│          INSERT INTO pa_audit_trail VALUES (                 │
│            audit_id: 'PA000001_Q1',                          │
│            request_id: 'PA000001',                           │
│            question_number: 1,                               │
│            question_text: 'Conservative treatment ≥6 weeks?',│
│            answer: 'YES',                                    │
│            evidence: '14 weeks of conservative management...',│
│            evidence_source: 'CLINICAL_NOTE',                 │
│            confidence: 0.95                                  │
│          )                                                   │
│                                                              │
│    Q2: "Failed PT and NSAIDs?"                              │
│    └→ SAVE TO AUDIT TRAIL ✅                                 │
│                                                              │
│    Q3: "MRI confirming meniscal tear?"                      │
│    └→ SAVE TO AUDIT TRAIL ✅                                 │
│                                                              │
│    Q4: "Severe osteoarthritis?"                             │
│    └→ SAVE TO AUDIT TRAIL ✅                                 │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Final Decision Calculated                                 │
│    └→ All YES answers (except Q4) → APPROVED ✅              │
│    └→ Update authorization_requests.decision = 'APPROVED'   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Example Audit Trail Record

### **Request: PA000001 (Knee Arthroscopy)**

```sql
SELECT * FROM pa_audit_trail WHERE request_id = 'PA000001' ORDER BY question_number;
```

| audit_id | request_id | question_number | question_text | answer | evidence | confidence |
|----------|------------|-----------------|---------------|--------|----------|------------|
| PA000001_Q1 | PA000001 | 1 | Has patient completed at least 6 weeks conservative treatment? | YES | Record 1 [CLINICAL_NOTE]: ORTHOPEDIC CONSULTATION NOTE Patient: 58-year-old male Date: 2025-04-03 Chief Complaint: Right knee pain, failed conservative treatment... | 0.95 |
| PA000001_Q2 | PA000001 | 2 | Has patient completed at least 8 PT sessions? | YES | Record 1 [CLINICAL_NOTE]: 11 sessions of physical therapy completed... | 0.90 |
| PA000001_Q3 | PA000001 | 3 | Is MRI confirming meniscal tear present? | YES | Record 2 [IMAGING_REPORT]: MRI Right Knee - Medial meniscus: Complex tear confirmed... | 0.98 |
| PA000001_Q4 | PA000001 | 4 | Is there severe (Grade 3-4) osteoarthritis? | NO | Record 2 [IMAGING_REPORT]: Cartilage: Grade 2 degeneration... | 0.92 |

**Result:** 3/4 criteria met → **APPROVED** ✅

---

## 🔗 Integration with Authorization Requests

The audit trail is tightly integrated with the main `authorization_requests` table:

```
authorization_requests (Primary Table)
├─ request_id (PK)
├─ patient_id
├─ procedure_code
├─ decision (APPROVED/DENIED/MANUAL_REVIEW)
├─ confidence_score
├─ mcg_code
└─ explanation

         ↓ (1:many relationship)

pa_audit_trail (Detail Table)
├─ audit_id (PK)
├─ request_id (FK) → authorization_requests.request_id
├─ question_number
├─ question_text
├─ answer
├─ evidence
└─ confidence
```

### **Queries:**

**Load summary decision:**
```sql
SELECT request_id, decision, confidence_score, mcg_code
FROM authorization_requests
WHERE request_id = 'PA000001';
```

**Load detailed Q&A breakdown:**
```sql
SELECT question_number, question_text, answer, evidence, confidence
FROM pa_audit_trail
WHERE request_id = 'PA000001'
ORDER BY question_number;
```

---

## 🖥️ UI Display

### **Dashboard: Processed Requests Section**

When a PA request is processed, the dashboard shows:

1. **Summary Card** (from `authorization_requests`):
   - Decision badge (✅ APPROVED / ❌ DENIED / ⚠️ MANUAL REVIEW)
   - Confidence percentage
   - MCG code
   - Criteria met (e.g., "3/4 criteria met")

2. **Expandable Q&A Breakdown** (from `pa_audit_trail`):
   - Click to expand detailed question-by-question analysis
   - Shows:
     - Question number and text
     - Answer with color coding (✅ YES / ❌ NO / ⚠️ UNCLEAR)
     - Evidence snippet
     - Confidence score

**Example UI:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ✅ PA000001 | PT00001 | CPT 29881 | APPROVED (75%) | MCG MCG-A-0398 │
│                                                            [▼]  │
├─────────────────────────────────────────────────────────────────┤
│ Decision: APPROVED    Confidence: 75%    MCG Code: MCG-A-0398  │
│ Criteria Met: 3/4                                               │
│                                                                 │
│ 📋 Question & Answer Breakdown                                  │
│                                                                 │
│ Q1: Has patient completed at least 6 weeks conservative treatment? │
│ ✅ Answer: YES (Confidence: 95%)                                │
│ Evidence: Record 1 [CLINICAL_NOTE]: 14 weeks of conservative...│
│ ─────────────────────────────────────────────────────────────  │
│                                                                 │
│ Q2: Has patient completed at least 8 PT sessions?              │
│ ✅ Answer: YES (Confidence: 90%)                                │
│ Evidence: Record 1 [CLINICAL_NOTE]: 11 sessions completed...   │
│ ─────────────────────────────────────────────────────────────  │
│                                                                 │
│ Q3: Is MRI confirming meniscal tear present?                   │
│ ✅ Answer: YES (Confidence: 98%)                                │
│ Evidence: Record 2 [IMAGING_REPORT]: Complex tear confirmed... │
│ ─────────────────────────────────────────────────────────────  │
│                                                                 │
│ Q4: Is there severe (Grade 3-4) osteoarthritis?                │
│ ❌ Answer: NO (Confidence: 92%)                                 │
│ Evidence: Record 2 [IMAGING_REPORT]: Grade 2 degeneration...   │
│                                                                 │
│ [🔄 Reset PA000001 to Pending]                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Demo Reset Functionality

### **Purpose:**
For testing and demo purposes, users can reset PA requests back to "pending" state and clear their audit trail.

### **UI Buttons:**

#### **1. Reset All 10 Demo Requests to Pending**
- Resets `PA000001` through `PA000010` to pending
- Clears decision, confidence, and MCG code
- **Does NOT delete audit trail** (for review purposes)

#### **2. Reset pa_audit_trail Table** ⭐ **NEW**
- Recreates the entire `pa_audit_trail` table
- Clears **all audit trail records** (all requests)
- Uses `CREATE OR REPLACE TABLE` statement
- Runs with service principal credentials

#### **3. Individual Request Reset**
- Click on a processed request to reset just that one
- Clears decision from `authorization_requests`
- **Does NOT delete audit trail** (for review purposes)

### **Implementation:**

**Reset Audit Trail Button:**
```python
if st.button("🗑️ Reset pa_audit_trail Table", key="reset_audit_trail"):
    try:
        # Use cached WorkspaceClient (service principal)
        result = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            catalog=CATALOG,
            schema=SCHEMA,
            statement=f"""
            CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.pa_audit_trail (
              audit_id STRING NOT NULL,
              request_id STRING NOT NULL,
              question_number INT NOT NULL,
              question_text STRING NOT NULL,
              answer STRING NOT NULL,
              evidence STRING,
              evidence_source STRING,
              confidence DOUBLE,
              created_at TIMESTAMP
            )
            USING DELTA
            COMMENT 'Detailed audit trail showing MCG Q&A breakdown'
            """,
            wait_timeout="50s"
        )
        st.success("✅ pa_audit_trail table reset (all audit records cleared)")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Reset failed: {str(e)}")
```

**Key Points:**
- Uses **service principal** credentials (not user credentials)
- Requires `ALL_PRIVILEGES` or `MODIFY` permission on table
- `CREATE OR REPLACE TABLE` is atomic and safe
- Re-grants permissions after table recreation

---

## 🔒 Permissions Required

### **Service Principal Needs:**

1. **On `pa_audit_trail` table:**
   - `SELECT` - Read audit trail records
   - `MODIFY` or `ALL_PRIVILEGES` - Insert new records, recreate table

2. **On schema:**
   - `USE_SCHEMA` - Access schema
   - `MODIFY` - Create/replace tables

3. **On warehouse:**
   - `CAN_USE` - Execute SQL statements

### **Granted via:**
```bash
./grant_permissions.sh dev
```

See [SERVICE_PRINCIPAL_PERMISSIONS.md](SERVICE_PRINCIPAL_PERMISSIONS.md) for details.

---

## 📊 Compliance & Regulatory Benefits

### **CMS HPMS Memo Requirements:**
The audit trail supports compliance with CMS mandates for PA transparency:

✅ **Real-time decision transparency** - Shows exact questions evaluated  
✅ **Evidence-based decisions** - Links answers to specific clinical records  
✅ **Explainability** - Clear reasoning for each answer  
✅ **Auditability** - Complete trail for regulatory review  
✅ **Traceability** - Links to source clinical documents  

### **Use Cases:**

1. **Appeals Process:**
   - Provider appeals denial → Show detailed Q&A breakdown
   - Demonstrate which criteria were not met
   - Show specific evidence reviewed

2. **Quality Assurance:**
   - Review agent accuracy
   - Identify patterns in incorrect answers
   - Improve training data

3. **Regulatory Audits:**
   - CMS audit → Export complete audit trail
   - Show evidence-based decision making
   - Demonstrate compliance with guidelines

4. **Clinical Review:**
   - Medical director reviews flagged cases
   - See agent's reasoning and evidence
   - Override if necessary

---

## 🎯 Best Practices

### **1. Evidence Quality:**
- Store sufficient evidence (not just "yes" or "no")
- Include record type and key snippets
- Keep evidence length reasonable (500-1000 chars)

### **2. Confidence Tracking:**
- Record AI confidence for each answer
- Flag low-confidence answers for manual review
- Aggregate confidence to overall decision confidence

### **3. Audit Trail Retention:**
- Keep audit trail for regulatory period (typically 7-10 years)
- Consider archiving old records to cold storage
- Maintain index on `request_id` for fast lookups

### **4. Testing:**
- Reset audit trail between test runs
- Verify 1 record per question (no duplicates)
- Check evidence links to source records

---

## 🧪 Testing & Validation

### **Verify Audit Trail Creation:**

```sql
-- Check audit trail records for a request
SELECT 
  question_number,
  question_text,
  answer,
  confidence,
  created_at
FROM pa_audit_trail
WHERE request_id = 'PA000001'
ORDER BY question_number;

-- Expected: 4 records (1 per question)
```

### **Verify No Duplicates:**

```sql
-- Check for duplicate questions
SELECT 
  request_id,
  question_number,
  COUNT(*) as count
FROM pa_audit_trail
GROUP BY request_id, question_number
HAVING COUNT(*) > 1;

-- Expected: 0 rows (no duplicates)
```

### **Verify Evidence Quality:**

```sql
-- Check evidence length
SELECT 
  audit_id,
  LENGTH(evidence) as evidence_length
FROM pa_audit_trail
WHERE evidence IS NOT NULL
ORDER BY evidence_length DESC;

-- Expected: 200-1000 characters per record
```

---

## 📈 Performance Considerations

### **Indexing:**
- Primary key on `audit_id` (auto-indexed)
- Consider secondary index on `request_id` for fast lookups
- Delta Lake handles small tables efficiently

### **Query Optimization:**
```sql
-- Fast: Query by request_id (indexed)
SELECT * FROM pa_audit_trail WHERE request_id = 'PA000001';

-- Slow: Full table scan
SELECT * FROM pa_audit_trail WHERE answer = 'YES';
```

### **Storage:**
- ~200-500 bytes per audit record
- For 10,000 PA requests with 5 questions each: ~2.5 MB
- Negligible storage cost

---

## ✅ Implementation Checklist

- [x] Table created with correct schema
- [x] Service principal has ALL_PRIVILEGES
- [x] Agent saves record after each question
- [x] UI displays Q&A breakdown
- [x] Reset functionality works
- [x] No duplicate records created
- [x] Evidence includes source record type
- [x] Confidence scores tracked
- [x] Created timestamp recorded

---

## 🔗 Related Documentation

- [TWO_TABLE_IMPLEMENTATION_COMPLETE.md](TWO_TABLE_IMPLEMENTATION_COMPLETE.md) - Data architecture
- [SERVICE_PRINCIPAL_PERMISSIONS.md](SERVICE_PRINCIPAL_PERMISSIONS.md) - Permissions model
- [PA_QUEUE_WORKFLOW_COMPLETE.md](PA_QUEUE_WORKFLOW_COMPLETE.md) - End-to-end workflow
- [AGENT_ARCHITECTURE_EXPLAINED.md](AGENT_ARCHITECTURE_EXPLAINED.md) - LangGraph agent design

---

*Last Updated: January 1, 2026*

