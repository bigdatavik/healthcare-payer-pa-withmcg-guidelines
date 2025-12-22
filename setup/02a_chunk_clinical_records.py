# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 02a: Chunk Clinical Records for Vector Search
# MAGIC
# MAGIC Reads clinical documents from volume, chunks them optimally, and creates table with Change Data Feed enabled.
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
FULL_TABLE_NAME = cfg.clinical_records_table

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
        record_id STRING,
        patient_id STRING,
        record_type STRING,
        record_date TIMESTAMP,
        content STRING,
        keywords ARRAY<STRING>,
        chunk_index INT,
        total_chunks INT,
        char_count INT,
        created_at TIMESTAMP,
        source_system STRING,
        provider_id STRING,
        metadata STRING
    )
    USING DELTA
    TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
""")
print(f"✅ Table created with Change Data Feed enabled: {FULL_TABLE_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Chunking Logic

# COMMAND ----------

from datetime import datetime
import re

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

def chunk_document(file_path, min_chunk_size=None, max_chunk_size=None):
    """Read and chunk a clinical document from volume"""
    if min_chunk_size is None:
        min_chunk_size = cfg.min_chunk_size
    if max_chunk_size is None:
        max_chunk_size = cfg.max_chunk_size
    
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
        
        # For short documents, keep as single chunk
        if len(content_text) <= max_chunk_size:
            chunks = [content_text]
        else:
            # Split by paragraphs
            paragraphs = content_text.split('\n\n')
            chunks = []
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
        
        # Create chunk records
        total_chunks = len(chunks)
        chunk_records = []
        
        for idx, chunk_content in enumerate(chunks):
            keywords = extract_keywords(chunk_content)
            
            chunk_records.append({
                'record_id': f"{doc_id}_chunk_{idx}",
                'patient_id': patient_id,
                'record_type': record_type,
                'record_date': datetime.strptime(record_date, '%Y-%m-%d') if record_date else None,
                'content': chunk_content,
                'keywords': keywords,
                'chunk_index': idx,
                'total_chunks': total_chunks,
                'char_count': len(chunk_content),
                'created_at': datetime.now(),
                'source_system': 'Epic',
                'provider_id': f"DR{random.randint(1000, 9999)}",
                'metadata': json.dumps({'condition': condition})
            })
        
        return chunk_records
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

import random
import json
print("✅ Chunking functions loaded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Process All Documents

# COMMAND ----------

# List all files in volume
files = dbutils.fs.ls(VOLUME_PATH)
print(f"Found {len(files)} files in volume")

all_chunks = []
for file_info in files:
    if file_info.path.endswith('.txt'):
        chunks = chunk_document(file_info.path)
        all_chunks.extend(chunks)
        if len(all_chunks) % 100 == 0:
            print(f"Processed {len(all_chunks)} chunks so far...")

print(f"\n✅ Total chunks created: {len(all_chunks)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Insert Chunks into Table

# COMMAND ----------

from pyspark.sql.types import *

# Define schema
chunk_schema = StructType([
    StructField("record_id", StringType(), False),
    StructField("patient_id", StringType(), False),
    StructField("record_type", StringType(), False),
    StructField("record_date", TimestampType(), True),
    StructField("content", StringType(), False),
    StructField("keywords", ArrayType(StringType()), False),
    StructField("chunk_index", IntegerType(), False),
    StructField("total_chunks", IntegerType(), False),
    StructField("char_count", IntegerType(), False),
    StructField("created_at", TimestampType(), False),
    StructField("source_system", StringType(), True),
    StructField("provider_id", StringType(), True),
    StructField("metadata", StringType(), True)
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
print("CLINICAL RECORDS TABLE STATISTICS")
print("=" * 80)

stats = spark.sql(f"""
SELECT 
    COUNT(*) as total_chunks,
    COUNT(DISTINCT patient_id) as unique_patients,
    AVG(char_count) as avg_chunk_size,
    MIN(char_count) as min_chunk_size,
    MAX(char_count) as max_chunk_size
FROM {FULL_TABLE_NAME}
""").collect()[0]

print(f"Total Chunks:      {stats['total_chunks']}")
print(f"Unique Patients:   {stats['unique_patients']}")
print(f"Avg Chunk Size:    {stats['avg_chunk_size']:.0f} chars")
print(f"Min Chunk Size:    {stats['min_chunk_size']} chars")
print(f"Max Chunk Size:    {stats['max_chunk_size']} chars")
print("=" * 80)

# Show sample chunks
print("\nSample chunks:")
display(spark.sql(f"""
SELECT record_id, patient_id, record_type, chunk_index, total_chunks, char_count, LEFT(content, 100) as content_preview
FROM {FULL_TABLE_NAME}
LIMIT 5
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("CLINICAL RECORDS TABLE CREATED WITH CDF!")
print("=" * 80)
print(f"✅ Table: {FULL_TABLE_NAME}")
print(f"✅ Change Data Feed: ENABLED")
print(f"✅ Total Chunks: {len(all_chunks)}")
print("=" * 80)
print("\n📝 Next step: Run 05_create_vector_index_clinical.py to create vector search index")
print("=" * 80)

