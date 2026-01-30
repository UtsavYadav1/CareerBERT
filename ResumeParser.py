import re
from pdfminer.high_level import extract_text as _extract_text
try:
    # pdfminer.high_level is the usual import; keep a safe fallback
    from pdfminer.high_level import extract_text as extract_text_pdf
except Exception:
    extract_text_pdf = _extract_text


class ResumeParserClass:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.resume_text = self.extract_text_from_pdf()

    def extract_text_from_pdf(self):
        try:
            text = extract_text_pdf(self.pdf_path)
        except Exception:
            text = ''
        # Normalize whitespace to make regex matching more reliable
        if text:
            text = re.sub(r'[\t\r]', ' ', text)
            text = re.sub(r'\u2022|\u2023|\u25E6|\u2043|\u2219', ' ', text)  # bullets → space
            text = re.sub(r'\s+', ' ', text)
        return text

    def parse(self):
        """Robust section extraction by locating header positions and slicing text between headers.
        Returns a dict with keys: Education, Experience, Projects, Publications, Skills
        """
        text = self.resume_text or ''
        if not text:
            return {
                "Education": "Section not found.",
                "Experience": "Section not found.",
                "Projects": "Section not found.",
                "Publications": "Section not found.",
                "Skills": "Section not found."
            }

        # Header variants
        headers = {
            'Education': [r'education', r'educational\s+background', r'academic\s+background'],
            'Experience': [r'experience', r'work\s+experience', r'professional\s+experience', r'employment\s+history'],
            'Projects': [r'personal\s+projects', r'projects', r'key\s+projects', r'academic\s+projects'],
            'Publications': [r'publications', r'research\s+publications'],
            'Skills': [r'technical\s+skills', r'skills', r'core\s+skills', r'technical\s+expertise']
        }

        # Find all header occurrences with their canonical name and start index
        markers = []
        for canon, variants in headers.items():
            for pat in variants:
                for m in re.finditer(rf'\b{pat}\b\s*[:\-]*', text, flags=re.IGNORECASE):
                    markers.append((m.start(), m.end(), canon))

        if not markers:
            # Nothing matched; return not found
            return {
                "Education": "Section not found.",
                "Experience": "Section not found.",
                "Projects": "Section not found.",
                "Publications": "Section not found.",
                "Skills": "Section not found."
            }

        # Sort by start index so we can slice blocks between headers
        markers.sort(key=lambda x: x[0])

        # Build slices: from end of marker i to start of marker i+1
        sections_map = {k: [] for k in headers.keys()}
        for idx, (start, end, canon) in enumerate(markers):
            next_start = markers[idx + 1][0] if idx + 1 < len(markers) else len(text)
            # Slice the text belonging to this section
            content = text[end:next_start].strip()
            if content:
                sections_map[canon].append(content)

        # Join multiple occurrences and normalize
        def norm_join(parts):
            if not parts:
                return "Section not found."
            joined = ' '.join(p.strip() for p in parts if p and p.strip())
            # Remove duplicated spaces
            return re.sub(r'\s+', ' ', joined).strip() or "Section not found."

        parsed = {k: norm_join(v) for k, v in sections_map.items()}

        return {
            "Education": parsed.get('Education', "Section not found."),
            "Experience": parsed.get('Experience', "Section not found."),
            "Projects": parsed.get('Projects', "Section not found."),
            "Publications": parsed.get('Publications', "Section not found."),
            "Skills": parsed.get('Skills', "Section not found.")
        }
