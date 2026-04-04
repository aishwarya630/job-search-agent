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
        # Increased from 800 to 5000 to ensure we catch the bottom of the text
        full_description = job.get('description', 'No description available')
        
        # If the description is massive, we take the start AND the end 
        # (Where the visa/citizenship info usually hides)
        if len(full_description) > 6000:
            desc_sample = full_description[:3000] + "\n[...]\n" + full_description[-2000:]
        else:
            desc_sample = full_description

        jobs_text += f"""
JOB {i+1}:
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
URL: {job['apply_url']}
Description: {desc_sample}
---
"""

    return f"""You are a strict job matching assistant for an international student on OPT visa in the US.

Candidate resume highlights:
{resume_chunks}

REAL JOB LISTINGS — score ONLY these {len(jobs)} jobs, never invent others:
{jobs_text}

HARD EXCLUSION RULES — immediately discard any job with:
- "security clearance", "TS/SCI", "polygraph", "US citizen only", "no sponsorship"
- "5+ years", "6+ years", "7+ years", "10+ years" experience required
- Embedded systems, hardware, robotics, electrical engineering — NOT relevant
- Part-time, contract-to-hire, gig work
- federal government client 

RELEVANCE CHECK — only include jobs that are clearly in:
- DevOps, Cloud, SRE, Platform Engineering, MLOps, AI Infrastructure
- Software Engineering roles requiring Python + Cloud skills
- Discard anything that doesn't match candidate's background

SCORING — be honest and strict:
- 9-10: 80%+ of required skills explicitly in resume, strong match
- 7-8: 60-80% match, clear overlap
- 6: 40-60% match, worth a stretch application
- Below 6: EXCLUDE entirely

FOR whats_missing — be VERY specific:
- List exact tools/technologies mentioned as REQUIRED in the job description that are NOT in the resume
- Example: "Go language, Rancher, IBM Cloud Pak" not "specific experience with certain technologies"
- If job description is vague or missing, write "job description insufficient to determine gaps"

FOR what_fits — list specific skills from the resume that directly match job requirements

FOR why_apply — give one concrete reason based on the actual job description, not generic

Return JSON array for ONLY relevant jobs scoring 6+:
[
  {{
    "title": "exact title",
    "company": "exact company",
    "location": "exact location",
    "apply_url": "exact url",
    "score": 7,
    "what_fits": "specific matching skills",
    "whats_missing": "specific required skills NOT in resume",
    "why_apply": "specific reason from job description",
    "visa_note": "exact sponsorship text or not mentioned"
  }}
]

Return ONLY valid JSON. No markdown. No extra text.
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
