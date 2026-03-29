import pandas as pd
import re
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_FILES = [
    r'C:\Users\apeks\OneDrive\Desktop\Seventh\Project\resume_parser\datasets\rawsplit_files\resume_part_1.csv',
    r'C:\Users\apeks\OneDrive\Desktop\Seventh\Project\resume_parser\datasets\rawsplit_files\resume_part_2.csv',
    r'C:\Users\apeks\OneDrive\Desktop\Seventh\Project\resume_parser\datasets\rawsplit_files\resume_part_3.csv',
]
OUTPUT_FILE = r'C:\Users\apeks\OneDrive\Desktop\Seventh\Project\resume_parser\datasets\processed\cleaned_resume_all.csv'

# ── 1. LOAD & MERGE ───────────────────────────────────────────────────────────
def load_and_merge(file_paths):
    dfs = []
    for path in file_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Input file not found: {path}")
        df = pd.read_csv(path)
        dfs.append(df)
    merged = pd.concat(dfs, ignore_index=True)
    merged.columns = ['category', 'raw_text']
    # Drop embedded header rows
    merged = merged[merged['category'] != 'Category'].reset_index(drop=True)
    print(f"[1/4] Loaded & merged {len(merged)} rows from {len(file_paths)} files.")
    return merged


# ── 2. DEEP CLEAN ─────────────────────────────────────────────────────────────
def deep_clean(text):
    if not isinstance(text, str):
        return ''
    # Normalize line endings
    text = text.replace('\\r\\n', ' ').replace('\\r', ' ').replace('\\n', ' ')
    text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
    # Remove leading OCR artifacts: ?___ or ?   sequences
    text = re.sub(r'^\?[_\s]*', '', text)
    text = re.sub(r'\?[_]{3,}', ' ', text)
    # Remove placeholder tokens e.g. [Number], [Software], [Type], [Job title]
    text = re.sub(r'\[[\w\s/]+\]', '', text)
    # Remove non-informative symbols and bullets
    text = re.sub(r'[•●○◦►▪■□✓✔✗×°¿¡©®™€£¥…]+', ' ', text)
    # Collapse repeated ellipsis artifacts
    text = re.sub(r'\.{2,}', ' ', text)
    # Remove stray single non-alphanumeric characters surrounded by spaces
    text = re.sub(r'\s[^a-zA-Z0-9]\s', ' ', text)
    # Normalize all whitespace
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def apply_cleaning(df):
    df['cleaned_text'] = df['raw_text'].apply(deep_clean)
    print(f"[2/4] Deep clean complete. Nulls remaining: {df['cleaned_text'].eq('').sum()}")
    return df


# ── 3. REGEX SECTION EXTRACTION ───────────────────────────────────────────────

# Patterns for each target section header
SECTION_HEADERS = {
    'skills': (
        r'(?:SKILLS?'
        r'|TECHNICAL\s+SKILLS?'
        r'|SKILLS?\s*(?:&|AND)\s*OTHER'
        r'|CORE\s+COMPETENCIES'
        r'|KEY\s+SKILLS?'
        r'|PROFESSIONAL\s+SKILLS?)'
    ),
    'education': (
        r'(?:EDUCATION(?:\s+AND\s+TRAINING)?'
        r'|ACADEMIC(?:\s+BACKGROUND)?'
        r'|QUALIFICATIONS?)'
    ),
    'experience': (
        r'(?:(?:WORK\s+|PROFESSIONAL\s+)?EXPERIENCE'
        r'|WORK\s+HISTORY'
        r'|EMPLOYMENT(?:\s+HISTORY)?'
        r'|CAREER\s+SUMMARY)'
    ),
}

# Combined pattern of all section headers (used as lookahead boundary)
ALL_SECTIONS = r'(?:' + '|'.join(SECTION_HEADERS.values()) + r')'


def extract_section_text(text, key):
    """Extract raw text block belonging to the given section key."""
    pat = SECTION_HEADERS[key]
    match = re.search(
        rf'(?i)(?:{pat})\s*[:\-]?\s*(.*?)(?=\s+(?:{ALL_SECTIONS})\b|$)',
        text,
        re.DOTALL,
    )
    if match:
        return re.sub(r'\s+', ' ', match.group(1)).strip()
    return ''


def extract_skills(text):
    """Return skills as a pipe-separated list."""
    raw = extract_section_text(text, 'skills')
    if not raw:
        return ''
    items = re.split(r'[,;|\n]+', raw)
    items = [s.strip().strip('-. ') for s in items if s.strip()]
    # Keep only short items — long strings are likely sentences, not skill names
    items = [s for s in items if 1 < len(s) < 80]
    return ' | '.join(items)


def extract_education(text):
    """Return education section text, truncated to 500 chars."""
    return extract_section_text(text, 'education')[:500]


def extract_experience(text):
    """Return experience section text, truncated to 800 chars."""
    return extract_section_text(text, 'experience')[:800]


def apply_extraction(df):
    df['skills']     = df['cleaned_text'].apply(extract_skills)
    df['education']  = df['cleaned_text'].apply(extract_education)
    df['experience'] = df['cleaned_text'].apply(extract_experience)

    print(f"[3/4] Extraction complete:")
    print(f"      Skills extracted:     {(df['skills'] != '').sum()} / {len(df)}")
    print(f"      Education extracted:  {(df['education'] != '').sum()} / {len(df)}")
    print(f"      Experience extracted: {(df['experience'] != '').sum()} / {len(df)}")
    return df


# ── 4. SAVE OUTPUT ────────────────────────────────────────────────────────────
def save_output(df, output_path):
    final = df[['category', 'cleaned_text', 'skills', 'education', 'experience']]
    final.to_csv(output_path, index=False)
    print(f"[4/4] Saved {len(final)} rows → {output_path}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    df = load_and_merge(INPUT_FILES)
    df = apply_cleaning(df)
    df = apply_extraction(df)
    save_output(df, OUTPUT_FILE)
    print("\nDone.")