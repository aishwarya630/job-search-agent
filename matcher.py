from dotenv import load_dotenv
load_dotenv()

import os
import json
import time
import requests
from groq import Groq

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def build_prompt(jobs, resume_chunks):
    jobs_text = ""
    for i, job in enumerate(jobs):
        jobs_text += f"""
JOB {i+1}:
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
URL: {job['apply_url']}
Description: {job.get('description', 'No description available')[:800]}
---
"""
    return f"""You are a job matching assistant for an international student on OPT visa.

Relevant resume sections:
{resume_chunks}

REAL JOB LISTINGS (score ONLY these {len(jobs)} jobs, do not add or invent any others):
{jobs_text}

EXCLUSION RULES:
- EXCLUDE: "security clearance", "TS/SCI", "US citizen only", "no sponsorship", "5+ years", "7+ years"
- EXCLUDE: part-time, contract-to-hire, outside USA

LOCATION RULES:
- Include all US locations, candidate is open to relocation anywhere in the US
- Include remote, hybrid and onsite roles

SCORING (be strict and honest):
- 9-10: 80%+ required skills present in resume
- 7-8: 60-80% match
- 6: 40-60% match, stretch role
- Below 6: exclude

Return a JSON array scoring ONLY the {len(jobs)} jobs listed above.
Do NOT add any jobs not in this list.
[
  {{
    "title": "exact title from job listing",
    "company": "exact company from job listing",
    "location": "exact location from job listing",
    "apply_url": "exact url from job listing",
    "score": 7,
    "what_fits": "specific matching skills from resume",
    "whats_missing": "specific required skills NOT in resume",
    "why_apply": "one specific reason from job description",
    "visa_note": "exact sponsorship text or not mentioned"
  }}
]

Return ONLY valid JSON array. No extra text. No markdown.
"""

def parse_response(text):
    text = text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)

def match_with_groq(prompt):
    time.sleep(2)
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000
    )
    return parse_response(response.choices[0].message.content)

def match_with_huggingface(prompt):
    print("Trying HuggingFace fallback...")
    hf_token = os.environ.get("HF_TOKEN", "")
    API_URL = "https://router.huggingface.co/hf-inference/models/mistralai/Mistral-7B-Instruct-v0.3/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistralai/Mistral-7B-Instruct-v0.3",
        "messages": [{"role": "user", "content": prompt[:3000]}],
        "max_tokens": 2000,
        "temperature": 0.3
    }
    response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    result = response.json()
    if "choices" in result:
        text = result["choices"][0]["message"]["content"]
        return parse_response(text)
    raise Exception(f"HF error: {result}")

def match_jobs(jobs, resume_text):
    if not jobs:
        return []

    try:
        from rag import get_relevant_resume_chunks
        resume_chunks = get_relevant_resume_chunks(
            " ".join([f"{j['title']} {j.get('description','')[:200]}" for j in jobs])
        )
    except Exception as e:
        print(f"RAG failed, using full resume: {e}")
        resume_chunks = resume_text[:2000]

    prompt = build_prompt(jobs, resume_chunks)

    try:
        return match_with_groq(prompt)
    except Exception as e:
        print(f"Groq failed: {e}")
        try:
            return match_with_huggingface(prompt)
        except Exception as e2:
            print(f"HuggingFace failed: {e2}")
            return []