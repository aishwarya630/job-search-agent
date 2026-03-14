import pdfplumber

def extract_resume_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text.strip()

if __name__ == "__main__":
    text = extract_resume_text("resume.pdf")
    print(text[:500])