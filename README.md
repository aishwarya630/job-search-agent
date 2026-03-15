# Job Search Agent

I got tired of refreshing LinkedIn. By the time I'd filter results and figure out which roles actually fit my background, the posting already had 50+ applicants. Early applicants get more recruiter attention — so I built a pipeline that runs every 15 minutes, scores job postings against my resume, and emails me only the ones worth applying to.

---

## How it works

```
GitHub Actions (every 15 min)
    ↓
Scraper → fetches public job pages, returns structured dicts
    ↓
Deduplicator → drops anything already seen
    ↓
RAG → retrieves relevant resume sections for this job batch
    ↓
LLM → scores each real job (Groq → HuggingFace fallback)
    ↓
Email → ranked matches with fit/gap breakdown
```

The scraper and the LLM are completely separate steps. Early versions sent raw HTML to the LLM and asked it to find and score jobs — it invented IBM, Airbnb, and Palantir roles that weren't in the results. Splitting the steps fixes that. The LLM gets a list of real job dicts and scores only those — hallucination isn't possible when the input is already structured.

---

## Why these specific tools

**FAISS over a hosted vector DB.** Runs locally, no account or API key needed. For a single resume it's faster than anything cloud-hosted. Pinecone would've added network latency and another secret to manage for no real gain.

**Hybrid search (FAISS + BM25).** Pure semantic search misses exact keyword matches. If a job requires "Terraform" and my resume says "infrastructure provisioning automation," the semantic score comes back low. BM25 catches those exact matches. Running both and combining results gives better retrieval than either alone.

**RAG instead of full resume per prompt.** My resume is ~800 tokens. With 6 keyword searches running in parallel and Groq's 100K daily free token cap, sending the full thing every time burns through the budget in a few hours. RAG cuts each call to ~200 tokens by pulling only the resume sections relevant to the current job batch.

**Groq → HuggingFace fallback.** Free tier rate limits are real constraints. When Groq hits its daily cap the system falls back to HuggingFace Mistral automatically. I didn't add DeepSeek as a fallback — wasn't comfortable sending resume data there.

**GitHub Actions for scheduling.** A local scheduler works but requires the laptop to be on. GitHub Actions runs in the cloud on a cron schedule, commits the tracker state back to the repo after each run (no database needed), and keeps a run history I can check if something looks wrong.

---

## Architecture diagram

```
┌────────────────────────────────────────────┐
│           GitHub Actions cron              │
│           (every 15 minutes)               │
└───────────────────┬────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│              jobsearch.py                  │
│    httpx requests → HTML parsing → dicts  │
│    Filters by posting time (past 30 min)   │
└───────────────────┬────────────────────────┘
                    │ list of job dicts
                    ▼
┌────────────────────────────────────────────┐
│               tracker.py                  │
│    Drops already-seen URLs                 │
│    Auto-cleans entries older than 7 days   │
└───────────────────┬────────────────────────┘
                    │ only new jobs
                    ▼
┌────────────────────────────────────────────┐
│                 rag.py                     │
│    FAISS index built from resume chunks    │
│    BGE embeddings (BAAI/bge-small-en-v1.5) │
│    BM25 keyword search                     │
│    Hybrid retrieval → ~200 relevant tokens │
└───────────────────┬────────────────────────┘
                    │ targeted resume context
                    ▼
┌────────────────────────────────────────────┐
│              matcher.py                   │
│    Groq LLaMA-3.3-70B (primary)           │
│    HuggingFace Mistral-7B (fallback)       │
│    Scores only provided jobs — no          │
│    hallucination possible                  │
└───────────────────┬────────────────────────┘
                    │ scored + filtered list
                    ▼
┌────────────────────────────────────────────┐
│           skill_tracker.py                │
│    Counts missing skills across runs       │
│    Flags anything appearing 5+ times       │
└───────────────────┬────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│               emailer.py                  │
│    HTML digest — top matches get full      │
│    detail, lower matches get a table       │
│    Includes skill gap recommendations      │
└────────────────────────────────────────────┘
```

---

## Stack

| Component | Tool | Why |
|---|---|---|
| HTTP | httpx | Lightweight, async-capable |
| Embeddings | BAAI/bge-small-en-v1.5 | Top MTEB benchmark, runs locally |
| Vector search | FAISS | Meta-developed, fastest local option |
| Keyword search | rank-bm25 | Exact skill matching |
| Primary LLM | Groq LLaMA-3.3-70B | Free, fast, good JSON output |
| Fallback LLM | HuggingFace Mistral-7B | Free inference API |
| Email | Gmail SMTP | Free, no external service |
| Scheduling | GitHub Actions | Cloud-hosted, free tier |
| PDF parsing | pdfplumber | Word-position-aware, better than PyPDF2 |

Everything here runs on free tiers.

---

## Project structure

```
job-search-agent/
├── .github/workflows/job_alert.yml  # cron schedule + secrets injection
├── config.py                        # keywords, emails, preferences
├── emailer.py                       # HTML formatting and SMTP
├── jobsearch.py                     # scraper — no AI in this file
├── main.py                          # parallel orchestration
├── matcher.py                       # LLM scoring, fallback chain
├── rag.py                           # FAISS + BM25 hybrid retrieval
├── resume.py                        # PDF text extraction
├── skill_tracker.py                 # skill gap analysis over time
├── tracker.py                       # deduplication state
├── seen_jobs.json                   # auto-committed after each run
├── skill_gaps.json                  # auto-committed after each run
└── requirements.txt
```

---

## Setup

You need Python 3.11+, a free Groq API key (console.groq.com), a HuggingFace token (huggingface.co), and a Gmail App Password.

```bash
git clone https://github.com/yourusername/job-search-agent
cd job-search-agent
pip install -r requirements.txt
```

Create `.env`:
```
GROQ_API_KEY=...
HF_TOKEN=...
SMTP_USER=yourgmail@gmail.com
SMTP_PASSWORD=your_16_char_app_password
```

Build the resume index:
```bash
python -c "from rag import build_resume_index; build_resume_index()"
```

Test it:
```bash
python main.py
```

For GitHub Actions: push the repo, add the four secrets under Settings → Secrets → Actions. The workflow picks up automatically.

Keep the repo private if your resume is in it.

---

## On scraping and LinkedIn's ToS

This hits publicly available job search pages — the same ones Google indexes. No login, no private data, no automation of applications. The *hiQ Labs v. LinkedIn* ruling (9th Circuit, 2022) found that scraping publicly available data doesn't violate the Computer Fraud and Abuse Act. This is personal, non-commercial use.

That said — LinkedIn has been tightening their public endpoints. Some runs return empty results. The next version of this will scrape **Google Jobs** instead, which aggregates LinkedIn, Indeed, Glassdoor, and company career pages in one place. Broader coverage, more stable to scrape. That's the direction this is heading.

---

## What the skill tracker caught

After a week of runs, GCP (Cloud Run, GKE) kept appearing as a gap. That's on the learning list. The tracker has been more useful than I expected for surfacing patterns I wasn't noticing manually.

---

## What I'd change

The chunking strategy for the resume index could be better. Right now it splits by section headers, but some experience bullets are long enough that a single chunk loses context from the role title. Sentence-level chunking with a sliding window would fix this. It's a small change with a noticeable impact on retrieval quality.

---

*Aishwarya Aravind Nair — MS Information, University of Wisconsin-Madison*
