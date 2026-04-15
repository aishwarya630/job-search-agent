import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# We only need ONE reliable client for extraction
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def extract_job_data(job_description):
    """
    Step 1: AI as the Parser. 
    It turns messy text into a clean 'Job Contract'.
    """
    prompt = f"""
    Examine the following job description. Extract the requirements into a JSON object.
    Be literal. Do not infer skills that aren't listed.
    
    Required Keys:
    - "role_title": The job title.
    - "tech_stack": A list of specific tools/languages required.
    - "min_years": An integer of required experience (0 if not specified).
    - "seniority": Is it "junior", "mid", or "senior"?
    - "visa_exclusion": Boolean. True if it says 'US Citizen', 'Security Clearance', or 'No Sponsorship'.
    
    JOB TEXT:
    {job_description[:4000]}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Extraction Error: {e}")
        return None

def calculate_score(job_data, my_profile):
    """
    Step 2: Python as the Judge.
    Deterministic math based on your real profile.
    """
    score = 0
    matches = []
    missing = []
    notes = []

    # 1. HARD BLOCK: Visa/Citizenship (The OPT Safety Net)
    if job_data.get('visa_exclusion'):
        return 0, "REJECTED: Visa/Citizenship constraints found.", "", ""

    # 2. Tech Stack Match (Weight: 60%)
    # Flatten all your skills into one list for comparison
    my_all_skills = [s.lower() for sublist in my_profile['skills'].values() for s in sublist]
    job_stack = [s.lower() for s in job_data.get('tech_stack', [])]

    for tool in job_stack:
        if any(my_skill in tool for my_skill in my_all_skills):
            matches.append(tool)
        else:
            missing.append(tool)

    if job_stack:
        score += (len(matches) / len(job_stack)) * 6

    # 3. Experience & Seniority Check (Weight: 40%)
    # 2.5y (TCS) + 0.5y (XNODE) = 3y Total
    if job_data['seniority'] == 'senior' and my_profile['seniority_level'] != 'senior':
        score -= 2 # Penalty for applying to Senior roles as a Mid
        notes.append("Role level (Senior) is above current Mid-level profile.")
    elif job_data['min_years'] <= my_profile['total_years_exp']:
        score += 4
        notes.append("Experience requirements met.")
    else:
        score += 1 # Some points for having related but less experience
        notes.append(f"Minor experience gap (Required: {job_data['min_years']}y)")

    return round(max(0, score), 1), ". ".join(notes), ", ".join(matches), ", ".join(missing[:5])

def match_jobs(jobs, my_profile):
    """
    The main entry point for your pipeline.
    """
    final_results = []
    
    for job in jobs:
        # 1. Get structured data
        job_data = extract_job_data(job.get('description', ''))
        
        if not job_data:
            continue
            
        # 2. Score it
        score, notes, fits, gaps = calculate_score(job_data, my_profile)
        
        # 3. Format for Streamlit/Google Sheets
        final_results.append({
            "title": job['title'],
            "company": job['company'],
            "location": job['location'],
            "apply_url": job['url'],
            "score": score,
            "what_fits": fits,
            "whats_missing": gaps,
            "why_apply": notes,
            "visa_note": "Exclusion Detected" if job_data.get('visa_exclusion') else "Possible OPT Match"
        })
        
    return final_results
