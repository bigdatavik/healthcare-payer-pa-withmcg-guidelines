# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 02: Generate Clinical Documents - Demo Quality
# MAGIC
# MAGIC Creates 10 high-quality demo patients with temporal clinical stories.
# MAGIC Each patient has a clear progression from initial visit → treatment → imaging → final consult.
# MAGIC
# MAGIC **Output:** Raw documents written to volume (before chunking)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Imports and Setup

# COMMAND ----------

from datetime import datetime, timedelta
import random
import json

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

volume_path = cfg.clinical_volume_path

print(f"📊 Generating demo clinical documents:")
print(f"   Volume path: {volume_path}")
print(f"   Number of demo patients: 10")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Clean Volume (Remove Old Documents)

# COMMAND ----------

print("🧹 Cleaning old documents from volume...")
try:
    dbutils.fs.rm(volume_path, recurse=True)
    print(f"✅ Cleaned volume: {volume_path}")
except Exception as e:
    print(f"ℹ️  Volume was already clean or doesn't exist: {e}")

# Recreate volume directory
try:
    dbutils.fs.mkdirs(volume_path)
    print(f"✅ Volume ready: {volume_path}")
except:
    pass

# COMMAND ----------

# MAGIC %md
# MAGIC ## Demo Patient Definitions

# COMMAND ----------

# Base date for temporal records (12 months ago)
BASE_DATE = datetime.now() - timedelta(days=365)

DEMO_PATIENTS = {
    # ========================================
    # APPROVED CASES (4 patients)
    # ========================================
    "PT00001": {
        "age": 58,
        "gender": "male",
        "condition": "knee_meniscus_tear",
        "records": [
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 0,
                "content": """SUBJECTIVE:
Patient is a 58-year-old male presenting with right knee pain and stiffness.
Pain level: 7/10
Duration: 6 months, progressively worsening
Previous treatment: Over-the-counter NSAIDs, activity modification

OBJECTIVE:
Vital Signs: BP 130/82, HR 72, Temp 98.6F
Examination: Medial joint line tenderness, crepitus with range of motion
Range of Motion: Limited flexion to 110 degrees, positive McMurray test

ASSESSMENT:
Right knee medial meniscus tear suspected
Degenerative joint disease

PLAN:
1. Prescribe ibuprofen 600mg TID
2. Refer to physical therapy - 12 sessions
3. Activity modification, ice/heat therapy
4. Follow-up in 8 weeks
Conservative treatment initiated."""
            },
            {
                "type": "PT_NOTE",
                "weeks_offset": 4,
                "content": """PHYSICAL THERAPY PROGRESS NOTE
Date: {date}
Patient: PT00001
Session: 4 of 12

DIAGNOSIS: Right knee osteoarthritis, medial meniscus tear

TREATMENT DURATION: 4 weeks
SESSIONS COMPLETED: 4 sessions (1x/week protocol)

SUBJECTIVE:
Patient reports persistent right knee pain rated 7/10. Pain worse with stairs, prolonged standing, and squatting. Reports mechanical symptoms including clicking and occasional giving way. Conservative treatment including PT, NSAIDs, activity modification has provided minimal relief.

OBJECTIVE:
- Quadriceps strength: 4/5
- Range of Motion: 0-110 degrees (limited by pain)
- Gait: Antalgic gait pattern noted

ASSESSMENT:
Limited progress after 4 weeks of physical therapy. Patient continues to have significant functional limitations.

PLAN:
Continue PT program, strengthening and ROM exercises. Recommend 8 more sessions to meet 6-week minimum conservative treatment requirement."""
            },
            {
                "type": "PT_NOTE",
                "weeks_offset": 8,
                "content": """PHYSICAL THERAPY PROGRESS NOTE
Date: {date}
Patient: PT00001
Session: 8 of 12

DIAGNOSIS: Right knee osteoarthritis, medial meniscus tear

TREATMENT DURATION: 8 weeks
SESSIONS COMPLETED: 8 sessions (1x/week protocol)

SUBJECTIVE:
Patient reports ongoing right knee pain 6-7/10. Minimal improvement from physical therapy. Still has mechanical symptoms. NSAIDs provide temporary relief only.

OBJECTIVE:
- Quadriceps strength: Improved to 4+/5
- Range of Motion: 0-115 degrees (slight improvement)
- Functional tests: Pain with single leg squat, step-down test positive

ASSESSMENT:
Completed 8 weeks of structured physical therapy with minimal functional improvement. Patient has failed conservative management including 8 weeks of PT and NSAIDs.

PLAN:
Complete remaining 4 sessions. Recommend orthopedic consultation for surgical evaluation if no significant improvement."""
            },
            {
                "type": "IMAGING_REPORT",
                "weeks_offset": 10,
                "content": """RADIOLOGY REPORT - MRI RIGHT KNEE

Patient: PT00001
Date: {date}
Exam: MRI Right Knee without contrast

CLINICAL INDICATION: Right knee pain, suspected meniscal tear, failed conservative treatment

TECHNIQUE: MRI of the right knee was performed without intravenous contrast.

FINDINGS:

MENISCI:
- MEDIAL MENISCUS: Complex tear of the posterior horn of the medial meniscus confirmed. Horizontal and oblique tear components present.
- LATERAL MENISCUS: Intact, no tear identified

CARTILAGE:
- Grade 2 chondromalacia of the medial femoral condyle
- Mild cartilage thinning, no full-thickness defects
- NOT Grade 3 or Grade 4 osteoarthritis

LIGAMENTS:
- ACL, PCL, MCL, LCL: All intact

BONE:
- No bone marrow edema
- No stress fractures
- Mild osteophyte formation medially

IMPRESSION:
1. Complex tear of posterior horn medial meniscus - CONFIRMED
2. Grade 2 chondromalacia (mild-moderate degenerative changes, NOT severe osteoarthritis)
3. Intact ligamentous structures
4. Findings consistent with symptomatic meniscal pathology requiring arthroscopic evaluation"""
            },
            {
                "type": "PT_NOTE",
                "weeks_offset": 12,
                "content": """PHYSICAL THERAPY DISCHARGE NOTE
Date: {date}
Patient: PT00001
Session: 12 of 12 (FINAL)

DIAGNOSIS: Right knee osteoarthritis, medial meniscus tear (MRI confirmed)

TREATMENT DURATION: 12 weeks
SESSIONS COMPLETED: 12 sessions (2x/week protocol)
CONSERVATIVE TREATMENT DURATION: 12 weeks total including NSAIDs, activity modification, ice/heat therapy

SUBJECTIVE:
Patient completed full 12-week physical therapy program. Reports persistent pain 6/10, mechanical symptoms (clicking, giving way) continue. Unable to return to desired activity level.

OBJECTIVE:
- Quadriceps strength: 4+/5 (improved but limited by pain)
- Range of Motion: 0-120 degrees
- Functional limitations: Unable to squat, difficulty with stairs, cannot kneel

ASSESSMENT:
Patient has FAILED conservative management despite 12 weeks of structured physical therapy, NSAIDs, and activity modification. MRI confirms complex medial meniscus tear. Conservative treatment has been exhausted.

RECOMMENDATION:
Discharge from physical therapy. Recommend SURGICAL EVALUATION for arthroscopic meniscectomy given failed conservative treatment and confirmed meniscal pathology."""
            },
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 14,
                "content": """ORTHOPEDIC CONSULTATION NOTE

Patient: 58-year-old male
Date: {date}
Chief Complaint: Right knee pain, failed conservative treatment

HPI:
Patient presents for surgical consultation. Has 6-month history of right knee pain with mechanical symptoms. Has completed 14 weeks of conservative management including:
- 12 weeks (12 sessions) of structured physical therapy
- NSAIDs (ibuprofen 600mg TID) for 14 weeks
- Activity modification, ice/heat therapy
- Minimal improvement, continued functional limitations

IMAGING:
MRI (10 weeks ago): Complex tear posterior horn medial meniscus CONFIRMED. Grade 2 chondromalacia (NOT severe osteoarthritis).

PHYSICAL EXAM:
- McMurray test: Positive for medial meniscus pathology
- Joint line tenderness: Present medially
- Range of motion: 0-120 degrees, pain with terminal flexion
- No severe osteoarthritis, no bone-on-bone, no Grade 3-4 OA

ASSESSMENT:
1. Right knee medial meniscus tear - MRI confirmed
2. Failed conservative management (14 weeks total)
3. Failed physical therapy (12 sessions completed)
4. NOT a candidate for continued non-operative treatment

PLAN:
RECOMMEND: Arthroscopic right knee meniscectomy (CPT 29881)
Meets MCG criteria:
✓ Conservative treatment ≥6 weeks (completed 14 weeks)
✓ Physical therapy completed (12 sessions)
✓ MRI confirmation of meniscal tear
✓ NO severe osteoarthritis (Grade 2 only, not Grade 3-4)

Prior authorization to be submitted."""
            }
        ]
    },
    
    "PT00016": {
        "age": 68,
        "gender": "female",
        "condition": "knee_severe_oa",
        "records": [
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 0,
                "content": """SUBJECTIVE:
Patient is a 68-year-old female presenting with severe bilateral knee pain, worse on the right.
Pain level: 8/10 at rest, 10/10 with activity
Duration: Progressive over 10 years, now significantly limiting function
Unable to walk more than 1 block, difficulty with stairs, cannot stand from chair without assistance

OBJECTIVE:
Vital Signs: BP 142/88, HR 68, Temp 98.4F
Examination: 
- Severe crepitus bilateral knees, worse right
- Bony enlargement, varus deformity right knee
- Range of Motion: Right knee 5-90 degrees (severely limited)
- Antalgic gait, uses cane

ASSESSMENT:
Severe osteoarthritis right knee
End-stage degenerative joint disease
Functional impairment

PLAN:
1. X-ray right knee
2. Trial of structured physical therapy
3. NSAIDs, consider intra-articular injection
4. Follow-up 4 weeks"""
            },
            {
                "type": "IMAGING_REPORT",
                "weeks_offset": 4,
                "content": """RADIOLOGY REPORT - X-RAY RIGHT KNEE

Patient: PT00016
Date: {date}
Exam: AP, Lateral, Sunrise views right knee

CLINICAL INDICATION: Severe knee pain, osteoarthritis

FINDINGS:

JOINT SPACE:
- COMPLETE LOSS of medial joint space - BONE-ON-BONE contact
- Lateral compartment: Severe narrowing

OSTEOARTHRITIS:
- GRADE 4 OSTEOARTHRITIS (Kellgren-Lawrence Grade 4)
- Severe changes throughout
- BONE-ON-BONE medial compartment

BONE:
- Large osteophytes medial and lateral femoral condyles
- Subchondral sclerosis
- Subchondral cyst formation present

ALIGNMENT:
- Varus malalignment 8 degrees

IMPRESSION:
1. SEVERE Grade 4 osteoarthritis right knee - END STAGE
2. Complete loss of medial joint space - BONE-ON-BONE
3. Varus deformity
4. Advanced degenerative changes
5. Findings consistent with need for total knee arthroplasty

RECOMMENDATION: Orthopedic consultation for total knee replacement evaluation"""
            },
            {
                "type": "PT_NOTE",
                "weeks_offset": 10,
                "content": """PHYSICAL THERAPY PROGRESS NOTE
Date: {date}
Patient: PT00016
Sessions: 6 of 8 completed

DIAGNOSIS: Severe osteoarthritis right knee, Grade 4, bone-on-bone

TREATMENT DURATION: 6 weeks
SESSIONS COMPLETED: 6 sessions

SUBJECTIVE:
Patient reports severe right knee pain 8-9/10. No relief from physical therapy. Pain limits all exercises. Cannot tolerate strengthening exercises due to pain.

OBJECTIVE:
- Significant pain with all ROM exercises
- Unable to perform resistance exercises
- Ambulation: Maximum 50 feet with cane before severe pain
- No improvement in function

ASSESSMENT:
Minimal to no benefit from physical therapy due to severity of underlying osteoarthritis. Grade 4 bone-on-bone disease limits rehabilitation potential.

PLAN:
Will complete 8 weeks of conservative management per insurance requirements, but patient is not a candidate for conservative treatment given severity of disease."""
            },
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 18,
                "content": """ORTHOPEDIC CONSULTATION NOTE - SURGICAL EVALUATION

Patient: 68-year-old female
Date: {date}
Chief Complaint: Severe right knee pain, failed conservative treatment

HPI:
Patient with end-stage osteoarthritis right knee. Has completed 12 weeks of conservative management:
- 8 weeks physical therapy (no improvement, limited by pain)
- NSAIDs maximum dose - inadequate relief
- Intra-articular corticosteroid injection - temporary relief only (3 weeks)
- Activity modification, weight loss attempts

IMAGING:
X-ray: Grade 4 osteoarthritis, complete loss of medial joint space, BONE-ON-BONE contact confirmed

PHYSICAL EXAM:
- Severe crepitus, bony deformity
- ROM: 5-90 degrees (severely limited)
- Varus deformity 8 degrees
- Significant functional impairment - cannot walk >1 block, cannot climb stairs

ASSESSMENT:
1. End-stage osteoarthritis right knee - Grade 4, bone-on-bone
2. Failed ALL conservative measures over 12 weeks
3. Severe functional impairment, quality of life significantly affected
4. Excellent candidate for total knee arthroplasty

PLAN:
RECOMMEND: Total right knee arthroplasty (TKA) - CPT 27447
Clear indication for surgery:
✓ Grade 4 osteoarthritis with bone-on-bone
✓ Failed 12 weeks conservative management
✓ Failed physical therapy
✓ Severe functional limitation
✓ No contraindications to surgery

Prior authorization to be submitted."""
            }
        ]
    },
    
    "PT00025": {
        "age": 62,
        "gender": "male",
        "condition": "cardiac",
        "records": [
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 0,
                "content": """SUBJECTIVE:
Patient is a 62-year-old male presenting with chest discomfort on exertion.
Symptoms: Pressure-like chest discomfort with moderate activity (walking uphill, climbing 2 flights stairs)
Duration: 3 months, increasing frequency
Relieved by rest after 5-10 minutes
No chest pain at rest

RISK FACTORS:
- Hypertension (controlled on medication)
- Hyperlipidemia
- Former smoker (quit 5 years ago, 30 pack-year history)
- Family history: Father MI at age 58
- Type 2 diabetes mellitus

OBJECTIVE:
Vital Signs: BP 138/86, HR 78, Temp 98.6F
General: No acute distress at rest
Cardiovascular: Regular rate and rhythm, no murmurs
Lungs: Clear bilaterally

ASSESSMENT:
Exertional chest discomfort, concerning for coronary artery disease
Multiple cardiac risk factors
Atypical angina

PLAN:
1. ECG today
2. Lipid panel, troponin
3. Stress test if ECG abnormal or high risk
4. Continue current medications
5. Cardiology referral"""
            },
            {
                "type": "LAB_RESULT",
                "weeks_offset": 1,
                "content": """LABORATORY RESULTS

Patient: PT00025
Date: {date}

CARDIAC BIOMARKERS:
- Troponin I: <0.01 ng/mL (Normal <0.04) - NEGATIVE
- CK-MB: 2.1 ng/mL (Normal <5.0) - NEGATIVE
- BNP: 45 pg/mL (Normal <100) - NEGATIVE

LIPID PANEL:
- Total Cholesterol: 242 mg/dL (Elevated)
- LDL: 165 mg/dL (High)
- HDL: 38 mg/dL (Low)
- Triglycerides: 195 mg/dL (Elevated)

METABOLIC PANEL:
- Glucose: 142 mg/dL (Elevated - known diabetes)
- Creatinine: 1.1 mg/dL (Normal)
- eGFR: >60 (Normal)

IMPRESSION:
- No acute coronary syndrome (troponin negative)
- Dyslipidemia present
- Multiple cardiac risk factors
- Proceed with stress testing for further evaluation"""
            },
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 2,
                "content": """FOLLOW-UP VISIT - ECG RESULTS

Patient: PT00025
Date: {date}

ECG FINDINGS:
- Sinus rhythm, rate 72 bpm
- Non-specific ST segment changes in leads V4-V6
- No acute ST elevation or depression
- Old Q waves inferior leads (possible prior silent MI)

ASSESSMENT:
1. Exertional chest discomfort with multiple cardiac risk factors
2. ECG shows non-specific ST changes and possible prior inferior MI
3. High pre-test probability for coronary artery disease given:
   - Typical exertional symptoms
   - Multiple risk factors (HTN, DM, dyslipidemia, smoking history, family history)
   - Abnormal ECG findings
   - Age and gender

PLAN:
RECOMMEND: Exercise stress test (CPT 93015) for coronary artery disease evaluation
Indication: Intermediate-high risk patient with exertional chest discomfort and abnormal baseline ECG

Prior authorization to be submitted.
If positive stress test, will proceed to cardiac catheterization."""
            },
            {
                "type": "IMAGING_REPORT",
                "weeks_offset": 3,
                "content": """RADIOLOGY REPORT - CHEST X-RAY

Patient: PT00025
Date: {date}
Exam: Chest X-ray, 2 views

CLINICAL INDICATION: Chest discomfort, cardiac evaluation

FINDINGS:

HEART:
- Cardiomegaly present (cardiothoracic ratio 0.55, upper limit of normal)
- Left ventricular prominence

LUNGS:
- Clear bilateral lung fields
- No infiltrates or effusions

MEDIASTINUM:
- Mild aortic tortuosity (age-related)
- No widening

IMPRESSION:
1. Cardiomegaly - suggests chronic cardiac condition
2. No acute pulmonary findings
3. Findings support need for cardiac stress testing evaluation"""
            }
        ]
    },
    
    "PT00003": {
        "age": 45,
        "gender": "female",
        "condition": "lumbar_radiculopathy",
        "records": [
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 0,
                "content": """SUBJECTIVE:
Patient is a 45-year-old female presenting with severe low back pain radiating to left leg.
Pain level: 8/10
Duration: 8 weeks, progressively worsening
Radiation: Pain radiates down posterior left leg to foot (L5 distribution)
Numbness in left lateral calf and dorsum of foot

OBJECTIVE:
Neurological Exam:
- Motor: Left ankle dorsiflexion 4/5 (weakness), plantarflexion 5/5
- Sensory: Decreased sensation L5 distribution left
- Reflexes: Left ankle reflex diminished
- Straight leg raise: Positive at 30 degrees left (reproduces leg pain)

ASSESSMENT:
Lumbar radiculopathy, likely L5 nerve root
Clinical signs of nerve compression
Progressive neurological symptoms

PLAN:
1. NSAIDs, muscle relaxants
2. Physical therapy referral - 6 weeks
3. If no improvement or worsening neuro symptoms, will need MRI
4. Follow-up 6 weeks"""
            },
            {
                "type": "PT_NOTE",
                "weeks_offset": 6,
                "content": """PHYSICAL THERAPY NOTE
Date: {date}
Patient: PT00003
Duration: 6 weeks completed

DIAGNOSIS: Lumbar radiculopathy, L5 nerve root

TREATMENT COMPLETED:
- 6 weeks of structured physical therapy
- McKenzie protocol, core strengthening
- Neural mobilization exercises

SUBJECTIVE:
Patient reports NO IMPROVEMENT in leg pain or numbness. Now reporting increased weakness - difficulty with foot dorsiflexion, occasional foot drop when walking.

OBJECTIVE:
- Straight leg raise still positive at 30 degrees
- Ankle dorsiflexion: Decreased to 3+/5 (WORSENING)
- Foot drop noted with ambulation
- Sensory deficit unchanged

ASSESSMENT:
FAILED 6 weeks of conservative management. Progressive neurological deficit developing (worsening motor weakness, foot drop). This is a RED FLAG indicating progressive nerve compression.

RECOMMENDATION:
Immediate return to physician. URGENT MRI needed to evaluate for surgical nerve decompression. Progressive motor weakness is indication for urgent evaluation."""
            },
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 8,
                "content": """URGENT NEUROSURGICAL REFERRAL

Patient: 45-year-old female
Date: {date}
Chief Complaint: Progressive foot drop, failed conservative treatment

HPI:
Patient with 8-week history of low back pain with left L5 radiculopathy. Has completed 6 weeks of conservative management including physical therapy and medications. NOW DEVELOPING PROGRESSIVE NEUROLOGICAL DEFICITS:
- Foot drop developing over past 2 weeks
- Ankle dorsiflexion strength deteriorated from 4/5 to 3+/5
- Unable to walk on heels
- Tripping when walking
- Numbness spreading in left foot

PHYSICAL EXAM:
- Motor: Left ankle dorsiflexion 3/5 (SIGNIFICANT WEAKNESS)
- Motor: Left EHL 3/5 (toe extension weak)
- Obvious foot drop when walking
- Positive straight leg raise
- Diminished ankle reflex

ASSESSMENT:
1. Lumbar radiculopathy L5 with PROGRESSIVE motor deficit
2. Foot drop - neurological emergency
3. Failed 6-8 weeks conservative treatment
4. RED FLAGS: Progressive motor weakness despite treatment

PLAN:
URGENT MRI lumbar spine (CPT 72148) to evaluate for:
- Disc herniation with nerve compression
- Spinal stenosis
- Other causes of progressive neurological deficit

This is URGENT/EXPEDITED request given progressive motor weakness and foot drop.
Patient may require urgent surgical decompression if significant nerve compression identified.

Prior authorization requested - URGENT."""
            }
        ]
    },

    # ========================================
    # MANUAL_REVIEW CASES (3 patients)
    # ========================================
    "PT00005": {
        "age": 52,
        "gender": "male",
        "condition": "shoulder_pain",
        "records": [
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 0,
                "content": """SUBJECTIVE:
Patient is a 52-year-old male presenting with right shoulder pain.
Pain level: 6/10
Duration: 3 months
Decreased range of motion, difficulty with overhead activities

OBJECTIVE:
Examination: Positive Hawkins test, positive Neer sign
Range of Motion: Forward flexion 140 degrees (limited), abduction 120 degrees
Strength: 4/5 with supraspinatus testing

ASSESSMENT:
Right shoulder rotator cuff syndrome
Possible rotator cuff tear

PLAN:
1. Physical therapy - 6 sessions
2. NSAIDs
3. Follow-up 4 weeks"""
            },
            {
                "type": "PT_NOTE",
                "weeks_offset": 4,
                "content": """PHYSICAL THERAPY PROGRESS NOTE
Date: {date}
Patient: PT00005
Sessions: 4 of 6

TREATMENT DURATION: 4 weeks (ONLY 4 weeks so far)
SESSIONS COMPLETED: 4 sessions

SUBJECTIVE:
Patient reports some improvement in pain (6/10 to 4/10). Still has difficulty with overhead activities but partial improvement noted.

OBJECTIVE:
- ROM improved: Forward flexion 160 degrees, abduction 140 degrees
- Strength improving: 4+/5

ASSESSMENT:
Partial improvement after 4 weeks of PT. Has NOT yet completed the recommended 6-week minimum conservative treatment period.

PLAN:
Complete remaining 2 sessions to reach 6-week treatment duration."""
            },
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 5,
                "content": """FOLLOW-UP VISIT

Patient: PT00005
Date: {date}

Patient requesting MRI evaluation. Reports persistent pain despite 4 weeks of physical therapy. States he cannot wait another 2 weeks and wants imaging now due to work demands.

ASSESSMENT:
Right shoulder rotator cuff syndrome
Only 4 weeks of conservative treatment completed (MCG typically requires 6 weeks)
Partial improvement noted

PLAN:
Will submit prior authorization for MRI shoulder (CPT 73221)
NOTE: Patient has only completed 4 weeks of conservative treatment, not the usual 6-week requirement. This may require manual review by insurance."""
            }
        ]
    },

    "PT00007": {
        "age": 35,
        "gender": "female",
        "condition": "hip_pain",
        "records": [
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 0,
                "content": """SUBJECTIVE:
Patient is a 35-year-old female presenting with left hip pain and clicking.
Pain level: 5/10
Duration: 6 months
Mechanical symptoms: Clicking, catching sensation with hip movement

OBJECTIVE:
Examination: Positive FABER test, positive anterior impingement test
ROM: Full but painful at extremes
No deformity

ASSESSMENT:
Left hip labral tear suspected
Femoroacetabular impingement possible

PLAN:
1. Physical therapy - 8 weeks
2. NSAIDs
3. Activity modification"""
            },
            {
                "type": "PT_NOTE",
                "weeks_offset": 8,
                "content": """PHYSICAL THERAPY DISCHARGE NOTE
Date: {date}
Patient: PT00007

TREATMENT DURATION: 8 weeks
SESSIONS COMPLETED: 8 sessions

SUBJECTIVE:
Persistent clicking and pain with certain movements despite 8 weeks of conservative treatment.

ASSESSMENT:
Completed 8 weeks of conservative management with partial relief but persistent mechanical symptoms.

RECOMMENDATION:
Return to physician for further evaluation."""
            },
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 9,
                "content": """FOLLOW-UP VISIT

Patient: PT00007
Date: {date}

Patient completed 8 weeks of physical therapy with persistent symptoms. Requesting arthroscopy evaluation.

X-RAY FINDINGS:
Plain radiographs show mild hip dysplasia, no fracture, no significant arthritis.

ASSESSMENT:
Suspected hip labral tear based on clinical exam
8 weeks conservative treatment completed
NOTE: No MRI confirmation of labral tear - only clinical suspicion and X-ray findings

PLAN:
Will request prior authorization for hip arthroscopy (CPT 29914)
CAVEAT: Most guidelines require MRI confirmation of labral tear before arthroscopy. This case may need manual review as we only have clinical suspicion without MRI documentation."""
            }
        ]
    },

    "PT00010": {
        "age": 28,
        "gender": "male",
        "condition": "acute_acl_injury",
        "records": [
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 0,
                "content": """EMERGENCY DEPARTMENT VISIT

Patient: 28-year-old male
Date: {date}
Chief Complaint: Acute left knee injury

HPI:
Patient injured left knee playing basketball 2 days ago. Heard a "pop" and immediate swelling. Unable to bear weight initially. Now able to walk with limp but knee feels unstable.

PHYSICAL EXAM:
- Effusion present (moderate)
- Lachman test: POSITIVE (2+ laxity, soft endpoint) - concerning for ACL tear
- Anterior drawer: Positive
- McMurray: Negative
- ROM: Limited by pain and swelling

IMAGING:
X-ray knee: No fracture

ASSESSMENT:
Acute ACL sprain/tear (clinical diagnosis)
Acute traumatic knee injury

PLAN:
1. Knee immobilizer, crutches
2. Ice, elevation, NSAIDs
3. Orthopedic follow-up 1 week"""
            },
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 2,
                "content": """ORTHOPEDIC FOLLOW-UP

Patient: PT00010
Date: {date}

Patient 2 weeks post-injury. Swelling improved. Still reports instability with pivoting.

PHYSICAL EXAM:
- Lachman: Positive (grade 2)
- Pivot shift: Positive
- Clinical diagnosis: ACL tear

ASSESSMENT:
Acute ACL tear (clinical)
Young, active patient

PLAN:
Patient requesting MRI for surgical planning. Wants to return to sports.

NOTE: This is an ACUTE injury (2 weeks old). No conservative treatment attempted yet. MCG guidelines typically require trial of conservative treatment for knee MRI unless there are specific indications for urgent imaging (which this case does not have - no fracture, no locked knee, neurovascularly intact).

Will submit MRI request (CPT 73721) but may require manual review as no conservative treatment has been attempted."""
            }
        ]
    },

    # ========================================
    # DENIED CASES (3 patients)
    # ========================================
    "PT00012": {
        "age": 40,
        "gender": "male",
        "condition": "chronic_back_pain",
        "records": [
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 0,
                "content": """SUBJECTIVE:
Patient is a 40-year-old male with chronic low back pain.
Pain level: 5/10
Duration: 5 years, stable, not worsening
No leg pain, no numbness, no weakness
Pain is mechanical, worse with lifting

OBJECTIVE:
Neurological exam: COMPLETELY NORMAL
- Motor: 5/5 all lower extremity muscle groups bilaterally
- Sensory: Intact all dermatomes
- Reflexes: 2+ and symmetric
- Straight leg raise: Negative bilaterally
- No focal neurological deficits

ASSESSMENT:
Chronic mechanical low back pain
NO radiculopathy
NO neurological deficits

PLAN:
Patient requesting MRI and surgical consultation
Referred by chiropractor who suggested "he needs fusion"

NOTE: No conservative treatment has been attempted
No physical therapy
No formal exercise program
No medication trial"""
            },
            {
                "type": "IMAGING_REPORT",
                "weeks_offset": 2,
                "content": """MRI LUMBAR SPINE (Patient paid cash for this)

Patient: PT00012
Date: {date}

FINDINGS:
L4-L5: Mild disc bulge, no significant canal stenosis, no nerve compression
L5-S1: Mild disc degeneration, no herniation

IMPRESSION:
1. Mild degenerative changes L4-L5 and L5-S1
2. NO nerve compression
3. NO spinal stenosis
4. Changes are age-appropriate and do NOT correlate with need for surgery

Findings do not support surgical intervention."""
            },
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 4,
                "content": """NEUROSURGICAL CONSULTATION

Patient: PT00012
Date: {date}

Patient requesting lumbar fusion surgery. States chiropractor told him he "needs fusion."

REVIEW:
- MRI: Mild degenerative changes, NO nerve compression
- Neurological exam: Completely normal
- No radiculopathy
- NO conservative treatment attempted (no PT, no structured exercise program)

ASSESSMENT:
Chronic mechanical low back pain WITHOUT surgical indication
- No neurological deficits
- No nerve compression on imaging
- No spinal instability
- NO conservative treatment has been attempted

RECOMMENDATION:
NOT a surgical candidate. Patient needs conservative treatment first:
- Physical therapy
- Core strengthening program
- Weight loss (patient is obese, BMI 34)

Will NOT submit prior authorization for lumbar fusion (CPT 22630) as there is no surgical indication. Patient does not meet criteria:
✗ No neurological deficits
✗ No nerve compression
✗ No conservative treatment attempted
✗ Inappropriate surgical indication"""
            }
        ]
    },

    "PT00018": {
        "age": 33,
        "gender": "female",
        "condition": "cosmetic",
        "records": [
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 0,
                "content": """PLASTIC SURGERY CONSULTATION

Patient: 33-year-old female
Date: {date}
Chief Complaint: Abdominal skin laxity

HPI:
Patient presents requesting abdominoplasty/panniculectomy. Reports loose abdominal skin following pregnancy (2 children, youngest is 3 years old). States she is "unhappy with appearance" and wants "tummy tuck."

PHYSICAL EXAM:
- Moderate skin laxity lower abdomen
- Striae distensae (stretch marks) present
- No pannicular overhang
- No intertrigo, no rashes, no skin breakdown
- NO functional impairment
- Able to perform all activities without limitation

ASSESSMENT:
Abdominal skin laxity post-pregnancy
Striae distensae
COSMETIC concern, NOT medical indication

REVIEW:
- No rashes or skin infections due to pannus
- No back pain from pannus weight
- No difficulty with ambulation
- No interference with hygiene
- Patient states this is purely about appearance and wanting to "look better in clothes"

PLAN:
Patient requesting insurance coverage for panniculectomy (CPT 15830).

HOWEVER: This is a COSMETIC request without medical necessity:
✗ No functional impairment
✗ No recurrent infections
✗ No hygiene issues
✗ No back pain from pannus
✗ Patient explicitly states cosmetic motivation

Will submit prior authorization but expect DENIAL as this does not meet medical necessity criteria. This is cosmetic surgery."""
            },
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 1,
                "content": """FOLLOW-UP VISIT

Patient: PT00018
Date: {date}

Patient states she "really wants insurance to cover this" and asks if we can document that it's causing problems.

ASSESSMENT:
Patient is clearly requesting cosmetic procedure. There is NO medical documentation of functional impairment, recurrent infections, or other medical indications.

Cosmetic procedures are NOT covered by insurance regardless of documentation.

RECOMMENDATION:
Patient can pursue self-pay cosmetic surgery. Insurance will not cover purely cosmetic procedures."""
            }
        ]
    },

    "PT00020": {
        "age": 50,
        "gender": "female",
        "condition": "new_knee_pain",
        "records": [
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 0,
                "content": """SUBJECTIVE:
Patient is a 50-year-old female presenting with left knee pain.
Pain level: 4/10
Duration: 2 weeks only (NEW onset)
Started after gardening
No trauma, no locking, no instability

OBJECTIVE:
Examination: Mild tenderness lateral joint line
ROM: Full, no effusion
Gait: Normal
No deformity

ASSESSMENT:
New onset knee pain, likely overuse/strain
No red flags for serious pathology

PLAN:
1. NSAIDs for 2-4 weeks
2. Activity modification
3. Ice, rest
4. Follow-up if not improving in 4 weeks

Patient requesting MRI today. Educated that MRI is not indicated for new onset knee pain without conservative treatment or red flags."""
            },
            {
                "type": "CLINICAL_NOTE",
                "weeks_offset": 1,
                "content": """FOLLOW-UP VISIT (Patient called requesting earlier appointment)

Patient: PT00020
Date: {date} (1 week later)

Patient insists on having MRI. States she "read online about meniscus tears" and is worried. Has only had symptoms for 3 weeks total.

ASSESSMENT:
New onset knee pain (3 weeks duration)
NO conservative treatment attempted yet
NO red flags:
✗ No mechanical symptoms (locking)
✗ No instability
✗ No significant effusion
✗ Normal exam
✗ No trauma
✗ Full range of motion

PLAN:
Patient demanding MRI knee (CPT 73721). Explained that guidelines require conservative treatment first for non-acute, non-traumatic knee pain.

Will submit prior authorization but expect DENIAL:
✗ No conservative treatment attempted (no PT, no formal NSAID trial)
✗ Only 3 weeks of symptoms
✗ No red flags requiring urgent imaging
✗ Normal physical exam
✗ Does not meet MCG criteria for knee MRI

Recommended: Complete 6 weeks of conservative treatment (NSAIDs, PT) and reassess. If still symptomatic after conservative treatment, can consider MRI at that time."""
            }
        ]
    }
}

print(f"✅ Defined {len(DEMO_PATIENTS)} demo patients")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Documents

# COMMAND ----------

all_documents = []
doc_count = 0

for patient_id, patient_data in DEMO_PATIENTS.items():
    print(f"\n📝 Generating documents for {patient_id} ({patient_data['age']} {patient_data['gender']}, {patient_data['condition']})...")
    
    for record in patient_data['records']:
        doc_count += 1
        record_date = BASE_DATE + timedelta(weeks=record['weeks_offset'])
        doc_id = f"{patient_id}_{record['type']}_{record_date.strftime('%Y%m%d')}_{record['weeks_offset']}"
        
        # Format content with date
        content_with_date = record['content'].format(date=record_date.strftime('%Y-%m-%d'))
        
        doc = {
            'doc_id': doc_id,
            'patient_id': patient_id,
            'record_type': record['type'],
            'record_date': record_date.strftime('%Y-%m-%d'),
            'condition': patient_data['condition'],
            'content': content_with_date
        }
        
        all_documents.append(doc)
    
    print(f"   ✅ Generated {len(patient_data['records'])} documents")

print(f"\n✅ Total documents generated: {len(all_documents)}")

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
print(f"✅ Patients: {len(DEMO_PATIENTS)}")
print()
print("Demo Patient Summary:")
print("-" * 80)
print(f"APPROVED (4):    PT00001, PT00016, PT00025, PT00003")
print(f"MANUAL_REVIEW (3): PT00005, PT00007, PT00010")
print(f"DENIED (3):      PT00012, PT00018, PT00020")
print("=" * 80)
print("\n📝 Next step: Run 02a_chunk_clinical_records.py to chunk and create tables with CDF")
print("=" * 80)
