# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 03a: Chunk Guidelines for Vector Search
# MAGIC
# MAGIC Reads guideline documents from volume, chunks them optimally, and creates table with Change Data Feed enabled.
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
FULL_TABLE_NAME = cfg.guidelines_table

print(f"Table: {FULL_TABLE_NAME}")
print(f"Volume: {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Drop and Recreate Table with CDF

# COMMAND ----------

# Drop and recreate for clean slate
print(f"🔄 Dropping and recreating table for clean slate")
try:
    spark.sql(f"DROP TABLE IF EXISTS {FULL_TABLE_NAME}")
    print(f"✅ Dropped existing table: {FULL_TABLE_NAME}")
except Exception as e:
    print(f"ℹ️  No existing table to drop: {e}")

# Create table with CDF enabled
spark.sql(f"""
    CREATE TABLE {FULL_TABLE_NAME} (
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
        tags ARRAY<STRING>,
        chunk_index INT,
        total_chunks INT,
        char_count INT,
        created_at TIMESTAMP
    )
    USING DELTA
    TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
""")
print(f"✅ Table created with Change Data Feed enabled: {FULL_TABLE_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Chunking Logic

# COMMAND ----------

from datetime import datetime, date
import re
import json

def extract_decision_criteria(content):
    """Extract decision/approval criteria from guideline content"""
    # Look for approval criteria section
    patterns = [
        r'APPROVAL CRITERIA:(.*?)(?=\n\n|\Z)',
        r'DECISION CRITERIA:(.*?)(?=\n\n|\Z)',
        r'MEDICAL NECESSITY:(.*?)(?=\n\n|\Z)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        if match:
            criteria = match.group(1).strip()
            # Clean up checkboxes and extra whitespace
            criteria = re.sub(r'☐\s*', '', criteria)
            criteria = re.sub(r'\n\s*\n', '\n', criteria)
            return criteria
    
    # If no specific section, try to extract lines with approval keywords
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
    
    # Common medical/procedure terms
    terms = [
        'surgery', 'imaging', 'therapy', 'medication', 'diagnosis',
        'knee', 'cardiac', 'orthopedic', 'radiology', 'cardiology',
        'mri', 'arthroscopy', 'replacement', 'stress test'
    ]
    
    text_lower = text.lower()
    for term in terms:
        if term in text_lower:
            tags.append(term)
    
    return list(set(tags))  # Remove duplicates

def split_guideline_sections(content):
    """Split guideline into logical sections"""
    sections = []
    
    # Common section headers in medical guidelines
    section_patterns = [
        r'^INDICATION:',
        r'^CLINICAL CRITERIA',
        r'^EXCLUSION CRITERIA',
        r'^APPROVAL CRITERIA',
        r'^COVERAGE INDICATIONS',
        r'^SEVERITY OF ILLNESS',
        r'^INTENSITY OF SERVICE',
        r'^MEDICAL NECESSITY',
        r'^DOCUMENTATION REQUIREMENTS',
        r'^\d+\.\s+[A-Z]'  # Numbered sections
    ]
    
    lines = content.split('\n')
    current_section = ""
    
    for line in lines:
        is_header = any(re.match(pattern, line.strip()) for pattern in section_patterns)
        
        if is_header and current_section and len(current_section) > 100:
            sections.append(current_section.strip())
            current_section = line + '\n'
        else:
            current_section += line + '\n'
    
    if current_section:
        sections.append(current_section.strip())
    
    # If no sections found, treat whole content as one section
    if not sections:
        sections = [content]
    
    return sections

def chunk_guideline(file_path, min_chunk_size=None, max_chunk_size=None):
    """Read and chunk a guideline document from volume"""
    if min_chunk_size is None:
        min_chunk_size = cfg.min_chunk_size
    if max_chunk_size is None:
        max_chunk_size = cfg.max_chunk_size
    
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
                # Capture questionnaire JSON (next line)
                if i + 1 < len(lines):
                    questionnaire = lines[i + 1].strip()
            elif i > 8 and not line.startswith("QUESTIONNAIRE"):
                main_content.append(line)
        
        content_text = '\n'.join(main_content).strip()
        
        # Split into sections
        sections = split_guideline_sections(content_text)
        
        # Chunk sections if needed
        chunks = []
        for section in sections:
            if len(section) <= max_chunk_size:
                chunks.append(section)
            else:
                # Split large sections by paragraphs
                paragraphs = section.split('\n\n')
                current_chunk = ""
                
                for para in paragraphs:
                    if len(current_chunk) + len(para) <= max_chunk_size:
                        current_chunk += para + '\n\n'
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = para + '\n\n'
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
        
        # Extract tags
        tags = extract_tags(content_text)
        
        # Extract decision criteria from content
        decision_criteria = extract_decision_criteria(content_text)
        
        # Create chunk records
        total_chunks = len(chunks)
        chunk_records = []
        
        for idx, chunk_content in enumerate(chunks):
            chunk_records.append({
                'guideline_id': f"{guideline_id}_chunk_{idx}",
                'platform': platform,
                'category': category,
                'procedure_code': procedure_code,
                'diagnosis_code': diagnosis_code,
                'title': title,
                'content': chunk_content,
                'questionnaire': questionnaire,
                'decision_criteria': decision_criteria,  # Now extracted from content
                'effective_date': effective_date,
                'tags': tags,
                'chunk_index': idx,
                'total_chunks': total_chunks,
                'char_count': len(chunk_content),
                'created_at': datetime.now()
            })
        
        return chunk_records
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

print("✅ Chunking functions loaded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Process All Guidelines

# COMMAND ----------

# List all files in volume
files = dbutils.fs.ls(VOLUME_PATH)
print(f"Found {len(files)} files in volume")

all_chunks = []
for file_info in files:
    if file_info.path.endswith('.txt'):
        print(f"Processing: {file_info.name}")
        chunks = chunk_guideline(file_info.path)
        all_chunks.extend(chunks)
        print(f"  → Created {len(chunks)} chunks")

print(f"\n✅ Total chunks created: {len(all_chunks)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Insert Chunks into Table

# COMMAND ----------

from pyspark.sql.types import *

# Define schema
chunk_schema = StructType([
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
    StructField("tags", ArrayType(StringType()), False),
    StructField("chunk_index", IntegerType(), False),
    StructField("total_chunks", IntegerType(), False),
    StructField("char_count", IntegerType(), False),
    StructField("created_at", TimestampType(), False)
])

# Create DataFrame and write to table
if all_chunks:
    chunks_df = spark.createDataFrame(all_chunks, schema=chunk_schema)
    chunks_df.write.mode("append").saveAsTable(FULL_TABLE_NAME)
    print(f"✅ Inserted {len(all_chunks)} chunks into {FULL_TABLE_NAME}")
else:
    print("⚠️  No chunks to insert")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Table

# COMMAND ----------

print("=" * 80)
print("GUIDELINES TABLE STATISTICS")
print("=" * 80)

stats = spark.sql(f"""
SELECT 
    COUNT(*) as total_chunks,
    COUNT(DISTINCT platform) as platforms,
    AVG(char_count) as avg_chunk_size,
    MIN(char_count) as min_chunk_size,
    MAX(char_count) as max_chunk_size
FROM {FULL_TABLE_NAME}
""").collect()[0]

print(f"Total Chunks:      {stats['total_chunks']}")
print(f"Platforms:         {stats['platforms']}")
print(f"Avg Chunk Size:    {stats['avg_chunk_size']:.0f} chars")
print(f"Min Chunk Size:    {stats['min_chunk_size']} chars")
print(f"Max Chunk Size:    {stats['max_chunk_size']} chars")
print("=" * 80)

# Show platform breakdown
print("\nPlatform breakdown:")
display(spark.sql(f"""
SELECT platform, COUNT(*) as chunks
FROM {FULL_TABLE_NAME}
GROUP BY platform
ORDER BY chunks DESC
"""))

# Show sample chunks
print("\nSample chunks:")
display(spark.sql(f"""
SELECT guideline_id, platform, procedure_code, chunk_index, total_chunks, char_count, LEFT(content, 100) as content_preview
FROM {FULL_TABLE_NAME}
LIMIT 5
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("GUIDELINES TABLE CREATED WITH CDF!")
print("=" * 80)
print(f"✅ Table: {FULL_TABLE_NAME}")
print(f"✅ Change Data Feed: ENABLED")
print(f"✅ Total Chunks: {len(all_chunks)}")
print("=" * 80)
print("\n📝 Next step: Run 06_create_vector_index_guidelines.py to create vector search index")
print("=" * 80)

