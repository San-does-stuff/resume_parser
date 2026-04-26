# Resume Parser Project - Full System Guide

## 1) Project Purpose

This project is a Django web application that:

- Accepts resume PDF uploads
- Extracts text and structured information (skills, experience, education)
- Predicts a job category/title from resume content using an ML model
- Scrapes live jobs from multiple company/job APIs and pages
- Recommends jobs to logged-in users based on their latest predicted category
- Provides a dashboard with recommendation stats and available jobs

---

## 2) High-Level Architecture

Main Django apps:

- `core` - home page and top-level UI state wiring
- `resume` - resume data model, upload, text extraction, ML prediction
- `users` - custom user model and authentication flow (register/login/logout)
- `jobs` - job storage, scraping sync, recommendation generation, dashboard view

Key flow:

1. User uploads resume
2. System parses text + predicts category
3. On dashboard visit, job scrapers run and DB is synced (insert/update only)
4. Recommended jobs are computed from latest predicted category
5. Dashboard shows both recommended jobs and all jobs

---

## 3) Directory and File Responsibilities

### `manage.py`
Entry point for Django commands (`runserver`, `migrate`, `makemigrations`, etc.).

### `resume_parser/settings.py`
Global Django settings:

- Installed apps (`core`, `resume`, `users`, `jobs`)
- DB configuration (PostgreSQL via environment variables)
- Static and media file configuration
- Custom auth user model: `AUTH_USER_MODEL = 'users.Users'`

### `resume_parser/urls.py`
Root URL router that includes app-level URLs.

### `core/views.py`
Home page logic.
Builds initial UI state for:

- extracted resume data
- prediction data
- latest resume URL

For authenticated users, it reads latest `Resume` and related `Experience` and `Education`.
For guests, it can use session-stored temporary state.

### `resume/models.py`
Main resume data structures:

- `Resume`: uploaded file, raw text, predicted category, confidence
- `Experience`: normalized experience rows tied to a resume
- `Education`: normalized education rows tied to a resume

### `resume/views.py` (and services/ml modules)
Handles resume upload and prediction pipeline:

- parses PDF text via `resume/services/pdf_parser.py`
- preprocesses text
- predicts category via trained Naive Bayes model (`resume/ml/*`)
- stores prediction on `Resume`

### `resume/ml/*`
Machine learning tooling:

- `naive_bayes.py`: custom Naive Bayes implementation
- `train_model.py`: training and evaluation script
- `predictor.py`: runtime model loading + prediction helper
- `clean_dataset.py` and `dataset_audit.py`: dataset hygiene/diagnostics
- `augment_dataset_with_jobs.py`: augments training dataset with scraped job-derived resume-style rows plus curated IT role seed profiles (QA, Project Manager, DevOps, etc.)

### `users/models.py`
Custom user model (`Users`) used across the project.

### `users/views.py`
Authentication lifecycle:

- `register_view`
- `login_view`
- `logout_view`

Also links guest-uploaded resumes to the user account after login/register.

### `jobs/models.py`
Job and recommendation domain:

- `JobCategory`
- `Company`
- `Job`
- `Recommendation`

New sync-safe fields in `Job`:

- `source`, `source_job_id` (unique together)
- `source_url`
- `description`
- `content_hash`
- `last_synced_at`

### `jobs/scraping_scripts/*`
Per-source scripts that fetch jobs and write source JSON files:

- `merojob.py`
- `cedar_json.py`
- `proshore_json.py`
- `verisk_json.py`

Each script has source-specific parsing logic and output shape.

### `jobs/services.py`
Central integration layer for scraping and syncing:

- runs all scraper scripts
- reads generated JSON outputs
- normalizes field differences into one internal schema
- upserts records into DB:
  - new jobs -> insert
  - changed jobs -> update (detected via `content_hash`)
  - unchanged jobs -> skip

Also contains recommendation query helper:

- `get_recommended_jobs_for_prediction(predicted_title)`

### `jobs/views.py`
Dashboard recommendation endpoint:

- runs scraping sync each time dashboard opens
- finds latest user resume prediction
- fetches recommended jobs
- ensures `Recommendation` rows exist
- sends both `jobs` (recommended) and `all_jobs` to template

### `templates/jobs/recommendations.html`
User dashboard page:

- profile and resume/prediction summary
- recommendation statistics
- job cards
- toggle button UI for:
  - Recommended Jobs
  - All Jobs

---

## 4) Database Design and Relationships

Main entity relationships:

- One `Users` can have many `Resume`
- One `Resume` can have many `Experience` and `Education`
- One `Job` belongs to one `JobCategory` and one `Company`
- One `Recommendation` links one `Users` to one `Job`

Scraping identity and dedup logic:

- Uniqueness key: (`source`, `source_job_id`)
- This prevents duplicate insertions for the same source job over multiple runs.
- If job content changes, `content_hash` changes and row is updated.

---

## 5) End-to-End Workflow

## A. Resume Upload + Prediction

1. User uploads resume PDF.
2. System extracts text.
3. System predicts category/title from ML model.
4. `Resume` row stores:
   - `predicted_category`
   - `confidence_score`

## B. Login + Dashboard

1. User logs in.
2. User is redirected to recommendations page.
3. `jobs/views.recommended_jobs` triggers scraping sync.
4. Source scripts run and output JSON.
5. Sync service normalizes and upserts jobs.
6. Recommended jobs are queried by predicted category/title match.
7. Page renders recommended and all jobs.

## C. Recommendation Matching Details

When recommendations are computed, the system matches the latest predicted category/title against:

- `Job.jobTitle`
- `Job.category.categoryName`
- `Job.requiredSkill`
- `Job.description`

Matching logic:

1. Direct contains/exact checks with full predicted title.
2. Token-level fuzzy checks (split predicted title into meaningful tokens).
3. A job is recommended if it satisfies either direct or token query.
4. Dashboard displays per-job "Why recommended" reasons from these matched fields.

---

## 6) Why Job Count Can Be Low

The total job count in DB is the sum of currently successful scraper sources.
If any scraper fails (dependency issue, API change, timeout, selector break), those jobs are not inserted.

Example current behavior:

- `cedar` and `verisk` succeed
- `merojob` and `proshore` fail
- Result: only jobs from two sources are visible

---

## 7) Migrations and Schema Evolution

When models are changed, this project uses standard Django migration flow:

1. `manage.py makemigrations`
2. `manage.py migrate`

If code references a new field before migration is applied, DB errors occur (e.g., missing column).

---

## 8) Operational Notes

- Scraping is currently triggered on dashboard load.
- This ensures fresh jobs but can increase response time.
- Scraper failures are isolated per source (one failure does not stop all sources).
- Frontend currently uses server-rendered templates and a small inline JS toggle for job list views.

---

## 9) Suggested Improvements (Optional Next Phase)

- Move scraping to background scheduler (Celery/cron) instead of request cycle
- Add per-source health and last-run status model for visibility
- Add pagination on All Jobs
- Add richer matching logic (skills + title + semantic similarity)
- Add automated tests for job normalization and upsert logic

---

## 10) Quick Command Reference

Use project virtual environment python:

- Run server:
  - `env/bin/python manage.py runserver`
- Apply migrations:
  - `env/bin/python manage.py migrate`
- Create migrations:
  - `env/bin/python manage.py makemigrations`
- Check project health:
  - `env/bin/python manage.py check`

Retrain with enhanced IT-focused data:

- Build enhanced dataset from scraped jobs + curated IT resume seeds:
  - `env/bin/python -m resume.ml.augment_dataset_with_jobs --base-path datasets/structured_resume_dataset.csv --output-path datasets/structured_resume_dataset.enhanced.csv`
- Clean enhanced dataset:
  - `env/bin/python -m resume.ml.clean_dataset --input-path datasets/structured_resume_dataset.enhanced.csv --output-path datasets/structured_resume_dataset.enhanced.cleaned.csv`
- Retrain model:
  - `env/bin/python -m resume.ml.train_model --dataset-path datasets/structured_resume_dataset.enhanced.csv --cleaned-dataset-path datasets/structured_resume_dataset.enhanced.cleaned.csv --model-output-path media/models/naive_bayes_model.pkl --metrics-output-path media/models/model_metrics.json`

