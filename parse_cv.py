import json
import re
from pypdf import PdfReader

def clean_pdf_artifacts(text):
    """Strips out repetitive PDF noise, page breaks, and icon placeholders."""
    # Remove page lines and headers
    text = re.sub(r'Page\s+\d+', '', text)
    text = re.sub(r'Arthur\s+Galichère\s+Curriculum\s+Vitæ', '', text, flags=re.IGNORECASE)
    
    # Clean font extraction placeholders/ligatures
    text = re.sub(r'􀄤|􀁡|􀈲|􀁦|•', '', text)
    
    # Standardize spaces
    text = re.sub(r'[ \t]+', ' ', text)
    return text

def parse_pdf_to_json():
    try:
        reader = PdfReader("website/CV_Arthur_Galichere.pdf")
    except Exception as e:
        print(f"Error opening PDF context: {e}")
        return

    # Extract raw text data streams
    raw_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            raw_text += text + "\n"

    raw_text = clean_pdf_artifacts(raw_text)

    # Core academic landmarks
    sections_anchors = [
        "EMPLOYMENT",
        "EDUCATION",
        "RESEArCH",
        "JOB MArKET PAPEr",
        "WOrKING PAPEr",
        "WOrK IN PrOGrESS",
        "CONFErENCE PAPEr REVIEWEr",
        "PrOFESSIONAL DEVELOPMENT",
        "TEACHING AWArDS AND QUALIfICATIONS",
        "TEACHING EXPErIENCE",
        "ACADEMIC LEADErSHIP, TEACHING SUPPOrT AND EDUCATIONAL DEVELOPMENT",
        "ADMINISTrATIVE AND COLLEGIAL EXPErIENCE",
        "REFErEES",
        "RESEArCH PrESENTATIONS"
    ]

    # Dynamically split document context based on section headers
    pattern = "|".join([rf"\b{section}\b" for section in sections_anchors])
    splits = re.split(f"({pattern})", raw_text)

    structured_data = {"sections": []}
    
    # Context Processing Engine
    for i in range(1, len(splits), 2):
        raw_title = splits[i].strip()
        # Clean title normalization (e.g. "WOrKING PAPEr" -> "Working Paper")
        clean_title = raw_title.title().replace("Working Paper", "Working Papers").replace("Research Presentations", "Selected Research Presentations")
        
        body = splits[i+1].strip() if (i+1) < len(splits) else ""
        lines = [line.strip() for line in body.split('\n') if line.strip()]
        
        items = []

        # --- Type A: Structural Timelines (Employment, Education, Leadership, Administration) ---
        if clean_title in ["Employment", "Education", "Conference Paper Reviewer", "Professional Development", "Academic Leadership, Teaching Support And Educational Development", "Administrative And Collegial Experience"]:
            current_item = None
            for line in lines:
                # Match standard academic date footprints (e.g., 2024 – PRESENT, 2017 – 2022, 2023)
                date_match = re.search(r'(\b\d{4}\s*–?\s*(?:PrESENT|\d{4})?)$', line, re.IGNORECASE)
                
                if date_match:
                    if current_item:
                        items.append(current_item)
                    date_str = date_match.group(1).strip()
                    role_str = line[:date_match.start()].strip().rstrip(',:-').strip()
                    
                    # Modern styling for known font updates
                    date_str = date_str.lower().replace("present", "Present").replace("present", "Present")
                    
                    current_item = {
                        "role": role_str,
                        "institution": "",
                        "date": date_str,
                        "details": ""
                    }
                elif current_item:
                    # Treat the second line under an appointment as the primary institution
                    if not current_item["institution"]:
                        current_item["institution"] = line
                    else:
                        # Append remaining text lines smoothly as details descriptions
                        current_item["details"] = (current_item["details"] + " " + line).strip()
            if current_item:
                items.append(current_item)

        # --- Type B: Dynamic Research Papers (Job Market, Working Papers, Works in Progress) ---
        elif "Paper" in clean_title or "Progress" in clean_title:
            if lines:
                title_line = lines[0]
                desc_text = " ".join(lines[1:])
                items.append({
                    "role": title_line,
                    "institution": "",
                    "date": "Forthcoming" if "Progress" in clean_title else "Working Abstract",
                    "details": desc_text
                })

        # --- Type C: Teaching Awards and Qualifications ---
        elif "Awards" in clean_title:
            current_award = None
            for line in lines:
                if ":" in line and any(yr in line for yr in ["2025", "2024", "2023", "2021", "2019"]):
                    if current_award:
                        items.append(current_award)
                    title_part, date_part = line.split(",", 1) if "," in line else (line, "")
                    current_award = {
                        "role": title_part.strip().rstrip(':'),
                        "institution": "University of Warwick" if "Warwick" in line or "Wate" in line.lower() else "University of Glasgow",
                        "date": re.sub(r'[^0-9–]', '', date_part),
                        "details": ""
                    }
                elif current_award:
                    current_award["details"] = (current_award["details"] + " " + line).strip()
            if current_award:
                items.append(current_award)

        # --- Type D: Chronological Presentations Tracker ---
        elif "Presentations" in clean_title:
            current_year = ""
            for line in lines:
                if re.match(r'^\d{4}$', line):
                    current_year = line
                elif current_year:
                    items.append({
                        "role": line,
                        "institution": "Speaker / Presenter",
                        "date": current_year,
                        "details": ""
                    })

        # --- Type E: Structural Lists / General Contexts (Research Paragraphs & Teaching Lists) ---
        else:
            # Fallback layout blocks to preserve raw sentences safely
            full_paragraph = " ".join(lines)
            if "Referees" not in clean_title: # Keep text professional, skip explicit display of private phone strings
                items.append({
                    "role": clean_title,
                    "institution": "",
                    "date": "",
                    "details": full_paragraph
                })

        if items:
            structured_data["sections"].append({
                "title": clean_title,
                "items": items
            })

    # Output verified tree nodes
    with open("website/cv.json", "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    print("cv.json compiled and generated successfully from standard structural arrays.")

if __name__ == "__main__":
    parse_pdf_to_json()
