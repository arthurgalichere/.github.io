import json
import re
import pdfplumber

def fix_known_squished_words(text):
    """Manually repairs specific LaTeX compilation glitches without an AI key."""
    replacements = {
        "AssetPriceBubblesandMacroeconomicPolicies": "Asset Price Bubbles and Macroeconomic Policies",
        "WhenBanksRidetheBubble:": "When Banks Ride the Bubble:",
        "FinancialStabilityandRealActivity": "Financial Stability and Real Activity",
        "StockMarketBubblesandMonetarypolicy:": "Stock Market Bubbles and Monetary Policy:",
        "aBayesianAnalysis": "a Bayesian Analysis",
        "WOrK IN PrOGrESS": "Work In Progress",
        "WOrKING PAPEr": "Working Paper",
        "JOB MArKET PAPEr": "Job Market Paper",
        "MainTeachingInterests:": "Main Teaching Interests: ",
        "UNIVErSITY OF W ArWICK": "UNIVERSITY OF WARWICK",
        "UNIVErSITY OF GLASGOW": "UNIVERSITY OF GLASGOW",
        "PrESENT": "Present"
    }
    for squished, fixed in replacements.items():
        text = text.replace(squished, fixed)
    return text

def parse_pdf_to_json():
    structured_data = {"sections": []}
    raw_lines = []

    # 1. Read the PDF using default spacing metrics (fixes the "No Spaces" bug)
    try:
        with pdfplumber.open("website/CV_Arthur_Galichere.pdf") as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text = fix_known_squished_words(text)
                    for line in text.split("\n"):
                        clean_line = line.strip()
                        if clean_line:
                            # Skip running page headers/footers
                            if re.search(r'(?i)Page\s+\d+', clean_line): continue
                            if re.search(r'(?i)Arthur\s+Galichère', clean_line): continue
                            if "Curriculum Vitae" in clean_line or "Curriculum Vitæ" in clean_line: continue
                            raw_lines.append(clean_line)
    except Exception as e:
        print(f"Error reading PDF layout: {e}")
        return

    # 2. Section Map & Skip Rules
    section_map = {
        "EMPLOYMENT": "Employment",
        "EDUCATION": "Education",
        "TEACHING AWARDS AND QUALIFICATIONS": "Teaching Awards & Qualifications",
        "TEACHING AWArDS AND QUALIfICATIONS": "Teaching Awards & Qualifications",
        "TEACHING EXPERIENCE": "Teaching Experience",
        "TEACHING EXPErIENCE": "Teaching Experience",
        "ACADEMIC LEADERSHIP, TEACHING SUPPORT AND EDUCATIONAL DEVELOPMENT": "Academic Leadership & Development",
        "ACADEMIC LEADErSHIP, TEACHING SUPPOrT AND EDUCATIONAL DEVELOPMENT": "Academic Leadership & Development",
        "REFEREES": "Referees",
        "REFErEES": "Referees",
        "RESEARCH PRESENTATIONS": "Selected Presentations",
        "RESEArCH PrESENTATIONS": "Selected Presentations",
        "PRESENTATIONS": "Selected Presentations"
    }
    
    # Sections to drop entirely because they have their own web tab
    skip_sections = ["RESEARCH", "RESEArCH", "JOB MARKET PAPER", "JOB MArKET PAPEr", "WORKING PAPER", "WOrKING PAPEr", "WORK IN PROGRESS", "WOrK IN PrOGrESS"]

    current_section = None
    section_data = {"title": "", "items": []}

    # 3. Main Processing Loop
    for line in raw_lines:
        normalized_line = line.upper().replace("  ", " ")
        
        # Check if line marks a section transition
        is_header = False
        for anchor, clean_title in section_map.items():
            if normalized_line.startswith(anchor):
                if current_section and section_data["items"]:
                    structured_data["sections"].append(section_data)
                current_section = clean_title
                section_data = {"title": current_section, "items": []}
                is_header = True
                break
                
        if is_header: continue

        for skip_anchor in skip_sections:
            if normalized_line.startswith(skip_anchor):
                if current_section and section_data["items"]:
                    structured_data["sections"].append(section_data)
                current_section = "SKIP"
                is_header = True
                break
                
        if is_header or current_section == "SKIP" or not current_section: continue

        # --- MODE A: Timelines (Employment, Education, Leadership) ---
        if current_section in ["Employment", "Education", "Academic Leadership & Development"]:
            date_match = re.search(r'(\b\d{4}\s*[-–]\s*(?:Present|\d{4})?)$', line)
            if date_match:
                date_str = date_match.group(1).strip()
                role_str = line[:date_match.start()].strip().rstrip(',:-').strip()
                
                inst_str = "University of Warwick" if "Warwick" in role_str or "Warwick" in line else ""
                if "Glasgow" in role_str or "Glasgow" in line: inst_str = "University of Glasgow"
                if "Caen" in role_str or "Caen" in line: inst_str = "University of Caen, France"

                section_data["items"].append({
                    "role": role_str,
                    "institution": inst_str,
                    "date": date_str,
                    "details": ""
                })
            elif section_data["items"]:
                last_item = section_data["items"][-1]
                if "University of" in line or "University of Caen" in line:
                    last_item["institution"] = line
                else:
                    last_item["details"] = (last_item["details"] + " " + line).strip()

        # --- MODE B: Hardcoded Teaching Awards & Qualifications Fix ---
        elif current_section == "Teaching Awards & Qualifications":
            # Identify standard titles
            if line in ["Excellence in Teaching", "Fellowship of the Higher Education Academy", "Associate Fellowship"]:
                section_data["items"].append({
                    "role": line,
                    "institution": "",
                    "date": "",
                    "details": ""
                })
            elif section_data["items"]:
                last_item = section_data["items"][-1]
                
                # Context check to ensure Warwick awards land at Warwick
                if "Warwick Award" in line or "WATE" in line:
                    last_item["institution"] = "University of Warwick"
                elif "Student Teaching Award" in line or "Graduate Teaching Assistant" in line:
                    last_item["institution"] = "University of Glasgow"
                elif "Developing as a Teacher in Higher Education" in line:
                    last_item["institution"] = "University of Glasgow"
                
                # Default safety assignment if blank
                if not last_item["institution"] and "University of" in line:
                    if "Warwick" in line: last_item["institution"] = "University of Warwick"
                    else: last_item["institution"] = "University of Glasgow"

                # Pull year strings out cleanly
                year_match = re.search(r'\b(20\d{2})\b', line)
                if year_match and not last_item["date"]:
                    last_item["date"] = year_match.group(1)

                if "University of" in line or line == "alignment":
                    continue
                last_item["details"] = (last_item["details"] + " " + line).strip()

        # --- MODE C: Presentations / Conferences ---
        elif current_section == "Selected Presentations":
            if re.match(r'^\d{4}$', line):
                section_data["items"].append({"role": "MARKER", "institution": "", "date": line, "details": ""})
            elif section_data["items"]:
                last_item = section_data["items"][-1]
                if last_item["role"] == "MARKER":
                    last_item["role"] = line
                else:
                    section_data["items"].append({"role": line, "institution": "", "date": last_item["date"], "details": ""})

        # --- MODE D: Fallback Blocks (Teaching Experience, Referees) ---
        else:
            if ":" in line and len(line) < 60:
                section_data["items"].append({"role": line, "institution": "", "date": "", "details": ""})
            elif section_data["items"]:
                section_data["items"][-1]["details"] = (section_data["items"][-1]["details"] + " " + line).strip()
            else:
                section_data["items"].append({"role": "", "institution": "", "date": "", "details": line})

    if current_section and current_section != "SKIP" and section_data["items"]:
        structured_data["sections"].append(section_data)

    # Clean up marker leftovers before writing out
    for sec in structured_data["sections"]:
        sec["items"] = [it for it in sec["items"] if it["role"] != "MARKER"]

    with open("website/cv.json", "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    print("cv.json synchronized locally with spacing corrections.")

if __name__ == "__main__":
    parse_pdf_to_json()
