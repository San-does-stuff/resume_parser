import pandas as pd
import os

# ── CONFIG ─────────────────────────────────────────────
INPUT_FILE = r'C:\Users\apeks\OneDrive\Desktop\Seventh\Project\resume_parser\datasets\raw\UpdatedResumeDataSet.csv'
OUTPUT_DIR = r'C:\Users\apeks\OneDrive\Desktop\Seventh\Project\resume_parser\datasets\raw\split_files'
ROWS_PER_FILE = 5000   # change this as needed

# ── CREATE OUTPUT DIRECTORY ────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"Loading file: {INPUT_FILE}...")

# Try safe loading (handles encoding issues)
try:
    df = pd.read_csv(INPUT_FILE, encoding='utf-8')
except UnicodeDecodeError:
    print("UTF-8 failed, switching to latin1...")
    df = pd.read_csv(INPUT_FILE, encoding='latin1')

total_rows = len(df)
print(f"Total rows: {total_rows}")

# ── SPLIT FILE ─────────────────────────────────────────
file_count = 0

for start in range(0, total_rows, ROWS_PER_FILE):
    end = start + ROWS_PER_FILE
    chunk = df.iloc[start:end]

    output_file = os.path.join(OUTPUT_DIR, f"resume_part_{file_count + 1}.csv")
    chunk.to_csv(output_file, index=False, encoding='utf-8')

    print(f"Saved: {output_file} (rows {start} to {end})")

    file_count += 1

print("\n" + "="*50)
print("SPLITTING COMPLETED")
print("="*50)
print(f"Total parts created: {file_count}")
print(f"Each file contains up to {ROWS_PER_FILE} rows")