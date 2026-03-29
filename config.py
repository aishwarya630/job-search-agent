from dotenv import load_dotenv
load_dotenv()

RECIPIENT_EMAILS = [
    "aanair4@wisc.edu",
    "aishunair0607@gmail.com",  # add any email here
]
YOUR_NAME = "Aishwarya Aravind Nair"

# Job search preferences
JOB_KEYWORDS = [
    "DevOps engineer",
    "Cloud engineer",
    "Software Engineer",
    "Site reliability engineer",
    "MLOps engineer",
    "AI infrastructure engineer"
]

LOCATIONS = ["United States"]

# Minimum match score to include in email (out of 10)
MIN_SCORE = 6

# How often to run (in hours)
SCHEDULE_INTERVAL_HOURS = 24

# Your resume path
RESUME_PATH = "resume.pdf"