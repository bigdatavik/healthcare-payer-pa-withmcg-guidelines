# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 02: Generate Clinical Documents
# MAGIC
# MAGIC Generates realistic synthetic patient clinical records and writes them to volume as individual documents.
# MAGIC
# MAGIC **Configuration:** Reads from config.yaml via shared.config module
# MAGIC
# MAGIC **Documents Generated:**
# MAGIC - Clinical notes from office visits
# MAGIC - Lab results (A1C, lipid panels, metabolic panels)
# MAGIC - Imaging reports (X-rays, MRIs, CT scans)
# MAGIC - Physical therapy notes
# MAGIC - Medication histories
# MAGIC
# MAGIC **Output:** Raw documents written to volume (before chunking)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Imports and Setup

# COMMAND ----------

from faker import Faker
from datetime import datetime, timedelta
import random
import json

fake = Faker()
Faker.seed(42)
random.seed(42)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Configuration

# COMMAND ----------

import sys
import os
sys.path.append(os.path.abspath('..'))
from shared.config import get_config, print_config

cfg = get_config()
print_config(cfg)

# COMMAND ----------

# Use config values
NUM_PATIENTS = cfg.num_patients
volume_path = cfg.clinical_volume_path

print(f"📊 Generating clinical documents:")
print(f"   Volume path: {volume_path}")
print(f"   Number of patients: {NUM_PATIENTS}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Patient IDs

# COMMAND ----------

patient_ids = [f"PT{str(i+1).zfill(5)}" for i in range(NUM_PATIENTS)]

print(f"Generated {len(patient_ids)} patient IDs")
print(f"Sample: {patient_ids[:5]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Clinical Note Templates

# COMMAND ----------

CLINICAL_NOTE_TEMPLATES = [
    """SUBJECTIVE:
Patient is a {age}-year-old {gender} presenting with {chief_complaint}.
Pain level: {pain_level}/10
Duration: {duration}
Previous treatment: {previous_treatment}

OBJECTIVE:
Vital Signs: BP {bp}, HR {hr}, Temp {temp}F
Examination: {examination_findings}

ASSESSMENT:
{diagnosis}

PLAN:
{treatment_plan}
Follow-up in {followup_weeks} weeks.
""",
    """Chief Complaint: {chief_complaint}

HPI: Patient reports {symptom_description} for the past {duration}. {pain_description}. No relief with {failed_treatment}.

Physical Exam:
- General: {general_appearance}
- {body_system}: {examination_findings}

Impression: {diagnosis}

Plan:
1. {treatment_1}
2. {treatment_2}
3. Follow-up: {followup_weeks} weeks
4. {additional_orders}
""",
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Clinical Documents

# COMMAND ----------

all_documents = []

for patient_id in patient_ids:
    patient_age = random.randint(35, 85)
    patient_gender = random.choice(["male", "female"])
    
    # Assign a primary condition
    primary_condition = random.choice([
        "knee_osteoarthritis",
        "diabetes",
        "cardiac",
        "back_pain",
        "general"
    ])
    
    # Generate 5-15 records per patient
    num_records = random.randint(5, 15)
    
    for i in range(num_records):
        days_ago = random.randint(1, 730)
        record_date = datetime.now() - timedelta(days=days_ago)
        
        record_type = random.choice(["CLINICAL_NOTE", "CLINICAL_NOTE", "LAB_RESULT", "IMAGING_REPORT", "PT_NOTE"])
        
        if record_type == "CLINICAL_NOTE" and primary_condition == "knee_osteoarthritis":
            content = CLINICAL_NOTE_TEMPLATES[0].format(
                age=patient_age,
                gender=patient_gender,
                chief_complaint="right knee pain",
                pain_level=random.randint(5, 8),
                duration=f"{random.randint(4, 24)} months",
                previous_treatment=random.choice([
                    "NSAIDs, ice, rest",
                    "physical therapy (12 weeks completed)",
                    "cortisone injection 6 months ago",
                    "home exercises, weight loss"
                ]),
                bp=f"{random.randint(110,140)}/{random.randint(70,90)}",
                hr=random.randint(60, 90),
                temp=round(random.uniform(97.5, 98.8), 1),
                examination_findings=random.choice([
                    "tenderness along medial joint line, crepitus with range of motion, limited flexion to 110 degrees",
                    "joint line tenderness, positive McMurray test, effusion present",
                    "decreased ROM, pain with weight bearing, antalgic gait"
                ]),
                diagnosis="Right knee osteoarthritis, moderate severity",
                treatment_plan=random.choice([
                    "Continue PT, consider viscosupplementation if no improvement",
                    "NSAIDs, activity modification, MRI ordered to assess cartilage",
                    "Home exercise program, weight loss counseling, follow-up 6 weeks"
                ]),
                followup_weeks=random.choice([4, 6, 8, 12])
            )
        else:
            content = f"Clinical documentation for patient {patient_id}. Record type: {record_type}. Date: {record_date.strftime('%Y-%m-%d')}. Condition: {primary_condition}."
        
        doc_id = f"{patient_id}_{record_type}_{record_date.strftime('%Y%m%d')}_{i}"
        
        all_documents.append({
            'doc_id': doc_id,
            'patient_id': patient_id,
            'record_type': record_type,
            'record_date': record_date.strftime('%Y-%m-%d'),
            'condition': primary_condition,
            'content': content
        })

print(f"✅ Generated {len(all_documents)} clinical documents")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write Documents to Volume

# COMMAND ----------

# Write each document as a text file
for doc in all_documents:
    file_name = f"{doc['doc_id']}.txt"
    file_path = f"{volume_path}/{file_name}"
    
    # Format document with metadata
    full_content = f"""Document ID: {doc['doc_id']}
Patient ID: {doc['patient_id']}
Record Type: {doc['record_type']}
Record Date: {doc['record_date']}
Condition: {doc['condition']}

{doc['content']}
"""
    
    # Write to volume
    dbutils.fs.put(file_path, full_content, overwrite=True)

print(f"\n✅ All {len(all_documents)} documents written to volume")
print(f"   Volume: {volume_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("CLINICAL DOCUMENTS CREATED!")
print("=" * 80)
print(f"✅ Volume: {volume_path}")
print(f"✅ Documents: {len(all_documents)}")
print(f"✅ Patients: {len(patient_ids)}")
print("=" * 80)
print("\n📝 Next step: Run 02a_chunk_clinical_records.py to chunk and create table with CDF")
print("=" * 80)

