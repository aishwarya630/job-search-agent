import pdfplumber
import re

def extract_resume_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(
                x_tolerance=2,
                y_tolerance=3,
                keep_blank_chars=False
            )
            if words:
                # Reconstruct text from word positions
                line = ""
                prev_y = None
                for word in words:
                    curr_y = round(word['top'], 1)
                    if prev_y is not None and abs(curr_y - prev_y) > 5:
                        text += line.strip() + "\n"
                        line = word['text'] + " "
                    else:
                        line += word['text'] + " "
                    prev_y = curr_y
                text += line.strip() + "\n"
            text += "\n"

    # Clean up
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()

if __name__ == "__main__":
    text = extract_resume_text("resume.pdf")
    print(text)