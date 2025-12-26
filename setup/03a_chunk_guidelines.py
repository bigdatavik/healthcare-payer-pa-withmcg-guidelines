# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 03a: Process Guidelines - Two-Table Architecture
# MAGIC
# MAGIC Reads guideline documents from volume and writes to TWO tables:
# MAGIC 1. `clinical_guidelines` - FULL guidelines (for PA review)
# MAGIC 2. `clinical_guidelines_chunks` - Chunked guidelines (for vector search)
# MAGIC
# MAGIC **Configuration:** Reads from config.yaml via shared.config module

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

VOLUME_PATH = cfg.guidelines_volume_path
FULL_GUIDELINES_TABLE = f"{cfg.catalog}.{cfg.schema}.clinical_guidelines"
CHUNKS_TABLE = f"{cfg.catalog}.{cfg.schema}.clinical_guidelines_chunks"

print(f"Full Guidelines Table: {FULL_GUIDELINES_TABLE}")
print(f"Chunks Table:          {CHUNKS_TABLE}")
print(f"Volume:                {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Drop and Recreate Tables with CDF

# COMMAND ----------

print(f"🔄 Dropping and recreating tables for clean slate")

# Drop full guidelines table
try:
    spark.sql(f"DROP TABLE IF EXISTS {FULL_GUIDELINES_TABLE}")
    print(f"✅ Dropped existing table: {FULL_GUIDELINES_TABLE}")
except Exception as e:
    print(f"ℹ️  No existing table to drop: {e}")

# Drop chunks table
try:
    spark.sql(f"DROP TABLE IF EXISTS {CHUNKS_TABLE}")
    print(f"✅ Dropped existing table: {CHUNKS_TABLE}")
except Exception as e:
    print(f"ℹ️  No existing table to drop: {e}")

# Create FULL GUIDELINES table
spark.sql(f"""
    CREATE TABLE {FULL_GUIDELINES_TABLE} (
        guideline_id STRING,
        platform STRING,
        category STRING,
        procedure_code STRING,
        diagnosis_code STRING,
        title STRING,
        content STRING,
        questionnaire STRING,
        decision_criteria STRING,
        effective_date DATE,
        tags STRING,
        created_at TIMESTAMP
    )
    USING DELTA
    TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
""")
print(f"✅ Full guidelines table created with CDF: {FULL_GUIDELINES_TABLE}")

# Create CHUNKS table
spark.sql(f"""
    CREATE TABLE {CHUNKS_TABLE} (
        chunk_id STRING,
        guideline_id STRING,
        procedure_code STRING,
        diagnosis_code STRING,
        chunk_index INT,
        chunk_text STRING,
        tags ARRAY<STRING>,
        char_count INT,
        created_at TIMESTAMP
    )
    USING DELTA
    TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
""")
print(f"✅ Chunks table created with CDF: {CHUNKS_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Processing Logic

# COMMAND ----------

from datetime import datetime, date
import re
import json

def extract_decision_criteria(content):
    """Extract decision/approval criteria from guideline content"""
    patterns = [
        r'APPROVAL CRITERIA:(.*?)(?=\n\n|\Z)',
        r'DECISION CRITERIA:(.*?)(?=\n\n|\Z)',
        r'MEDICAL NECESSITY:(.*?)(?=\n\n|\Z)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        if match:
            criteria = match.group(1).strip()
            criteria = re.sub(r'☐\s*', '', criteria)
            criteria = re.sub(r'\n\s*\n', '\n', criteria)
            return criteria
    
    lines = content.split('\n')
    criteria_lines = []
    for line in lines:
        if any(keyword in line.upper() for keyword in ['APPROVED', 'DENIED', 'MANUAL REVIEW', 'CRITERIA MET', 'NOT MET']):
            criteria_lines.append(line.strip())
    
    if criteria_lines:
        return '\n'.join(criteria_lines)
    
    return None

def extract_tags(text):
    """Extract tags from guideline content"""
    tags = []
    terms = [
        'surgery', 'imaging', 'therapy', 'medication', 'diagnosis',
        'knee', 'cardiac', 'orthopedic', 'radiology', 'cardiology',
        'mri', 'arthroscopy', 'replacement', 'stress test'
    ]
    
    text_lower = text.lower()
    for term in terms:
        if term in text_lower:
            tags.append(term)
    
    return list(set(tags))

def chunk_text(text, min_size, max_size):
    """Chunk text into optimal sizes"""
    if len(text) <= max_size:
        return [text]
    
    # Split by sections or paragraphs
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) <= max_size:
            current_chunk += para + '\n\n'
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + '\n\n'
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def process_guideline(file_path):
    """Process a guideline document and return both full guideline and chunks"""
    try:
        content = dbutils.fs.head(file_path, 1000000)
        
        # Extract metadata
        lines = content.split('\n')
        guideline_id = ""
        platform = ""
        category = ""
        procedure_code = ""
        diagnosis_code = ""
        title = ""
        effective_date = None
        questionnaire = ""
        main_content = []
        
        for i, line in enumerate(lines):
            if line.startswith("Guideline ID:"):
                guideline_id = line.replace("Guideline ID:", "").strip()
            elif line.startswith("Platform:"):
                platform = line.replace("Platform:", "").strip()
            elif line.startswith("Category:"):
                category = line.replace("Category:", "").strip()
            elif line.startswith("Procedure Code:"):
                procedure_code = line.replace("Procedure Code:", "").strip()
            elif line.startswith("Diagnosis Code:"):
                diagnosis_code = line.replace("Diagnosis Code:", "").strip()
            elif line.startswith("Title:"):
                title = line.replace("Title:", "").strip()
            elif line.startswith("Effective Date:"):
                date_str = line.replace("Effective Date:", "").strip()
                try:
                    effective_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except:
                    effective_date = date.today()
            elif line.startswith("QUESTIONNAIRE:"):
                if i + 1 < len(lines):
                    questionnaire = lines[i + 1].strip()
            elif i > 8 and not line.startswith("QUESTIONNAIRE"):
                main_content.append(line)
        
        content_text = '\n'.join(main_content).strip()
        
        # Extract metadata from content
        tags = extract_tags(content_text)
        tags_str = ','.join(tags)
        decision_criteria = extract_decision_criteria(content_text)
        
        # 1. FULL GUIDELINE (for PA review)
        full_guideline = {
            'guideline_id': guideline_id,
            'platform': platform,
            'category': category,
            'procedure_code': procedure_code,
            'diagnosis_code': diagnosis_code,
            'title': title,
            'content': content_text,  # FULL TEXT (no chunking)
            'questionnaire': questionnaire,
            'decision_criteria': decision_criteria,
            'effective_date': effective_date,
            'tags': tags_str,
            'created_at': datetime.now()
        }
        
        # 2. CHUNKS (for vector search)
        text_chunks = chunk_text(content_text, cfg.min_chunk_size, cfg.max_chunk_size)
        chunk_records = []
        
        for idx, chunk_content in enumerate(text_chunks):
            chunk_records.append({
                'chunk_id': f"{guideline_id}_chunk_{idx}",
                'guideline_id': guideline_id,
                'procedure_code': procedure_code,
                'diagnosis_code': diagnosis_code,
                'chunk_index': idx,
                'chunk_text': chunk_content,
                'tags': tags,
                'char_count': len(chunk_content),
                'created_at': datetime.now()
            })
        
        return full_guideline, chunk_records
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None, []

print("✅ Processing functions loaded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Process All Guidelines

# COMMAND ----------

# List all files in volume
files = dbutils.fs.ls(VOLUME_PATH)
print(f"Found {len(files)} files in volume")

full_guidelines = []
all_chunks = []

for file_info in files:
    if file_info.path.endswith('.txt'):
        print(f"Processing: {file_info.name}")
        full_guide, chunks = process_guideline(file_info.path)
        if full_guide:
            full_guidelines.append(full_guide)
            all_chunks.extend(chunks)
            print(f"  → 1 full guideline, {len(chunks)} chunks")

print(f"\n✅ Total full guidelines: {len(full_guidelines)}")
print(f"✅ Total chunks:          {len(all_chunks)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Insert FULL GUIDELINES into Table

# COMMAND ----------

from pyspark.sql.types import *

# Define schema for FULL guidelines
full_guideline_schema = StructType([
    StructField("guideline_id", StringType(), False),
    StructField("platform", StringType(), False),
    StructField("category", StringType(), False),
    StructField("procedure_code", StringType(), True),
    StructField("diagnosis_code", StringType(), True),
    StructField("title", StringType(), False),
    StructField("content", StringType(), False),
    StructField("questionnaire", StringType(), True),
    StructField("decision_criteria", StringType(), True),
    StructField("effective_date", DateType(), True),
    StructField("tags", StringType(), True),
    StructField("created_at", TimestampType(), False)
])

# Write full guidelines
if full_guidelines:
    full_guidelines_df = spark.createDataFrame(full_guidelines, schema=full_guideline_schema)
    full_guidelines_df.write.mode("append").saveAsTable(FULL_GUIDELINES_TABLE)
    print(f"✅ Inserted {len(full_guidelines)} FULL guidelines into {FULL_GUIDELINES_TABLE}")
else:
    print("⚠️  No full guidelines to insert")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Insert CHUNKS into Table

# COMMAND ----------

# Define schema for CHUNKS
chunk_schema = StructType([
    StructField("chunk_id", StringType(), False),
    StructField("guideline_id", StringType(), False),
    StructField("procedure_code", StringType(), True),
    StructField("diagnosis_code", StringType(), True),
    StructField("chunk_index", IntegerType(), False),
    StructField("chunk_text", StringType(), False),
    StructField("tags", ArrayType(StringType()), False),
    StructField("char_count", IntegerType(), False),
    StructField("created_at", TimestampType(), False)
])

# Write chunks
if all_chunks:
    chunks_df = spark.createDataFrame(all_chunks, schema=chunk_schema)
    chunks_df.write.mode("append").saveAsTable(CHUNKS_TABLE)
    print(f"✅ Inserted {len(all_chunks)} CHUNKS into {CHUNKS_TABLE}")
else:
    print("⚠️  No chunks to insert")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Tables

# COMMAND ----------

print("=" * 80)
print("FULL GUIDELINES TABLE (For PA Review)")
print("=" * 80)

stats1 = spark.sql(f"""
SELECT 
    COUNT(*) as total_guidelines,
    COUNT(DISTINCT platform) as platforms,
    AVG(LENGTH(content)) as avg_content_length
FROM {FULL_GUIDELINES_TABLE}
""").collect()[0]

print(f"Total Guidelines:   {stats1['total_guidelines']}")
print(f"Platforms:          {stats1['platforms']}")
print(f"Avg Content Length: {stats1['avg_content_length']:.0f} chars")
print("=" * 80)

print("\n" + "=" * 80)
print("CHUNKS TABLE (For Vector Search)")
print("=" * 80)

stats2 = spark.sql(f"""
SELECT 
    COUNT(*) as total_chunks,
    AVG(char_count) as avg_chunk_size,
    MIN(char_count) as min_chunk_size,
    MAX(char_count) as max_chunk_size
FROM {CHUNKS_TABLE}
""").collect()[0]

print(f"Total Chunks:       {stats2['total_chunks']}")
print(f"Avg Chunk Size:     {stats2['avg_chunk_size']:.0f} chars")
print(f"Min Chunk Size:     {stats2['min_chunk_size']} chars")
print(f"Max Chunk Size:     {stats2['max_chunk_size']} chars")
print("=" * 80)

# Show sample full guidelines
print("\nSample FULL guidelines:")
display(spark.sql(f"""
SELECT guideline_id, platform, procedure_code, diagnosis_code, LENGTH(content) as content_length, LEFT(content, 100) as content_preview
FROM {FULL_GUIDELINES_TABLE}
LIMIT 5
"""))

# Show sample chunks
print("\nSample CHUNKS:")
display(spark.sql(f"""
SELECT chunk_id, guideline_id, procedure_code, chunk_index, char_count, LEFT(chunk_text, 100) as chunk_preview
FROM {CHUNKS_TABLE}
LIMIT 5
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("TWO-TABLE ARCHITECTURE COMPLETE!")
print("=" * 80)
print(f"✅ Full Guidelines Table: {FULL_GUIDELINES_TABLE}")
print(f"   - {len(full_guidelines)} complete guidelines")
print(f"   - Used by: PA agent for complete context")
print(f"   - Change Data Feed: ENABLED")
print()
print(f"✅ Chunks Table:          {CHUNKS_TABLE}")
print(f"   - {len(all_chunks)} chunks for semantic search")
print(f"   - Used by: Vector search index")
print(f"   - Change Data Feed: ENABLED")
print("=" * 80)
print("\n📝 Next step: Run 06_create_vector_index_guidelines.py")
print("   (Vector index will point to CHUNKS table)")
print("=" * 80)
