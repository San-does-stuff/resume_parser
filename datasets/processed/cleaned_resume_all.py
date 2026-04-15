"""
Resume Dataset Preprocessor — Full Dataset (43 Categories)
============================================================
Reads the 3 raw split CSV files, applies deep cleaning,
extracts skills / education / experience via regex,
and saves a single model-ready CSV.

File placement
--------------
    project/
    ├── datasets/
    │   ├── raw/
    │   │   ├── resume_part_1.csv
    │   │   ├── resume_part_2.csv
    │   │   └── resume_part_3.csv
    │   └── processed/
    │       └── model_ready_resume.csv   <- OUTPUT
    └── ml/
        └── resume_classifier_custom_nb.ipynb

Run:
    python preprocess_dataset.py
"""

import os, re, warnings
import pandas as pd, numpy as np
from collections import defaultdict
warnings.filterwarnings('ignore')

# ── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_FILES = [
    r'C:\Users\apeks\OneDrive\Desktop\Seventh\Project\resume_parser\datasets\raw\split_files\resume_part_1.csv',
    r'C:\Users\apeks\OneDrive\Desktop\Seventh\Project\resume_parser\datasets\raw\split_files\resume_part_2.csv',
    r'C:\Users\apeks\OneDrive\Desktop\Seventh\Project\resume_parser\datasets\raw\split_files\resume_part_3.csv',
]
OUTPUT_FILE = r'C:\Users\apeks\OneDrive\Desktop\Seventh\Project\resume_parser\datasets\processed\cleaned_resume.csv'

# Drop malformed category rows (encoding artifacts)
EXCLUDE_PATTERNS = ['"', "'", ';']

ALL_SECTIONS = (
    r'(?:SKILLS?|TECHNICAL\s+SKILLS?|EDUCATION|EXPERIENCE'
    r'|WORK\s+HISTORY|EMPLOYMENT|SUMMARY|OBJECTIVE'
    r'|CERTIFICATIONS?|ACHIEVEMENTS?)'
)


# ── STEP 1: LOAD & MERGE ──────────────────────────────────────────────────────
def load_and_merge(file_paths):
    dfs = []
    for path in file_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Not found: {path}")
        dfs.append(pd.read_csv(path))
    df = pd.concat(dfs, ignore_index=True)
    df.columns = ['category', 'raw_text']
    # Drop header rows and malformed categories
    df = df[df['category'] != 'Category']
    df = df[~df['category'].apply(
        lambda x: any(p in str(x) for p in EXCLUDE_PATTERNS)
    )].reset_index(drop=True)
    print(f"[1/5] Loaded {len(df):,} rows | {df['category'].nunique()} categories")
    print(f"      Categories: {sorted(df['category'].unique())}")
    return df


# ── STEP 2: DEEP CLEAN RAW OCR TEXT ──────────────────────────────────────────
def deep_clean(text):
    """Remove OCR artifacts, escape sequences, placeholders, noise symbols."""
    if not isinstance(text, str): return ''
    # normalize line endings
    for s, r in [('\\r\\n',' '),('\\r',' '),('\\n',' '),
                 ('\r\n',' '),('\r',' '),('\n',' ')]:
        text = text.replace(s, r)
    text = re.sub(r'^\?[_\s]*', '', text)           # leading OCR artifact
    text = re.sub(r'\?[_]{3,}', ' ', text)          # ?___ separators
    text = re.sub(r'\[[\w\s/]+\]', '', text)         # [Number] [Software] etc.
    text = re.sub(r'[•●○◦►▪■□✓✔✗×°¿¡©®™€£¥…]+', ' ', text)
    text = re.sub(r'\.{2,}', ' ', text)              # ellipsis artifacts
    text = re.sub(r'\s[^a-zA-Z0-9]\s', ' ', text)   # stray single symbols
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


# ── STEP 3: MODEL-FOCUSED PREPROCESSING ──────────────────────────────────────
def preprocess_for_model(text):
    """
    Remove noise that hurts TF-IDF quality:
    - Emails, URLs, phone numbers  →  personal info = noise
    - Standalone numbers           →  years/IDs not useful for NB
    - Special characters           →  keep + # . for C++, C#, .NET
    - Lowercase                    →  reduces vocabulary sparsity
    """
    if not isinstance(text, str): return ''
    text = re.sub(r'\S+@\S+', ' ', text)                       # emails
    text = re.sub(r'http\S+|www\S+', ' ', text)                # URLs
    text = re.sub(r'[\+\(]?\d[\d\s\-\(\)]{7,}\d', ' ', text)  # phones
    text = re.sub(r'\b\d+\b', ' ', text)                       # numbers
    text = re.sub(r'[^\w\s+#.]', ' ', text)                    # special chars
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()


# ── STEP 4: DEDUPLICATE SENTENCES ─────────────────────────────────────────────
def dedup_sentences(text):
    """Remove OCR-reprinted duplicate sentences within a resume."""
    if not isinstance(text, str): return ''
    sentences = re.split(r'(?<=[.!?])\s+', text)
    seen = set(); result = []
    for s in sentences:
        key = s.strip().lower()
        if key and key not in seen:
            seen.add(key); result.append(s.strip())
    return ' '.join(result)


# ── STEP 5: EXTRACT SECTIONS ──────────────────────────────────────────────────
def extract_section(text, pat, max_len=800):
    m = re.search(
        rf'(?i)(?:{pat})\s*[:\-]?\s*(.*?)(?=\s+(?:{ALL_SECTIONS})\b|$)',
        text, re.DOTALL
    )
    return re.sub(r'\s+', ' ', m.group(1)).strip()[:max_len] if m else ''


def get_skills(text):
    pat = r'(?:SKILLS?|TECHNICAL\s+SKILLS?|CORE\s+COMPETENCIES|KEY\s+SKILLS?|PROFESSIONAL\s+SKILLS?)'
    raw = extract_section(text, pat, max_len=600)
    if not raw: return ''
    items = re.split(r'[,;|\n]+', raw)
    items = [s.strip().strip('-. ') for s in items if 1 < len(s.strip()) < 80]
    return ' '.join(items)


def get_experience(text):
    pat = r'(?:(?:WORK\s+|PROFESSIONAL\s+)?EXPERIENCE|WORK\s+HISTORY|EMPLOYMENT(?:\s+HISTORY)?|CAREER\s+SUMMARY)'
    return extract_section(text, pat, max_len=1000)


def get_education(text):
    pat = r'(?:EDUCATION(?:\s+AND\s+TRAINING)?|ACADEMIC(?:\s+BACKGROUND)?|QUALIFICATIONS?)'
    return extract_section(text, pat, max_len=600)


# ── STEP 6: BUILD FINAL FEATURE COLUMN ───────────────────────────────────────
def build_final_text(row):
    """
    Combine columns into one rich feature string.

    Weighting strategy (tuned for 43-category dataset):
      skills × 4    — strongest discriminating signal between job types
      experience × 2 — job titles, company context
      education × 1  — degree, field of study
      clean_text × 1 — full resume body

    Skills repetition is the single most impactful change:
    categories that share generic writing (Management, Consultant, Sales)
    differ mainly in listed skills/tools, so boosting skills weight
    gives the TF-IDF model the best chance to separate them.
    """
    t = row['clean_text']
    s = row['clean_skills']
    e = row['clean_exp']
    d = row['clean_edu']
    return f"{t} {s} {s} {s} {s} {e} {e} {d}"


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n  Resume Dataset Preprocessor — Full 43-Category Dataset")
    print("  " + "─" * 50)

    df = load_and_merge(INPUT_FILES)

    print("[2/5] Deep cleaning raw OCR text...")
    df['dc'] = df['raw_text'].apply(deep_clean)

    print("[3/5] Extracting skills / experience / education sections...")
    df['skills']     = df['dc'].apply(get_skills)
    df['experience'] = df['dc'].apply(get_experience)
    df['education']  = df['dc'].apply(get_education)

    print("[4/5] Applying model preprocessing...")
    df['cleaned_text'] = df['dc'].apply(dedup_sentences).apply(preprocess_for_model)
    df['clean_text']   = df['cleaned_text']
    df['clean_skills'] = df['skills'].fillna('').apply(preprocess_for_model)
    df['clean_exp']    = df['experience'].fillna('').apply(preprocess_for_model)
    df['clean_edu']    = df['education'].fillna('').apply(preprocess_for_model)
    df['final_text']   = df.apply(build_final_text, axis=1)

    before = len(df)
    df = df[df['final_text'].str.strip() != ''].reset_index(drop=True)
    print(f"      Dropped {before - len(df)} empty rows → {len(df):,} remaining")

    out_cols = ['category','cleaned_text','clean_text','skills','clean_skills',
                'education','clean_edu','experience','clean_exp','final_text']
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df[out_cols].to_csv(OUTPUT_FILE, index=False)

    print(f"\n[5/5] Saved {len(df):,} rows → {OUTPUT_FILE}")
    print(f"\n  Column stats:")
    print(f"  {'Column':<20} {'Non-null':>10} {'Avg len':>10}")
    print(f"  {'-'*42}")
    for col in out_cols:
        nn  = df[col].notna().sum()
        avg = df[col].fillna('').str.len().mean()
        print(f"  {col:<20} {nn:>10} {avg:>9.0f}")

    print(f"\n  Category distribution:")
    print(df['category'].value_counts().to_string())
    print("\n  Done. Use model_ready_resume.csv as input for the notebook.\n")