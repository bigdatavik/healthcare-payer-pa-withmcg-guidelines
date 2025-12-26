# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 03: Generate Clinical Guidelines Documents
# MAGIC
# MAGIC Generates realistic synthetic clinical guidelines (MCG, InterQual, Medicare) and writes them to volume as individual documents.
# MAGIC
# MAGIC **Configuration:** Reads from config.yaml via shared.config module
# MAGIC
# MAGIC **Guidelines Generated:**
# MAGIC - MCG Care Guidelines (outpatient procedures)
# MAGIC - InterQual Criteria (inpatient admissions)
# MAGIC - Medicare Local Coverage Determination (LCDs)
# MAGIC
# MAGIC **Output:** Raw guideline documents written to volume (before chunking)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Imports and Setup

# COMMAND ----------

from datetime import datetime, date
import json
import random

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
volume_path = cfg.guidelines_volume_path

print(f"📊 Generating guidelines documents:")
print(f"   Volume path: {volume_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## MCG Care Guidelines

# COMMAND ----------

mcg_guidelines = [
    {
        "guideline_id": "MCG-A-0398",
        "platform": "MCG",
        "category": "OUTPATIENT_PROCEDURE",
        "procedure_code": "29881",
        "diagnosis_code": "M23.205",
        "title": "MCG: Knee Arthroscopy with Meniscectomy",
        "content": """MCG CARE GUIDELINES - KNEE ARTHROSCOPY WITH MENISCECTOMY (CPT 29881)

INDICATION:
Medial or lateral meniscus tear documented by clinical examination and imaging

CLINICAL CRITERIA (ALL must be met):

1. FAILED CONSERVATIVE TREATMENT
   ☐ Minimum 6 weeks of conservative therapy
   ☐ Physical therapy (at least 8 sessions documented)
   ☐ NSAIDs trial (at least 4 weeks)
   ☐ Activity modification attempted
   
2. CLINICAL FINDINGS
   ☐ Positive McMurray test
   ☐ Joint line tenderness
   ☐ Mechanical symptoms (locking, catching, giving way)
   ☐ Effusion present
   
3. IMAGING CONFIRMATION
   ☐ MRI confirming meniscal tear
   ☐ X-ray ruling out severe osteoarthritis (Grade 3-4 not suitable)
   
4. FUNCTIONAL LIMITATION
   ☐ Significant impact on ADLs or work
   ☐ Pain level 5/10 or higher
   
EXCLUSION CRITERIA:
- Severe osteoarthritis (Kellgren-Lawrence Grade 3-4)
- Active infection
- Significant comorbidities contraindicating surgery
- BMI > 40 without weight management attempt

APPROVAL CRITERIA:
✓ ALL clinical criteria met → APPROVED
✗ ANY criterion not met → MANUAL REVIEW or DENIED
""",
        "questionnaire": json.dumps([
            {"question": "Has patient completed at least 6 weeks conservative treatment?", "required": True},
            {"question": "Has patient completed at least 8 PT sessions?", "required": True},
            {"question": "Is MRI confirming meniscal tear present?", "required": True},
            {"question": "Is there severe (Grade 3-4) osteoarthritis?", "required": True, "deny_if": "yes"}
        ])
    },
    {
        "guideline_id": "MCG-A-0285",
        "platform": "MCG",
        "category": "IMAGING",
        "procedure_code": "73721",
        "diagnosis_code": "M25.561",
        "title": "MCG: MRI of Joint (Knee)",
        "content": """MCG CARE GUIDELINES - MRI KNEE (CPT 73721)

INDICATION:
Suspected internal derangement of knee

CLINICAL CRITERIA:

1. ACUTE INJURY (within 6 weeks)
   ☐ Trauma with suspected ligament tear (ACL/PCL/MCL/LCL)
   ☐ Suspected meniscal tear with mechanical symptoms
   ☐ Ottawa knee rules positive
   
   OR

2. CHRONIC SYMPTOMS (> 6 weeks)
   ☐ Failed conservative treatment (min 6 weeks)
   ☐ Persistent mechanical symptoms (locking, catching)
   ☐ Clinical exam suggests internal derangement
   ☐ X-ray performed and reviewed
   
3. PRE-OPERATIVE PLANNING
   ☐ Surgery planned based on clinical findings
   ☐ MRI needed to confirm diagnosis and plan procedure
   
EXCLUSION CRITERIA:
- Mild degenerative symptoms without mechanical findings
- Contraindication to MRI (pacemaker, implants)
- Recent MRI (< 6 months) already available

APPROVAL CRITERIA:
✓ Meets acute injury OR chronic symptoms criteria → APPROVED
✗ Does not meet criteria → DENIED
""",
        "questionnaire": json.dumps([
            {"question": "Is this for acute injury within 6 weeks?", "required": False},
            {"question": "If chronic, has conservative treatment been tried for 6+ weeks?", "required": True},
            {"question": "Are mechanical symptoms present (locking/catching)?", "required": True},
            {"question": "Has X-ray been performed and reviewed?", "required": True}
        ])
    },
    {
        "guideline_id": "MCG-A-0412",
        "platform": "MCG",
        "category": "OUTPATIENT_PROCEDURE",
        "procedure_code": "93015",
        "diagnosis_code": "I25.10",
        "title": "MCG: Cardiovascular Stress Test",
        "content": """MCG CARE GUIDELINES - CARDIOVASCULAR STRESS TEST (CPT 93015)

INDICATION:
Evaluation of known or suspected coronary artery disease

CLINICAL CRITERIA (ONE or more):

1. CHEST PAIN EVALUATION
   ☐ Atypical or typical angina symptoms
   ☐ Risk factors present (diabetes, hypertension, smoking, family history)
   ☐ ECG changes suggestive of ischemia
   
2. CARDIAC RISK ASSESSMENT
   ☐ Pre-operative evaluation for intermediate/high-risk surgery
   ☐ Known CAD with change in symptoms
   ☐ Post-MI risk stratification (after stabilization)
   
3. EXERCISE CAPACITY
   ☐ Heart failure with unclear functional capacity
   ☐ Evaluation of cardiac rehabilitation progress
   
EXCLUSION CRITERIA (DO NOT APPROVE):
- Recent MI (< 2 days)
- Unstable angina
- Severe aortic stenosis
- Acute myocarditis or pericarditis
- Uncontrolled arrhythmias

APPROVAL CRITERIA:
✓ ONE or more indication present AND no exclusion criteria → APPROVED
✗ Does not meet criteria → DENIED
""",
        "questionnaire": json.dumps([
            {"question": "Does patient have chest pain or angina symptoms?", "required": False},
            {"question": "Is this for pre-operative risk assessment?", "required": False},
            {"question": "Recent MI within 2 days?", "required": True, "deny_if": "yes"},
            {"question": "Unstable angina present?", "required": True, "deny_if": "yes"}
        ])
    }
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## InterQual Criteria

# COMMAND ----------

interqual_guidelines = [
    {
        "guideline_id": "IQ-2024-KNEE-01",
        "platform": "InterQual",
        "category": "OUTPATIENT_PROCEDURE",
        "procedure_code": "27447",
        "diagnosis_code": "M17.11",
        "title": "InterQual: Total Knee Arthroplasty",
        "content": """INTERQUAL CRITERIA - TOTAL KNEE ARTHROPLASTY (CPT 27447)

SEVERITY OF ILLNESS (ALL must be present):

1. RADIOGRAPHIC EVIDENCE
   ☐ X-ray showing Grade 3-4 osteoarthritis (Kellgren-Lawrence)
   ☐ Joint space narrowing < 50% of contralateral knee
   ☐ Osteophyte formation present
   
2. PAIN AND FUNCTION
   ☐ Severe pain (7/10 or higher) despite medication
   ☐ Significant functional limitation in ADLs
   ☐ Difficulty with ambulation or stairs
   
3. CONSERVATIVE TREATMENT FAILURE
   ☐ 6+ months conservative treatment documented
   ☐ Physical therapy (minimum 12 sessions)
   ☐ NSAIDs or other analgesics tried
   ☐ Weight loss attempted if BMI > 30
   ☐ Assistive devices used (cane, walker)
   ☐ Intra-articular injection tried (if not contraindicated)

INTENSITY OF SERVICE:
- Requires inpatient or outpatient surgical facility
- Anesthesia required
- Post-operative rehabilitation needed

MEDICAL NECESSITY:
✓ ALL severity criteria met → APPROVED
⚠ Missing 1-2 criteria → MANUAL REVIEW
✗ Missing 3+ criteria → DENIED
""",
        "questionnaire": json.dumps([
            {"question": "X-ray confirms Grade 3-4 OA?", "required": True},
            {"question": "Pain level 7/10 or higher?", "required": True},
            {"question": "Conservative treatment for 6+ months?", "required": True},
            {"question": "Physical therapy completed (12+ sessions)?", "required": True},
            {"question": "NSAIDs trial completed?", "required": True},
            {"question": "If BMI>30, weight loss attempted?", "required": True}
        ])
    },
    # ========================================
    # ADDITIONAL GUIDELINES FOR DEMO PATIENTS
    # ========================================
    {
        "guideline_id": "MCG-A-0542",
        "platform": "MCG",
        "category": "IMAGING",
        "procedure_code": "72148",
        "diagnosis_code": "M54.5",
        "title": "MCG: MRI Lumbar Spine Without Contrast",
        "content": """MCG CARE GUIDELINES - MRI LUMBAR SPINE (CPT 72148)

INDICATION:
Low back pain with radiculopathy or red flag symptoms

CLINICAL CRITERIA:

1. RED FLAGS (Any one present → APPROVE immediately)
   ☐ Progressive motor weakness or neurological deficit
   ☐ Cauda equina symptoms (bowel/bladder dysfunction, saddle anesthesia)
   ☐ Suspected infection or malignancy
   ☐ History of cancer with new back pain
   ☐ Significant trauma
   
   OR

2. RADICULOPATHY WITH CONSERVATIVE TREATMENT FAILURE
   ☐ Dermatomal pain distribution
   ☐ Positive straight leg raise or neurological signs
   ☐ Conservative treatment for 6+ weeks (PT, medications)
   ☐ Persistent or worsening symptoms
   ☐ Surgical evaluation being considered
   
3. PRE-OPERATIVE PLANNING
   ☐ Surgery planned for confirmed diagnosis
   ☐ MRI needed for surgical planning

EXCLUSION CRITERIA:
- Mechanical low back pain without radiculopathy and no red flags
- < 6 weeks conservative treatment (unless red flags present)
- Recent MRI available (< 6 months)

APPROVAL CRITERIA:
✓ Red flags present OR radiculopathy with failed conservative Rx → APPROVED
✗ Mechanical pain only, no red flags, insufficient conservative Rx → DENIED
""",
        "questionnaire": json.dumps([
            {"question": "Are red flags present (progressive weakness, cauda equina, trauma, cancer)?", "required": True},
            {"question": "If no red flags, is radiculopathy present with dermatomal pain?", "required": True},
            {"question": "If no red flags, has conservative treatment been tried for 6+ weeks?", "required": True}
        ])
    },
    {
        "guideline_id": "MCG-A-0789",
        "platform": "MCG",
        "category": "IMAGING",
        "procedure_code": "73221",
        "diagnosis_code": "M75.100",
        "title": "MCG: MRI Shoulder Without Contrast",
        "content": """MCG CARE GUIDELINES - MRI SHOULDER (CPT 73221)

INDICATION:
Suspected rotator cuff tear or internal shoulder derangement

CLINICAL CRITERIA:

1. CLINICAL EXAMINATION
   ☐ Positive impingement signs (Hawkins, Neer)
   ☐ Weakness or pain with ROM testing
   ☐ Failed conservative treatment (6+ weeks)
   ☐ Physical therapy completed (minimum 6 weeks)
   
2. IMAGING CONFIRMATION NEEDED FOR
   ☐ Surgical planning for suspected rotator cuff tear
   ☐ X-ray non-diagnostic or normal
   ☐ Clinical suspicion of labral tear or other pathology
   
3. CONSERVATIVE TREATMENT DOCUMENTED
   ☐ Physical therapy: 6+ weeks (typically 8-12 sessions)
   ☐ NSAIDs trial: 4+ weeks
   ☐ Activity modification
   ☐ Home exercise program

EXCLUSION CRITERIA:
- Insufficient conservative treatment (< 6 weeks)
- Resolved symptoms
- Recent MRI available (< 6 months)

APPROVAL CRITERIA:
✓ 6+ weeks PT + persistent symptoms + surgical consideration → APPROVED
⚠ 4-6 weeks PT (borderline) → MANUAL REVIEW
✗ < 4 weeks PT or resolved symptoms → DENIED
""",
        "questionnaire": json.dumps([
            {"question": "Has patient completed 6+ weeks physical therapy?", "required": True},
            {"question": "Are symptoms persistent despite conservative treatment?", "required": True},
            {"question": "Is surgical evaluation being considered?", "required": True}
        ])
    },
    {
        "guideline_id": "MCG-A-0621",
        "platform": "MCG",
        "category": "OUTPATIENT_PROCEDURE",
        "procedure_code": "29914",
        "diagnosis_code": "M24.051",
        "title": "MCG: Hip Arthroscopy with Labral Repair",
        "content": """MCG CARE GUIDELINES - HIP ARTHROSCOPY (CPT 29914)

INDICATION:
Symptomatic hip labral tear or femoroacetabular impingement (FAI)

CLINICAL CRITERIA (ALL must be met):

1. CLINICAL FINDINGS
   ☐ Mechanical symptoms (clicking, catching, pain with motion)
   ☐ Positive FABER test or anterior impingement test
   ☐ Failed conservative treatment (8+ weeks)
   
2. IMAGING CONFIRMATION
   ☐ MRI arthrogram confirming labral tear (REQUIRED)
   ☐ X-ray to assess for FAI morphology or dysplasia
   ☐ Advanced imaging showing intra-articular pathology
   
3. CONSERVATIVE TREATMENT
   ☐ Physical therapy: 8+ weeks
   ☐ Activity modification
   ☐ NSAIDs trial
   ☐ May include intra-articular injection

EXCLUSION CRITERIA:
- Severe osteoarthritis (Grade 3-4) - better candidate for replacement
- No MRI confirmation of labral tear
- Insufficient conservative treatment

APPROVAL CRITERIA:
✓ MRI confirms labral tear + 8+ weeks conservative Rx → APPROVED
⚠ Clinical suspicion but no MRI confirmation → MANUAL REVIEW (MRI required first)
✗ No imaging confirmation or insufficient conservative Rx → DENIED
""",
        "questionnaire": json.dumps([
            {"question": "Has patient completed 8+ weeks conservative treatment including PT?", "required": True},
            {"question": "Is MRI arthrogram confirmation of labral tear present?", "required": True},
            {"question": "Is severe osteoarthritis (Grade 3-4) present?", "required": True, "deny_if": "yes"}
        ])
    },
    {
        "guideline_id": "MCG-A-0934",
        "platform": "MCG",
        "category": "INPATIENT_PROCEDURE",
        "procedure_code": "22630",
        "diagnosis_code": "M51.26",
        "title": "MCG: Lumbar Spinal Fusion",
        "content": """MCG CARE GUIDELINES - LUMBAR SPINAL FUSION (CPT 22630)

INDICATION:
Spinal instability, spondylolisthesis, or refractory radiculopathy

CLINICAL CRITERIA (ALL must be met):

1. NEUROLOGICAL FINDINGS
   ☐ Radiculopathy with objective neurological deficits (motor weakness, sensory loss, reflex changes)
   ☐ Dermatomal pain distribution
   ☐ Positive nerve tension signs
   
   OR
   
   ☐ Documented spinal instability or spondylolisthesis Grade 2+
   
2. IMAGING CONFIRMATION
   ☐ MRI showing nerve compression at specific level(s)
   ☐ X-ray showing instability, spondylolisthesis, or structural abnormality
   ☐ Correlation between imaging and clinical findings
   
3. CONSERVATIVE TREATMENT FAILURE
   ☐ Comprehensive conservative treatment: 12+ weeks minimum
   ☐ Physical therapy: extensive program (12+ weeks)
   ☐ Epidural steroid injections considered/tried
   ☐ Medications: NSAIDs, neuropathic pain medications
   
4. FUNCTIONAL IMPAIRMENT
   ☐ Significant impact on quality of life and function
   ☐ Unable to work or perform ADLs

EXCLUSION CRITERIA:
- Mechanical low back pain WITHOUT radiculopathy or instability
- No objective neurological findings
- No nerve compression on imaging
- Insufficient conservative treatment
- Psychosocial factors predominant

APPROVAL CRITERIA:
✗ No neurological deficits + no imaging showing nerve compression → DENIED
✗ No/minimal conservative treatment attempted → DENIED
✓ Neurological deficits + imaging confirms compression + 12+ weeks failed Rx → APPROVED
""",
        "questionnaire": json.dumps([
            {"question": "Are objective neurological deficits present (motor weakness, sensory loss, reflex changes)?", "required": True},
            {"question": "Does MRI show nerve compression at the affected level?", "required": True},
            {"question": "Has comprehensive conservative treatment been attempted for 12+ weeks?", "required": True},
            {"question": "Is spinal instability or spondylolisthesis Grade 2+ present?", "required": False}
        ])
    },
    {
        "guideline_id": "MCG-A-1124",
        "platform": "MCG",
        "category": "OUTPATIENT_PROCEDURE",
        "procedure_code": "15830",
        "diagnosis_code": "L90.6",
        "title": "MCG: Panniculectomy (Excision of Excessive Skin)",
        "content": """MCG CARE GUIDELINES - PANNICULECTOMY (CPT 15830)

INDICATION:
Massive weight loss resulting in pannus causing functional impairment or medical complications

CLINICAL CRITERIA (ALL must be met for coverage):

1. FUNCTIONAL IMPAIRMENT (REQUIRED)
   ☐ Pannus interferes with ambulation or mobility
   ☐ Difficulty with personal hygiene due to pannus
   ☐ Pannus causes chronic back, hip, or joint pain documented
   
   AND/OR

2. MEDICAL COMPLICATIONS (REQUIRED)
   ☐ Recurrent intertrigo or skin infections under pannus (3+ episodes in 12 months)
   ☐ Chronic skin ulceration or breakdown
   ☐ Documented rashes requiring medical treatment
   
3. WEIGHT STABILITY (REQUIRED)
   ☐ BMI < 35 OR stable weight for 12+ months post-bariatric surgery
   ☐ No active weight loss program underway
   ☐ Weight management documented
   
4. DOCUMENTATION
   ☐ Photos showing pannus and skin complications
   ☐ Medical records of recurrent infections/rashes
   ☐ Documentation of functional limitations

EXCLUSION CRITERIA (COSMETIC - NOT COVERED):
- Desire for improved appearance WITHOUT functional impairment
- No documented recurrent infections or medical complications
- No interference with mobility or hygiene
- Stretch marks alone (striae distensae) without pannus
- Post-pregnancy skin laxity without functional impairment

APPROVAL CRITERIA:
✗ Purely cosmetic (no functional impairment, no medical complications) → DENIED (NOT MEDICALLY NECESSARY)
⚠ Borderline functional impairment, limited documentation → MANUAL REVIEW
✓ Clear functional impairment + recurrent infections + documentation → APPROVED
""",
        "questionnaire": json.dumps([
            {"question": "Does pannus cause functional impairment (mobility, hygiene, chronic pain)?", "required": True},
            {"question": "Are recurrent skin infections documented (3+ episodes in 12 months)?", "required": True},
            {"question": "Is weight stable for 12+ months with BMI < 35?", "required": True},
            {"question": "Is this request purely for cosmetic reasons without functional impairment?", "required": True, "deny_if": "yes"}
        ])
    }
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Medicare LCDs

# COMMAND ----------

medicare_guidelines = [
    {
        "guideline_id": "LCD-L33822",
        "platform": "Medicare",
        "category": "DME",
        "procedure_code": "E0601",
        "diagnosis_code": "M15.0",
        "title": "Medicare LCD: Continuous Passive Motion (CPM) Device",
        "content": """MEDICARE LOCAL COVERAGE DETERMINATION - CPM DEVICE (E0601)

COVERAGE INDICATIONS:

1. POST-OPERATIVE USE ONLY
   ☐ Following total knee replacement (TKR)
   ☐ Within 7 days of surgery
   ☐ Prescribed by treating surgeon
   
2. MEDICAL NECESSITY
   ☐ Patient unable to perform active ROM exercises
   ☐ Risk of adhesion formation or stiffness
   ☐ Documentation of baseline ROM measurements
   
3. DURATION
   ☐ Initial authorization: 21 days post-op
   ☐ Extension requires: Progress notes showing benefit
   ☐ Maximum duration: 6 weeks from surgery

COVERAGE LIMITATIONS:
- NOT covered for routine post-op rehabilitation if patient can do active ROM
- NOT covered for chronic conditions or arthritis management
- NOT covered for other joints (hip, shoulder, elbow) without specific LCD

DOCUMENTATION REQUIREMENTS:
1. Operative note from TKR surgery
2. Prescription from surgeon specifying duration
3. Initial ROM measurements
4. Weekly progress notes if extending beyond 21 days

APPROVAL CRITERIA:
✓ Post-TKR within 7 days + unable to do active ROM → APPROVED (21 days)
⚠ Extension request → Requires progress notes
✗ Other indications → DENIED (not covered)
""",
        "questionnaire": json.dumps([
            {"question": "Is this post-TKR surgery?", "required": True},
            {"question": "Surgery within last 7 days?", "required": True},
            {"question": "Patient unable to perform active ROM?", "required": True},
            {"question": "Prescribed by treating surgeon?", "required": True}
        ])
    }
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Combine All Guidelines

# COMMAND ----------

all_guidelines = mcg_guidelines + interqual_guidelines + medicare_guidelines

print(f"✅ Created {len(all_guidelines)} guideline documents")
print(f"   MCG: {len(mcg_guidelines)}")
print(f"   InterQual: {len(interqual_guidelines)}")
print(f"   Medicare: {len(medicare_guidelines)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write Documents to Volume

# COMMAND ----------

# Write each guideline as a text file
for guideline in all_guidelines:
    file_name = f"{guideline['guideline_id']}.txt"
    file_path = f"{volume_path}/{file_name}"
    
    # Format document with metadata
    full_content = f"""Guideline ID: {guideline['guideline_id']}
Platform: {guideline['platform']}
Category: {guideline['category']}
Procedure Code: {guideline['procedure_code']}
Diagnosis Code: {guideline['diagnosis_code']}
Title: {guideline['title']}
Effective Date: {date.today().isoformat()}

{guideline['content']}

QUESTIONNAIRE:
{guideline['questionnaire']}
"""
    
    # Write to volume
    dbutils.fs.put(file_path, full_content, overwrite=True)
    print(f"✅ Written: {file_name}")

print(f"\n✅ All {len(all_guidelines)} guidelines written to volume")
print(f"   Volume: {volume_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("CLINICAL GUIDELINES DOCUMENTS CREATED!")
print("=" * 80)
print(f"✅ Volume: {volume_path}")
print(f"✅ Total Guidelines: {len(all_guidelines)}")
print(f"   - MCG: {len(mcg_guidelines)}")
print(f"   - InterQual: {len(interqual_guidelines)}")
print(f"   - Medicare: {len(medicare_guidelines)}")
print("=" * 80)
print("\n📝 Next step: Run 03a_chunk_guidelines.py to chunk and create table with CDF")
print("=" * 80)

