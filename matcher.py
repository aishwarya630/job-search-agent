from dotenv import load_dotenv
load_dotenv()

import os
import json
from google import genai
from groq import Groq

gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def build_prompt(jobs_text, resume_text):
    return f"""You are a job matching assistant helping an international student on OPT visa in the US.

Here is the candidate's resume:
{resume_text[:2000]}

Here are the job listings with full descriptions:
{jobs_text[:4000]}

LOCATION RULES:
- Include all US locations — candidate is open to relocation anywhere in the US
- Include remote, hybrid and onsite roles
- Only exclude jobs outside the US

STRICT EXCLUSION RULES — discard any job that mentions:
- "security clearance", "TS/SCI", "polygraph"
- "US citizen only", "must be authorized to work", "no sponsorship"
- "5+ years", "7+ years", "10+ years" of experience required
- part-time, contract-to-hire, gig work

SCORING RULES:
- Score based on how well the candidate's resume matches the job requirements
- 9-10: Strong match, most required skills present
- 7-8: Good match, minor gaps
- 6: Decent match, some gaps but worth applying
- Below 6: Do not include

For each suitable job return a JSON array:
[
  {{
    "title": "job title",
    "company": "company name",
    "location": "location",
    "apply_url": "url",
    "score": 7,
    "what_fits": "specific skills from the candidate resume that match the job requirements",
    "whats_missing": "specific skills or tools listed as REQUIRED in the job description that are NOT in the candidate resume — be specific e.g. 'Java, Go, Rancher' not vague",
    "why_apply": "one specific reason based on the job description, not generic",
    "visa_note": "copy exact text from job posting about sponsorship/OPT/citizenship if mentioned, else write 'not mentioned'"
  }}
]

Only include jobs scoring 6 or above.
Return ONLY valid JSON array, no extra text, no markdown backticks.
"""

def parse_response(text):
    text = text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)

def match_with_gemini(prompt):
    print("Trying Gemini...")
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return parse_response(response.text)

def match_with_groq(prompt):
    import time
    time.sleep(3)  # avoid Groq rate limiting
    print("Trying Groq...")
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000  # add this to ensure full response
    )
    text = response.choices[0].message.content
    print(f"  Groq matched {len(json.loads(text.strip().replace('```json','').replace('```','')))} jobs")    
    return parse_response(text)

def match_jobs(jobs_text, resume_text):
    prompt = build_prompt(jobs_text, resume_text)
    try:
        return match_with_groq(prompt)
    except Exception as e:
        print(f"Groq failed: {e}")
        return []