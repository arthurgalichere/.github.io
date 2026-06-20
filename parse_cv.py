import os
import json
import re
import pdfplumber

# Direct inline check to prevent execution if heavy dependencies aren't ready
try:
    import torch
    from transformers import pipeline
except ImportError:
    print("Error: torch and transformers libraries are required. Check your workflow file.")
    exit(1)

def extract_json_from_llm_output(output_text):
    """Safely extracts a JSON block from the LLM text response."""
    try:
        # Look for content wrapped between the first '{' and last '}'
        match = re.search(r'\{.*\}', output_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(output_text)
    except Exception as e:
        print(f"Failed to isolate clean JSON structure: {e}")
        return None

def parse_pdf_to_json():
    # 1. Extract completely raw text from your PDF
    print("Extracting raw text matrices from CV PDF...")
    raw_text = ""
    try:
        with pdfplumber.open("website/CV_Arthur_Galichere.pdf") as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
    except Exception as e:
        print(f"Error opening or reading PDF file: {e}")
        return

    # 2. Build the structural engineering prompt
    prompt = f"""
Clean and transform the following messy text extracted from an academic CV into a structured JSON object.

RULES:
1. Fix words squished together by PDF layout issues (e.g., convert 'AssistantProfessor' to 'Assistant Professor', 'UniversityofWarwick' to 'University of Warwick').
2. Drop and completely OMIT general text research blocks, summaries, or abstracts (e.g., 'Research Summary', 'Job Market Paper', 'Working Papers', 'Work in Progress').
3. Keep the 'Research Presentations' / 'Presentations' section, rename it to 'Selected Presentations', and group items neatly by year.
4. Correct institutional misattributions:
   - The 'Warwick Award for Teaching Excellence' (WATE) belongs to the 'University of Warwick'.
   - The 'Fellowship of the Higher Education Academy' belongs to the 'University of Warwick'.
   - The 'Associate Fellowship' / 'DAT HE' belongs to the 'University of Glasgow'.
5. Strip all running page headers, footers, page numbers, and custom icon bullets.

Output ONLY a valid JSON object matching this schema layout:
{{
  "sections": [
    {{
      "title": "Section Title",
      "items": [
        {{
          "role": "Role, award name, or conference title",
          "institution": "University name or blank string if inapplicable",
          "date": "Year or timeline range (e.g., 2024–Present or 2025)",
          "details": "Paragraph description text"
        }}
      ]
    }}
  ]
}}

Raw CV Text:
{raw_text}
"""

    # 3. Initialize the local open-source LLM engine (runs entirely on CPU)
    print("Loading local lightweight AI engine (Qwen2.5-1.5B)...")
    try:
        pipe = pipeline(
            "text-generation",
            model="Qwen/Qwen2.5-1.5B-Instruct",
            torch_dtype=torch.float32, # Force clean float32 for CPU stability
            device_map="cpu"
        )
        
        messages = [
            {"role": "system", "content": "You are a precise data extraction assistant that outputs strictly valid raw JSON without conversational filler or markdown codeblocks."},
            {"role": "user", "content": prompt}
        ]
        
        print("Processing text layout via local AI inference... (This may take 1-2 minutes on CPU)")
        outputs = pipe(messages, max_new_tokens=2048, temperature=0.1, do_sample=False)
        llm_response = outputs[0]["generated_text"][-1]["content"]
        
        # 4. Clean and serialize the output
        final_json = extract_json_from_llm_output(llm_response)
        if final_json:
            with open("website/cv.json", "w", encoding="utf-8") as f:
                json.dump(final_json, f, indent=2, ensure_ascii=False)
            print("Success! cv.json has been accurately compiled locally by open-source AI.")
        else:
            print("Error: The local LLM output could not be parsed into valid JSON.")
            
    except Exception as e:
        print(f"Local AI Pipeline encountered an error: {e}")

if __name__ == "__main__":
    parse_pdf_to_json()
