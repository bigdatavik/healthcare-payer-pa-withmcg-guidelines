# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 02a: Process Clinical Records - Two-Table Architecture
# MAGIC
# MAGIC Reads clinical documents from volume and writes to TWO tables:
# MAGIC 1. `patient_clinical_records` - FULL records (for PA review)
# MAGIC 2. `patient_clinical_records_chunks` - Chunked records (for vector search)
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

VOLUME_PATH = cfg.clinical_volume_path
FULL_RECORDS_TABLE = f"{cfg.catalog}.{cfg.schema}.patient_clinical_records"
CHUNKS_TABLE = f"{cfg.catalog}.{cfg.schema}.patient_clinical_records_chunks"

print(f"Full Records Table: {FULL_RECORDS_TABLE}")
print(f"Chunks Table:       {CHUNKS_TABLE}")
print(f"Volume:             {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Drop and Recreate Tables with CDF

# COMMAND ----------

print(f"🔄 Dropping and recreating tables for clean slate")

# Drop full records table
try:
    spark.sql(f"DROP TABLE IF EXISTS {FULL_RECORDS_TABLE}")
    print(f"✅ Dropped existing table: {FULL_RECORDS_TABLE}")
except Exception as e:
    print(f"ℹ️  No existing table to drop: {e}")

# Drop chunks table
try:
    spark.sql(f"DROP TABLE IF EXISTS {CHUNKS_TABLE}")
    print(f"✅ Dropped existing table: {CHUNKS_TABLE}")
except Exception as e:
    print(f"ℹ️  No existing table to drop: {e}")

# Create FULL RECORDS table
spark.sql(f"""
    CREATE TABLE {FULL_RECORDS_TABLE} (
        record_id STRING,
        patient_id STRING,
        record_type STRING,
        record_date TIMESTAMP,
        content STRING,
        source_system STRING,
        provider_id STRING,
        metadata STRING,
        created_at TIMESTAMP
    )
    USING DELTA
    TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
""")
print(f"✅ Full records table created with CDF: {FULL_RECORDS_TABLE}")

# Create CHUNKS table
spark.sql(f"""
    CREATE TABLE {CHUNKS_TABLE} (
        chunk_id STRING,
        record_id STRING,
        patient_id STRING,
        record_type STRING,
        chunk_index INT,
        chunk_text STRING,
        keywords ARRAY<STRING>,
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

from datetime import datetime
import re
import random
import json

def extract_keywords(text, max_keywords=10):
    """Extract keywords from clinical text"""
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 
                  'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 
                  'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 
                  'these', 'those', 'not', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
                  'patient', 'clinical', 'record', 'note'}
    
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    word_freq = {}
    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:max_keywords]
    return [word for word, freq in keywords]

def chunk_text(text, min_size, max_size):
    """Chunk text into optimal sizes"""
    if len(text) <= max_size:
        return [text]
    
    # Split by paragraphs
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

def process_document(file_path):
    """Process a clinical document and return both full record and chunks"""
    try:
        content = dbutils.fs.head(file_path, 1000000)
        
        # Extract metadata
        lines = content.split('\n')
        doc_id = ""
        patient_id = ""
        record_type = ""
        record_date = ""
        condition = ""
        main_content = []
        
        for i, line in enumerate(lines):
            if line.startswith("Document ID:"):
                doc_id = line.replace("Document ID:", "").strip()
            elif line.startswith("Patient ID:"):
                patient_id = line.replace("Patient ID:", "").strip()
            elif line.startswith("Record Type:"):
                record_type = line.replace("Record Type:", "").strip()
            elif line.startswith("Record Date:"):
                record_date = line.replace("Record Date:", "").strip()
            elif line.startswith("Condition:"):
                condition = line.replace("Condition:", "").strip()
            elif i > 5:
                main_content.append(line)
        
        content_text = '\n'.join(main_content).strip()
        
        # 1. FULL RECORD (for PA review)
        full_record = {
            'record_id': doc_id,
            'patient_id': patient_id,
            'record_type': record_type,
            'record_date': datetime.strptime(record_date, '%Y-%m-%d') if record_date else None,
            'content': content_text,  # FULL TEXT (no chunking)
            'source_system': 'Epic',
            'provider_id': f"DR{random.randint(1000, 9999)}",
            'metadata': json.dumps({'condition': condition}),
            'created_at': datetime.now()
        }
        
        # 2. CHUNKS (for vector search)
        text_chunks = chunk_text(content_text, cfg.min_chunk_size, cfg.max_chunk_size)
        chunk_records = []
        
        for idx, chunk_content in enumerate(text_chunks):
            keywords = extract_keywords(chunk_content)
            
            chunk_records.append({
                'chunk_id': f"{doc_id}_chunk_{idx}",
                'record_id': doc_id,
                'patient_id': patient_id,
                'record_type': record_type,
                'chunk_index': idx,
                'chunk_text': chunk_content,
                'keywords': keywords,
                'char_count': len(chunk_content),
                'created_at': datetime.now()
            })
        
        return full_record, chunk_records
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None, []

print("✅ Processing functions loaded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Process All Documents

# COMMAND ----------

# List all files in volume
files = dbutils.fs.ls(VOLUME_PATH)
print(f"Found {len(files)} files in volume")

full_records = []
all_chunks = []

for file_info in files:
    if file_info.path.endswith('.txt'):
        full_rec, chunks = process_document(file_info.path)
        if full_rec:
            full_records.append(full_rec)
            all_chunks.extend(chunks)
        if len(full_records) % 20 == 0:
            print(f"Processed {len(full_records)} documents, {len(all_chunks)} chunks...")

print(f"\n✅ Total full records: {len(full_records)}")
print(f"✅ Total chunks:       {len(all_chunks)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Insert FULL RECORDS into Table

# COMMAND ----------

from pyspark.sql.types import *

# Define schema for FULL records
full_record_schema = StructType([
    StructField("record_id", StringType(), False),
    StructField("patient_id", StringType(), False),
    StructField("record_type", StringType(), False),
    StructField("record_date", TimestampType(), True),
    StructField("content", StringType(), False),
    StructField("source_system", StringType(), True),
    StructField("provider_id", StringType(), True),
    StructField("metadata", StringType(), True),
    StructField("created_at", TimestampType(), False)
])

# Write full records
if full_records:
    full_records_df = spark.createDataFrame(full_records, schema=full_record_schema)
    full_records_df.write.mode("append").saveAsTable(FULL_RECORDS_TABLE)
    print(f"✅ Inserted {len(full_records)} FULL records into {FULL_RECORDS_TABLE}")
else:
    print("⚠️  No full records to insert")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Insert CHUNKS into Table

# COMMAND ----------

# Define schema for CHUNKS
chunk_schema = StructType([
    StructField("chunk_id", StringType(), False),
    StructField("record_id", StringType(), False),
    StructField("patient_id", StringType(), False),
    StructField("record_type", StringType(), False),
    StructField("chunk_index", IntegerType(), False),
    StructField("chunk_text", StringType(), False),
    StructField("keywords", ArrayType(StringType()), False),
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
print("FULL RECORDS TABLE (For PA Review)")
print("=" * 80)

stats1 = spark.sql(f"""
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT patient_id) as unique_patients,
    AVG(LENGTH(content)) as avg_content_length
FROM {FULL_RECORDS_TABLE}
""").collect()[0]

print(f"Total Records:      {stats1['total_records']}")
print(f"Unique Patients:    {stats1['unique_patients']}")
print(f"Avg Content Length: {stats1['avg_content_length']:.0f} chars")
print("=" * 80)

print("\n" + "=" * 80)
print("CHUNKS TABLE (For Vector Search)")
print("=" * 80)

stats2 = spark.sql(f"""
SELECT 
    COUNT(*) as total_chunks,
    COUNT(DISTINCT patient_id) as unique_patients,
    AVG(char_count) as avg_chunk_size,
    MIN(char_count) as min_chunk_size,
    MAX(char_count) as max_chunk_size
FROM {CHUNKS_TABLE}
""").collect()[0]

print(f"Total Chunks:       {stats2['total_chunks']}")
print(f"Unique Patients:    {stats2['unique_patients']}")
print(f"Avg Chunk Size:     {stats2['avg_chunk_size']:.0f} chars")
print(f"Min Chunk Size:     {stats2['min_chunk_size']} chars")
print(f"Max Chunk Size:     {stats2['max_chunk_size']} chars")
print("=" * 80)

# Show sample full records
print("\nSample FULL records:")
display(spark.sql(f"""
SELECT record_id, patient_id, record_type, LENGTH(content) as content_length, LEFT(content, 100) as content_preview
FROM {FULL_RECORDS_TABLE}
LIMIT 5
"""))

# Show sample chunks
print("\nSample CHUNKS:")
display(spark.sql(f"""
SELECT chunk_id, patient_id, record_type, chunk_index, char_count, LEFT(chunk_text, 100) as chunk_preview
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
print(f"✅ Full Records Table: {FULL_RECORDS_TABLE}")
print(f"   - {len(full_records)} complete clinical records")
print(f"   - Used by: PA agent for complete context")
print(f"   - Change Data Feed: ENABLED")
print()
print(f"✅ Chunks Table:       {CHUNKS_TABLE}")
print(f"   - {len(all_chunks)} chunks for semantic search")
print(f"   - Used by: Vector search index")
print(f"   - Change Data Feed: ENABLED")
print("=" * 80)
print("\n📝 Next step: Run 05_create_vector_index_clinical.py")
print("   (Vector index will point to CHUNKS table)")
print("=" * 80)
