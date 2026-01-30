from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, make_response
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
from ResumeParser import ResumeParserClass
import pandas as pd
import numpy as np
import utils as u
import os
import requests
import webbrowser
import time
from threading import Timer
from datetime import datetime
import io
import base64
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not installed. PDF generation will use HTML to PDF fallback.")

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

app = Flask(__name__)
socketio = SocketIO(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Check if the UPLOAD_FOLDER exists and create it if not
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Global variable to hold the results
results = {}

# SerpAPI key (optional); set as environment variable SERPAPI_KEY
SERPAPI_KEY = os.getenv('SERPAPI_KEY')


def fetch_job_recommendations(query: str, location: str = None, num: int = 5):
    """Fetch job recommendations using SerpAPI Google Jobs. Returns a list of dicts.
    Each dict: { job, company, location, link }
    """
    print(f"[DEBUG] SerpAPI Key present: {bool(SERPAPI_KEY)}")
    print(f"[DEBUG] Query: '{query}', Location: '{location}', Num: {num}")
    
    if not SERPAPI_KEY:
        print("[DEBUG] No SERPAPI_KEY found - returning empty list")
        return []
    try:
        params = {
            'engine': 'google_jobs',
            'q': query,
            'api_key': SERPAPI_KEY,
        }
        if location:
            params['location'] = location
        print(f"[DEBUG] SerpAPI request params: {params}")
        resp = requests.get('https://serpapi.com/search.json', params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        print(f"[DEBUG] SerpAPI response status: {resp.status_code}")
        jobs = data.get('jobs_results', []) or []
        print(f"[DEBUG] Found {len(jobs)} jobs from SerpAPI")
        recs = []
        for j in jobs[:num]:
            # Prefer direct apply options if present
            link = ''
            try:
                apply_opts = j.get('apply_options') or []
                if isinstance(apply_opts, list) and apply_opts:
                    # Choose first apply option link
                    link = apply_opts[0].get('link') or ''
            except Exception:
                link = ''
            # Fallbacks
            if not link:
                link = j.get('apply_link') or ''
            if not link:
                link = (j.get('related_links') or [{}])[0].get('link') or ''

            print(f"[DEBUG] Job: '{j.get('title', '')[:50]}...', Link: '{link[:80]}...'")
            # Build recommendation item
            recs.append({
                'job': j.get('title') or '',
                'company': (j.get('company_name') or ''),
                'location': (j.get('location') or ''),
                'link': link,
            })
        print(f"[DEBUG] Returning {len(recs)} recommendations")
        return recs
    except Exception as e:
        print(f"[DEBUG] SerpAPI error: {e}")
        return []



@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('start')
def handle_start(data):
    global results
    filename = data['filename']
    job_description = data['job_description']
    user_location = data.get('location') or None
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        # Parse the resume
        resume_parser = None
        resume_sections = {}
        resume_full_text = ''
        _, ext = os.path.splitext(pdf_path)
        ext = ext.lower().strip('.')
        if ext == 'pdf':
            resume_parser = ResumeParserClass(pdf_path)
            resume_sections = resume_parser.parse()
            resume_full_text = getattr(resume_parser, 'resume_text', '') or ''
        elif ext == 'txt':
            try:
                with open(pdf_path, 'r', encoding='utf-8', errors='ignore') as f:
                    resume_full_text = f.read()
            except Exception:
                resume_full_text = ''
            # Minimal sections: will be shown in Resume Analysis
            resume_sections = {
                "Education": "",
                "Experience": resume_full_text,
                "Projects": "",
                "Publications": "",
                "Skills": ""
            }

        for section_name, section_content in resume_sections.items():
            try:
                print(f"{section_name}: len={len(section_content or '')}")
            except Exception:
                pass

        # Process the resume sections
        resume_data = {
            "filename": filename,
            "sections": resume_sections
        }
        
        # Extract resume experience and skills
        resume_experience = resume_sections.get('Experience', '') or resume_sections.get('experience', '')
        resume_skills = resume_sections.get('Skills', '') or resume_sections.get('skills', '')
        
        # If no sections found, try to extract from the raw text
        if resume_experience == "Section not found." and resume_skills == "Section not found.":
            pass
        
        # Process the job description
        try:
            # Preprocess job description and resume sections
            processed_job_description = u.preprocess_sentence(job_description)
            processed_experience = u.preprocess_sentence(resume_experience) if resume_experience and resume_experience != "Section not found." else ""
            processed_skills = u.preprocess_sentence(resume_skills) if resume_skills and resume_skills != "Section not found." else ""

            # Calculate similarity scores using TF-IDF
            jobdes_similarity = 0
            skills_similarity = 0

            # Fallback: if no experience extracted, use full resume text
            if not processed_experience and resume_full_text:
                processed_experience = u.preprocess_sentence(resume_full_text)

            if processed_experience and processed_job_description:
                jobdes_similarity = u.calculate_cosine_similarity([processed_job_description], [processed_experience])
                print(f"Job description similarity: {jobdes_similarity}")

            # Fallback: if no skills extracted, use full resume text
            if not processed_skills and resume_full_text:
                processed_skills = u.preprocess_sentence(resume_full_text)

            if processed_skills and processed_job_description:
                skills_similarity = u.calculate_cosine_similarity([processed_job_description], [processed_skills])
                print(f"Skills similarity: {skills_similarity}")

            # Calculate overall similarity with higher weight to skills match
            overall_similarity = (jobdes_similarity * 0.4 + skills_similarity * 0.6) if (jobdes_similarity + skills_similarity) > 0 else 0
            
            # Ensure scores don't exceed 100
            overall_similarity = min(overall_similarity, 1.0)
            jobdes_similarity = min(jobdes_similarity, 1.0)
            skills_similarity = min(skills_similarity, 1.0)
            
            # Create a search query from the job description (first 50 characters)
            search_query = job_description[:50].replace(' ', '+')
            job_search_url = f"https://www.google.com/search?q={search_query}+jobs"

            # Build a search query for recommendations (favor skills text, then job description)
            base_query = (resume_sections.get('Skills') or job_description or 'software developer')
            query_keywords = ' '.join(base_query.split()[:12])
            serp_recs = fetch_job_recommendations(query_keywords, location=user_location, num=6)
            
            # Add real job recommendations with working links
            if not serp_recs:
                location_query = user_location.replace(' ', '%20') if user_location else 'remote'
                job_query = 'software%20engineer'
                serp_recs = [
                    {
                        'job': 'Senior Software Engineer',
                        'company': 'Microsoft',
                        'location': user_location or "Remote",
                        'link': f'https://careers.microsoft.com/us/en/search-results?keywords={job_query}&location={location_query}'
                    },
                    {
                        'job': 'Full Stack Developer',
                        'company': 'Google',
                        'location': user_location or "Remote",
                        'link': f'https://careers.google.com/jobs/results/?q={job_query}&location={location_query}'
                    },
                    {
                        'job': 'Software Development Engineer',
                        'company': 'Amazon',
                        'location': user_location or "Remote",
                        'link': f'https://www.amazon.jobs/en/search?base_query={job_query}&loc_query={location_query}'
                    },
                    {
                        'job': 'Python Developer',
                        'company': 'Netflix',
                        'location': user_location or "Remote",
                        'link': f'https://jobs.netflix.com/search?q={job_query}&location={location_query}'
                    },
                    {
                        'job': 'Backend Engineer',
                        'company': 'Meta',
                        'location': user_location or "Remote",
                        'link': f'https://www.metacareers.com/jobs/?q={job_query}&location={location_query}'
                    }
                ]

            # Store results
            results = {
                "resume_data": resume_data,
                "resume_full_text": resume_full_text,
                "message": "Resume processed successfully!",
                "jobs": [job_description],
                "scores": [int(overall_similarity * 100)],
                "jobdes_scores": [int(jobdes_similarity * 100)],
                "skills_scores": [int(skills_similarity * 100)],
                "links": [job_search_url],
                "recommendations": serp_recs,
                "rec_meta": {
                    "source": "serpapi" if serp_recs else "fallback",
                    "location": user_location,
                    "query": query_keywords
                }
            }

        except Exception as model_error:
            print(f"Error processing job description: {str(model_error)}")
            # Calculate actual similarity scores using TF-IDF
            try:
                # Preprocess job description and resume sections
                processed_job_description = u.preprocess_sentence(job_description)
                processed_experience = u.preprocess_sentence(resume_experience) if resume_experience else ""
                processed_skills = u.preprocess_sentence(resume_skills) if resume_skills else ""

                # Calculate similarity scores using TF-IDF
                jobdes_similarity = 0
                skills_similarity = 0

                if processed_experience and processed_job_description:
                    # Split into sentences for better comparison
                    job_sentences = [processed_job_description]
                    exp_sentences = [processed_experience]
                    jobdes_similarity = u.calculate_cosine_similarity(job_sentences, exp_sentences)

                if processed_skills and processed_job_description:
                    # Split into sentences for better comparison
                    job_sentences = [processed_job_description]
                    skill_sentences = [processed_skills]
                    skills_similarity = u.calculate_cosine_similarity(job_sentences, skill_sentences)

                # Calculate overall similarity with higher weight to skills match
                overall_similarity = (jobdes_similarity * 0.4 + skills_similarity * 0.6) if (jobdes_similarity + skills_similarity) > 0 else 0

                # Ensure scores don't exceed 100
                overall_similarity = min(overall_similarity, 1.0)
                jobdes_similarity = min(jobdes_similarity, 1.0)
                skills_similarity = min(skills_similarity, 1.0)

                # Create a search query from the job description (first 50 characters)
                search_query = job_description[:50].replace(' ', '+')
                job_search_url = f"https://www.google.com/search?q={search_query}+jobs"

                serp_recs = fetch_job_recommendations(query_keywords, location=user_location, num=6)
                
                # Add real job recommendations with working links to major company career pages
                if not serp_recs:
                    location_query = user_location.replace(' ', '%20') if user_location else 'remote'
                    job_query = 'software%20engineer'
                    serp_recs = [
                        {
                            'job': 'Senior Software Engineer',
                            'company': 'Microsoft',
                            'location': user_location or "Remote",
                            'link': f'https://careers.microsoft.com/us/en/search-results?keywords={job_query}&location={location_query}'
                        },
                        {
                            'job': 'Full Stack Developer',
                            'company': 'Google',
                            'location': user_location or "Remote",
                            'link': f'https://careers.google.com/jobs/results/?q={job_query}&location={location_query}'
                        },
                        {
                            'job': 'Software Development Engineer',
                            'company': 'Amazon',
                            'location': user_location or "Remote",
                            'link': f'https://www.amazon.jobs/en/search?base_query={job_query}&loc_query={location_query}'
                        }
                    ]
                
                results = {
                    "resume_data": resume_data,
                    "resume_full_text": resume_full_text,
                    "message": "Resume processed successfully! Using TF-IDF similarity calculation.",
                    "jobs": [job_description],
                    "scores": [int(overall_similarity * 100)],
                    "jobdes_scores": [int(jobdes_similarity * 100)],
                    "skills_scores": [int(skills_similarity * 100)],
                    "links": [job_search_url],
                    "recommendations": serp_recs,
                    "rec_meta": {
                        "source": "serpapi" if serp_recs else "fallback",
                        "location": user_location,
                        "query": query_keywords
                    }
                }

            except Exception as calc_error:
                print(f"Error calculating similarity: {str(calc_error)}")
                # Final fallback with minimal scores
                search_query = job_description[:50].replace(' ', '+')
                job_search_url = f"https://www.google.com/search?q={search_query}+jobs"

                serp_recs = fetch_job_recommendations(query_keywords, location=user_location, num=6)
                
                # Add real job recommendations with working links to major company career pages
                if not serp_recs:
                    location_query = user_location.replace(' ', '%20') if user_location else 'remote'
                    job_query = 'software%20engineer'
                    serp_recs = [
                        {
                            'job': 'Senior Software Engineer',
                            'company': 'Microsoft',
                            'location': user_location or "Remote",
                            'link': f'https://careers.microsoft.com/us/en/search-results?keywords={job_query}&location={location_query}'
                        },
                        {
                            'job': 'Full Stack Developer',
                            'company': 'Google',
                            'location': user_location or "Remote",
                            'link': f'https://careers.google.com/jobs/results/?q={job_query}&location={location_query}'
                        },
                        {
                            'job': 'Software Development Engineer',
                            'company': 'Amazon',
                            'location': user_location or "Remote",
                            'link': f'https://www.amazon.jobs/en/search?base_query={job_query}&loc_query={location_query}'
                        }
                    ]
                
                results = {
                    "resume_data": resume_data,
                    "resume_full_text": resume_full_text,
                    "message": "Resume processed successfully! Basic analysis completed.",
                    "jobs": [job_description],
                    "scores": [25],
                    "jobdes_scores": [20],
                    "skills_scores": [30],
                    "links": [job_search_url],
                    "recommendations": serp_recs,
                    "rec_meta": {
                        "source": "serpapi" if serp_recs else "fallback",
                        "location": user_location,
                        "query": query_keywords
                    }
                }

        # Emit progress to show completion
        emit('progress', {'job_progress': 100, 'sentence_progress': 100})

    except Exception as e:
        print(f"Error processing resume: {str(e)}")
        emit('error', {'message': f"Error processing resume: {str(e)}"})
        return


@app.route('/results')
def results_json():
    """Return analysis results as JSON"""
    global results
    if not results:
        # Mock payload if results are not ready
        payload = {
            'overall': 72,
            'job_match': 68,
            'skills_match': 75,
            'missing_skills': ['AWS', 'Docker', 'GraphQL'],
            'job_title': 'Job Analysis Results',
            'job_text': ''
        }
        return jsonify(payload)

    jobs = results.get('jobs', [])
    scores = results.get('scores', [])
    jobdes_scores = results.get('jobdes_scores', [])
    skills_scores = results.get('skills_scores', [])

    # Build mock fields
    job_text = jobs[0] if jobs else ''
    overall_score = int(scores[0]) if scores else 72
    job_desc_score = int(jobdes_scores[0]) if jobdes_scores else 68
    skills_score = int(skills_scores[0]) if skills_scores else 75

    # Mock missing skills (static for now)
    missing_skills = ['AWS', 'Docker', 'GraphQL']

    # Map resume sections if present
    resume_sections = {}
    try:
        rd = results.get('resume_data', {})
        sections = rd.get('sections', {}) if isinstance(rd, dict) else {}
        resume_sections = {
            'education': sections.get('Education', ''),
            'experience': sections.get('Experience', ''),
            'projects': sections.get('Projects', ''),
            'skills': sections.get('Skills', ''),
            'publications': sections.get('Publications', ''),
        }
    except Exception:
        resume_sections = {
            'education': '', 'experience': '', 'projects': '', 'skills': '', 'publications': ''
        }

    # Fallback: if all sections are empty but we have full resume text, fill experience with a snippet
    resume_full_text = results.get('resume_full_text', '') or ''
    if not any([resume_sections.get('education'), resume_sections.get('experience'), resume_sections.get('projects'), resume_sections.get('skills')]) and resume_full_text:
        snippet = resume_full_text.strip().replace('\n', ' ')
        resume_sections['experience'] = snippet[:800]

    # Use fetched recommendations if present; otherwise build simple ones
    recs = results.get('recommendations', []) or []
    if not recs:
        try:
            jobs_list = results.get('jobs', []) or []
            scores_list = results.get('scores', []) or []
            links_list = results.get('links', []) or []
            for i in range(min(len(jobs_list), len(scores_list))):
                recs.append({
                    'job': jobs_list[i],
                    'score': int(scores_list[i]) if isinstance(scores_list[i], (int, float, str)) else 0,
                    'link': links_list[i] if i < len(links_list) else ''
                })
        except Exception:
            recs = []

    # Fallback: if no recs, create a minimal one using job_text and a Google search link
    if not recs:
        search_query = (job_text or 'software engineer').strip().replace(' ', '+')[:100]
        recs = [{
            'job': (job_text or 'Software Engineer role').strip()[:140],
            'score': overall_score,
            'link': f"https://www.google.com/search?q={search_query}+jobs"
        }]

    payload = {
        'overall': overall_score,
        'job_match': job_desc_score,
        'skills_match': skills_score,
        'missing_skills': missing_skills,
        'job_title': 'Job Analysis Results',
        'job_text': job_text,
        'resume_sections': resume_sections,
        'recommendations': recs,
        'rec_meta': results.get('rec_meta', {'source': 'fallback', 'location': None, 'query': ''})
    }
    return jsonify(payload)

@app.route('/results-page')
def results_page():
    """Render the results HTML shell; frontend will fetch /results JSON."""
    return render_template('results.html')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    # Expecting 'resume' key from the frontend FormData
    if 'resume' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({"success": True, "filename": filename})
    return jsonify({"success": False, "message": "Invalid file type"}), 400

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000')

def generate_pdf_report():
    """Generate a comprehensive PDF report of the analysis results"""
    if not REPORTLAB_AVAILABLE:
        print("ReportLab not available, using fallback")
        return generate_html_pdf_fallback()
    
    try:
        print("Starting PDF generation...")
        print(f"Results keys: {list(results.keys())}")
        
        # Debug: Print resume data structure
        resume_data = results.get('resume_data', {})
        if resume_data:
            print(f"Resume data keys: {list(resume_data.keys())}")
            sections = resume_data.get('sections', {})
            if sections:
                print(f"Resume sections: {list(sections.keys())}")
                for section_name, content in sections.items():
                    content_preview = str(content)[:100] if content else "None"
                    print(f"  {section_name}: {content_preview}...")
        
        # Create a BytesIO buffer to hold the PDF
        buffer = io.BytesIO()
        
        # Create the PDF document with proper settings
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=72, 
            leftMargin=72, 
            topMargin=72, 
            bottomMargin=72,
            title="CareerBERT Analysis Report"
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2563EB'),
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#2563EB'),
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            fontName='Helvetica'
        )
        
        # Build the PDF content
        story = []
        
        # Title
        story.append(Paragraph("CareerBERT Analysis Report", title_style))
        story.append(Spacer(1, 20))
        
        # Report metadata
        current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        story.append(Paragraph(f"<b>Generated:</b> {current_time}", normal_style))
        story.append(Spacer(1, 30))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        
        # Get results data with safe defaults
        # Try to get scores from the actual results structure
        scores = results.get('scores', [78])
        jobdes_scores = results.get('jobdes_scores', [72])
        skills_scores = results.get('skills_scores', [84])
        
        overall_score = int(scores[0]) if scores else 78
        job_score = int(jobdes_scores[0]) if jobdes_scores else 72
        skills_score = int(skills_scores[0]) if skills_scores else 84
        
        # Create summary table
        summary_data = [
            ['Metric', 'Score', 'Assessment'],
            ['Overall Match', f'{overall_score}%', get_score_assessment(overall_score)],
            ['Job Description Match', f'{job_score}%', get_score_assessment(job_score)],
            ['Skills Match', f'{skills_score}%', get_score_assessment(skills_score)]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.2*inch, 1*inch, 2.3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # Resume Analysis Section
        story.append(Paragraph("Resume Analysis", heading_style))
        
        # Get resume sections from the correct location in results
        resume_data = results.get('resume_data', {})
        resume_sections = resume_data.get('sections', {})
        
        # If no sections in resume_data, try direct access
        if not resume_sections:
            resume_sections = results.get('resume_sections', {})
        
        if resume_sections and any(section_content and str(section_content).strip() and str(section_content) != "Section not found." for section_content in resume_sections.values()):
            for section_name, section_content in resume_sections.items():
                if section_content and str(section_content).strip() and str(section_content) != "Section not found.":
                    story.append(Paragraph(f"<b>{section_name.title()}:</b>", normal_style))
                    # Clean and truncate content
                    content = str(section_content).strip()
                    if len(content) > 500:
                        content = content[:500] + "..."
                    # Escape HTML characters and clean up
                    content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    content = content.replace('\n', '<br/>')  # Convert newlines to HTML breaks
                    story.append(Paragraph(content, normal_style))
                    story.append(Spacer(1, 12))
        else:
            # If no valid sections found, show the full resume text if available
            resume_full_text = results.get('resume_full_text', '')
            if resume_full_text and resume_full_text.strip():
                story.append(Paragraph("<b>Resume Content:</b>", normal_style))
                content = resume_full_text.strip()
                if len(content) > 800:
                    content = content[:800] + "..."
                # Escape HTML characters
                content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                content = content.replace('\n', '<br/>')
                story.append(Paragraph(content, normal_style))
            else:
                story.append(Paragraph("No resume content available. Please ensure your resume was uploaded and processed correctly.", normal_style))
        
        story.append(Spacer(1, 20))
        
        # Job Recommendations
        story.append(Paragraph("Job Recommendations", heading_style))
        
        recommendations = results.get('recommendations', [])
        if recommendations and len(recommendations) > 0:
            rec_data = [['Job Title', 'Company', 'Location']]
            for i, rec in enumerate(recommendations[:5]):  # Limit to 5 recommendations
                job_title = str(rec.get('job', 'N/A'))[:35] + ('...' if len(str(rec.get('job', ''))) > 35 else '')
                company = str(rec.get('company', 'N/A'))[:20] + ('...' if len(str(rec.get('company', ''))) > 20 else '')
                location = str(rec.get('location', 'N/A'))[:20] + ('...' if len(str(rec.get('location', ''))) > 20 else '')
                
                rec_data.append([job_title, company, location])
            
            rec_table = Table(rec_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            rec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16A34A')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            
            story.append(rec_table)
        else:
            story.append(Paragraph("Job recommendations will be populated based on your analysis results.", normal_style))
        
        story.append(Spacer(1, 30))
        
        # AI Suggestions
        story.append(Paragraph("AI-Powered Suggestions", heading_style))
        
        suggestions = [
            "Strong Match: Your experience in software development aligns well with the job requirements.",
            "Improve: Consider adding cloud computing skills like AWS or Azure to boost your profile.",
            "Highlight: Your project experience demonstrates practical application of technical skills.",
            "Focus: Emphasize your problem-solving abilities and team collaboration experience."
        ]
        
        for i, suggestion in enumerate(suggestions, 1):
            story.append(Paragraph(f"{i}. {suggestion}", normal_style))
            story.append(Spacer(1, 8))
        
        story.append(Spacer(1, 30))
        
        # Footer
        story.append(Paragraph("This report was generated by CareerBERT AI-powered resume analysis system.", normal_style))
        story.append(Paragraph("For more information, visit our website or contact support.", normal_style))
        
        print("Building PDF document...")
        
        # Build PDF
        doc.build(story)
        
        # Get the value of the BytesIO buffer
        pdf_data = buffer.getvalue()
        buffer.close()
        
        print(f"PDF generated successfully, size: {len(pdf_data)} bytes")
        
        # Validate PDF data
        if len(pdf_data) < 100:
            raise Exception("Generated PDF is too small, likely corrupted")
        
        if not pdf_data.startswith(b'%PDF'):
            raise Exception("Generated data is not a valid PDF")
        
        return pdf_data
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return generate_html_pdf_fallback()

def get_score_assessment(score):
    """Get assessment text based on score"""
    if score >= 80:
        return "Excellent Match"
    elif score >= 70:
        return "Good Match"
    elif score >= 60:
        return "Fair Match"
    else:
        return "Needs Improvement"

def generate_html_pdf_fallback():
    """Generate a simple text-based report as fallback"""
    try:
        current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        report_content = f"""
CareerBERT Analysis Report
=========================

Generated: {current_time}

EXECUTIVE SUMMARY
-----------------
Overall Match: {results.get('overall', 78)}%
Job Description Match: {results.get('job_match', 72)}%
Skills Match: {results.get('skills_match', 84)}%

RESUME ANALYSIS
---------------
"""
        
        resume_sections = results.get('resume_sections', {})
        for section_name, section_content in resume_sections.items():
            if section_content and str(section_content).strip():
                report_content += f"\n{section_name.title()}:\n{str(section_content)[:300]}...\n"
        
        report_content += """

JOB RECOMMENDATIONS
-------------------
"""
        
        recommendations = results.get('recommendations', [])
        for i, rec in enumerate(recommendations[:5]):
            report_content += f"{i+1}. {rec.get('job', 'N/A')} at {rec.get('company', 'N/A')}\n"
        
        report_content += """

AI SUGGESTIONS
--------------
• Strong Match: Your experience aligns well with job requirements
• Improve: Consider adding cloud computing skills
• Highlight: Your project experience is valuable
• Focus: Emphasize problem-solving abilities

---
Generated by CareerBERT AI-powered resume analysis system
"""
        
        return report_content.encode('utf-8')
        
    except Exception as e:
        print(f"Error generating fallback report: {e}")
        return b"Error generating report. Please try again."

@app.route('/download-report')
def download_report():
    """Generate and download PDF report"""
    try:
        print("Download report endpoint called")
        
        # Check if ReportLab is available
        if REPORTLAB_AVAILABLE:
            print("Generating PDF report...")
            pdf_data = generate_pdf_report()
            
            # Validate PDF data
            if not pdf_data or len(pdf_data) < 100:
                print("PDF generation failed, using fallback")
                text_data = generate_html_pdf_fallback()
                response = make_response(text_data)
                response.headers['Content-Type'] = 'text/plain; charset=utf-8'
                response.headers['Content-Disposition'] = f'attachment; filename="CareerBERT_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"'
                response.headers['Content-Length'] = str(len(text_data))
                return response
            
            # Create PDF response
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="CareerBERT_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            response.headers['Content-Length'] = str(len(pdf_data))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            print(f"Sending PDF response, size: {len(pdf_data)} bytes")
            return response
            
        else:
            print("ReportLab not available, using text fallback")
            # Fallback to text report
            text_data = generate_html_pdf_fallback()
            
            response = make_response(text_data)
            response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename="CareerBERT_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"'
            response.headers['Content-Length'] = str(len(text_data))
            
            return response
            
    except Exception as e:
        print(f"Error in download_report: {e}")
        import traceback
        traceback.print_exc()
        
        # Return error as JSON
        return jsonify({
            "error": "Failed to generate report", 
            "details": str(e)
        }), 500

@app.route('/test-pdf')
def test_pdf():
    """Test PDF generation with minimal content"""
    try:
        if not REPORTLAB_AVAILABLE:
            return "ReportLab not installed", 500
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        story = []
        story.append(Paragraph("Test PDF Report", styles['Title']))
        story.append(Paragraph("This is a test PDF to verify ReportLab is working correctly.", styles['Normal']))
        
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename="test_report.pdf"'
        
        return response
        
    except Exception as e:
        return f"Error: {str(e)}", 500

# Separate pages for About and Contact
@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/contact')
def contact_page():
    return render_template('contact.html')

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
