# Architecture Documentation

This folder contains comprehensive documentation about the Prior Authorization system architecture, data flows, and workflows.

---

## 📚 Documentation Index

### **Core Architecture**
- **[TWO_TABLE_IMPLEMENTATION_COMPLETE.md](TWO_TABLE_IMPLEMENTATION_COMPLETE.md)**
  - Two-table pattern for operational vs search data
  - Full records vs chunks architecture
  - Vector index design
  - Performance benefits

- **[PA_AUDIT_TRAIL_ARCHITECTURE.md](PA_AUDIT_TRAIL_ARCHITECTURE.md)** ⭐ **NEW!**
  - Audit trail table schema and purpose
  - Q&A tracking workflow
  - UI display and demo reset functionality
  - Compliance and regulatory benefits

- **[SERVICE_PRINCIPAL_PERMISSIONS.md](SERVICE_PRINCIPAL_PERMISSIONS.md)** ⭐ **NEW!**
  - Service principal authentication model
  - Required permissions and why
  - Grant permissions workflow
  - Troubleshooting permission issues

### **Data Flows & Integration**
- **[REAL_WORLD_DATA_FLOWS.md](REAL_WORLD_DATA_FLOWS.md)**
  - Complete guide to how data enters the PA system in production
  - Covers 3 main data sources: Clinical Records, PA Requests, Guidelines
  - Includes ASCII diagrams, examples, and code samples
  - Real-world integration methods (FHIR, HL7, EDI, APIs)
  - Medallion architecture (Bronze/Silver/Gold)

### **Workflows**
- **[PA_QUEUE_WORKFLOW_COMPLETE.md](PA_QUEUE_WORKFLOW_COMPLETE.md)**
  - End-to-end PA request processing workflow
  - Queue management
  - Decision tracking

- **[AGENT_ARCHITECTURE_EXPLAINED.md](AGENT_ARCHITECTURE_EXPLAINED.md)**
  - LangGraph agent design
  - Node and edge definitions
  - State management

### **Planning & Design**
- **[DEMO_DATA_PLAN.md](DEMO_DATA_PLAN.md)**
  - Demo data generation strategy
  - Test patient scenarios

- **[TWO_TABLE_REFACTORING_PLAN.md](TWO_TABLE_REFACTORING_PLAN.md)**
  - Original design plan for two-table architecture

---

## 🔍 Quick Reference

### **Want to understand...**

**"Where does patient clinical data come from?"**
→ See [REAL_WORLD_DATA_FLOWS.md](REAL_WORLD_DATA_FLOWS.md#-data-flow-1-patient-clinical-records)

**"How do PA requests arrive?"**
→ See [REAL_WORLD_DATA_FLOWS.md](REAL_WORLD_DATA_FLOWS.md#-data-flow-2-prior-authorization-requests)

**"Where do MCG guidelines come from?"**
→ See [REAL_WORLD_DATA_FLOWS.md](REAL_WORLD_DATA_FLOWS.md#-data-flow-3-clinical-guidelines-mcg-interqual-medicare)

**"What's the complete end-to-end flow?"**
→ See [REAL_WORLD_DATA_FLOWS.md](REAL_WORLD_DATA_FLOWS.md#-complete-end-to-end-flow)

**"How does audit trail tracking work?"**
→ See [PA_AUDIT_TRAIL_ARCHITECTURE.md](PA_AUDIT_TRAIL_ARCHITECTURE.md)

**"What permissions does the app need?"**
→ See [SERVICE_PRINCIPAL_PERMISSIONS.md](SERVICE_PRINCIPAL_PERMISSIONS.md)

**"How do I reset demo data for testing?"**
→ See [PA_AUDIT_TRAIL_ARCHITECTURE.md](PA_AUDIT_TRAIL_ARCHITECTURE.md#-demo-reset-functionality)

---

## 🎯 Key Concepts Explained

### **Data Sources:**
1. **Clinical Records** - Patient medical history from EMRs
2. **PA Requests** - Authorization requests from providers
3. **Guidelines** - MCG/InterQual approval criteria

### **Integration Methods:**
- FHIR API (real-time)
- HL7 V2 Messages (real-time)
- EDI 278 (batch)
- Claims Attachments (batch)
- Provider Portals (manual)
- File Feeds (batch)

### **Architecture:**
```
Raw Data (Bronze) 
  ↓
Cleaned & Structured (Silver)
  ↓
Vector Search Ready (Gold)
  ↓
PA Agent Processing
  ↓
Decision & Audit Trail
```

---

## 📊 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                            │
├──────────────┬──────────────┬───────────────┬──────────────┤
│   CLINICAL   │ PA REQUESTS  │  GUIDELINES   │ AUDIT TRAIL  │
│     DATA     │              │   (MCG/IQ)    │   (Q&A)      │
└──────┬───────┴──────┬───────┴───────┬───────┴──────┬───────┘
       │              │               │              │
       └──────────────┼───────────────┼──────────────┘
                      ↓               ↓
             ┌────────────────────────────────┐
             │   DATABRICKS UNITY CATALOG     │
             │                                │
             │  Tables:                       │
             │  • patient_clinical_records    │
             │  • clinical_guidelines         │
             │  • authorization_requests      │
             │  • pa_audit_trail ⭐           │
             │                                │
             │  Vector Indexes:               │
             │  • clinical_records_chunks_idx │
             │  • guidelines_idx              │
             └────────────┬───────────────────┘
                          ↓
             ┌────────────────────────────┐
             │   LANGGRAPH PA AGENT       │
             │                            │
             │  Nodes:                    │
             │  • load_patient_data       │
             │  • get_guideline           │
             │  • answer_question (loop)  │
             │  • calculate_decision      │
             └────────────┬───────────────┘
                          ↓
             ┌────────────────────────────┐
             │   STREAMLIT DASHBOARD      │
             │                            │
             │  • PA Queue                │
             │  • Batch Processing        │
             │  • Q&A Breakdown Display   │
             │  • Demo Reset Tools ⭐     │
             └────────────────────────────┘
```

---

## 🏗️ Medallion Architecture

### **Bronze Layer (Raw)**
- Raw PDFs, XML, JSON, HL7, EDI files
- Stored in Unity Catalog Volumes
- No schema enforcement
- Append-only

### **Silver Layer (Structured)**
- Delta Tables with CDF enabled
- Schema enforced
- Data validated and cleaned
- Tables:
  - `patient_clinical_records` (full records)
  - `patient_clinical_records_chunks` (search chunks)
  - `clinical_guidelines` (full guidelines)
  - `clinical_guidelines_chunks` (search chunks)
  - `authorization_requests` (PA queue)
  - `pa_audit_trail` (Q&A tracking) ⭐

### **Gold Layer (Optimized)**
- Vector Search Indexes
- Aggregated analytics tables
- Optimized for queries
- ML-ready

---

## 🔄 Real-Time vs. Batch Processing

| Source | Method | Latency | Use Case |
|--------|--------|---------|----------|
| EMR → Clinical Data | FHIR API | Seconds | Urgent PA |
| Provider → PA Request | Portal | Minutes | Standard PA |
| Vendor → Guidelines | File Feed | Hours/Days | Updates |
| Claims → Attachments | EDI 278 | Hours | Bulk PA |

---

## 🔐 Security & Permissions

### **Service Principal Model:**
- App runs as Databricks service principal
- Permissions granted via Unity Catalog
- Principle of least privilege
- See [SERVICE_PRINCIPAL_PERMISSIONS.md](SERVICE_PRINCIPAL_PERMISSIONS.md)

### **Required Permissions:**
- `USE_CATALOG` on catalog
- `USE_SCHEMA`, `SELECT`, `MODIFY` on schema
- `SELECT`, `MODIFY` on tables
- `ALL_PRIVILEGES` on `pa_audit_trail` (for reset)
- `CAN_USE` on SQL warehouse
- `EXECUTE` on UC functions

---

## 🧪 Testing & Demo Reset

### **Demo Reset Tools:**

1. **Reset All 10 Demo Requests to Pending**
   - Clears decisions for PA000001-PA000010
   - Resets to pending state

2. **Reset pa_audit_trail Table** ⭐ **NEW**
   - Recreates audit trail table
   - Clears all Q&A records
   - Uses `CREATE OR REPLACE TABLE`

3. **Individual Request Reset**
   - Reset specific PA request
   - Click on processed request

See [PA_AUDIT_TRAIL_ARCHITECTURE.md](PA_AUDIT_TRAIL_ARCHITECTURE.md#-demo-reset-functionality) for details.

---

## 🎓 Learning Path

**For Beginners:**
1. Start with the Complete End-to-End Flow diagram
2. Follow one PA request from submission to decision
3. Understand the three data sources
4. Review audit trail tracking

**For Developers:**
1. Review integration methods (FHIR, HL7, EDI)
2. Study the Databricks pipeline code examples
3. Understand Delta Sync Vector Indexes
4. Learn service principal permissions model

**For Architects:**
1. Review medallion architecture
2. Study security and compliance sections
3. Compare demo vs. production systems
4. Understand two-table pattern benefits

---

## 📝 Related Documentation

### **Within This Folder:**
- [TWO_TABLE_IMPLEMENTATION_COMPLETE.md](TWO_TABLE_IMPLEMENTATION_COMPLETE.md) - Data architecture
- [PA_AUDIT_TRAIL_ARCHITECTURE.md](PA_AUDIT_TRAIL_ARCHITECTURE.md) - Audit trail design ⭐
- [SERVICE_PRINCIPAL_PERMISSIONS.md](SERVICE_PRINCIPAL_PERMISSIONS.md) - Permissions model ⭐
- [REAL_WORLD_DATA_FLOWS.md](REAL_WORLD_DATA_FLOWS.md) - Data integration
- [PA_QUEUE_WORKFLOW_COMPLETE.md](PA_QUEUE_WORKFLOW_COMPLETE.md) - PA workflow
- [AGENT_ARCHITECTURE_EXPLAINED.md](AGENT_ARCHITECTURE_EXPLAINED.md) - LangGraph agent
- [DEMO_DATA_PLAN.md](DEMO_DATA_PLAN.md) - Test data strategy

### **Project Root:**
- [README.md](../../README.md) - Project overview and setup
- [CMS_MANDATES_STUDY_GUIDE.md](../CMS_MANDATES_STUDY_GUIDE.md) - Regulatory context
- [DEMO_DATA_SETUP.md](../DEMO_DATA_SETUP.md) - Demo test data

---

## 🤝 Contributing

When adding new architecture documentation:
1. Create new `.md` file in this folder
2. Add ASCII diagrams where helpful
3. Include code examples
4. Update this README with links
5. Keep content clear and actionable

---

*Last Updated: January 1, 2026*
