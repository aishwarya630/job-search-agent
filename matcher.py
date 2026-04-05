import os
import json
import time
import requests
from openai import OpenAI
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- INITIALIZE CLIENTS ---
# NVIDIA uses the OpenAI-compatible library
nv_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY")
)
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def build_prompt(jobs, resume_chunks):
    jobs_text = ""
    for i, job in enumerate(jobs):
        # Catch the bottom of the text where visa info usually hides
        full_description = job.get('description', 'No description available')
        
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
    # Strip potential markdown backticks
    text = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception as e:
        print(f"JSON Parse Error: {e} | Raw Text: {text[:100]}...")
        return []

# --- AI ENGINES ---

def match_with_nvidia(prompt):
    """Tier 1: NVIDIA NIM (Llama 3.1 70B)"""
    print("🚀 Using NVIDIA NIM...")
    response = nv_client.chat.completions.create(
        model="meta/llama-3.1-70b-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2048
    )
    return parse_response(response.choices[0].message.content)

def match_with_groq(prompt):
    """Tier 2: Groq (Llama 3.3 70B)"""
    print("⚡ Falling back to Groq...")
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000
    )
    return parse_response(response.choices[0].message.content)

def match_with_huggingface(prompt):
    """Tier 3: Hugging Face (Emergency Backup)"""
    print("☁️ Falling back to Hugging Face...")
    hf_token = os.environ.get("HF_TOKEN")
    # Using Mistral 7B as it's better at JSON than Llama on HF free tier
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    # HF usually needs shorter input for free tier
    payload = {
        "inputs": f"<s>[INST] {prompt[:4000]} [/INST]",
        "parameters": {"max_new_tokens": 1000, "return_full_text": False}
    }
    
    response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
    result = response.json()
    
    if isinstance(result, list) and "generated_text" in result[0]:
        return parse_response(result[0]["generated_text"])
    elif "choices" in result: # Handle OpenAI-compatible HF endpoints
        return parse_response(result["choices"][0]["message"]["content"])
    
    raise Exception(f"HF Error Response: {result}")

# --- MAIN EXECUTION ---

def match_jobs(jobs, resume_text):
    if not jobs:
        return []

    # Get RAG chunks if available
    try:
        from rag import get_relevant_resume_chunks
        resume_chunks = get_relevant_resume_chunks(
            " ".join([f"{j['title']} {j.get('description','')[:200]}" for j in jobs])
        )
    except Exception as e:
        print(f"RAG failed, using top of resume: {e}")
        resume_chunks = resume_text[:3000]

    prompt = build_prompt(jobs, resume_chunks)

    # The Chain of Fallbacks
    try:
        return match_with_nvidia(prompt)
    except Exception as e_nv:
        print(f"⚠️ NVIDIA failed: {e_nv}")
        try:
            return match_with_groq(prompt)
        except Exception as e_g:
            print(f"⚠️ Groq failed: {e_g}")
            try:
                return match_with_huggingface(prompt)
            except Exception as e_hf:
                print(f"❌ All AI engines failed: {e_hf}")
                return []