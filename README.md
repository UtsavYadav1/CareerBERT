<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-2.3.2-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch">
  <img src="https://img.shields.io/badge/Transformers-4.29+-FF6F00?style=for-the-badge&logo=huggingface&logoColor=white" alt="Transformers">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

<h1 align="center">🧠 CareerBERT</h1>
<h3 align="center">AI-Powered Resume-to-Job Matching System</h3>

<p align="center">
  <strong>Smart job matching and resume analysis powered by Transformer models (DistilBERT) and classic IR techniques (TF-IDF + Cosine Similarity)</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-demo">Demo</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-api-reference">API</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

## 📋 Overview

**CareerBERT** is an intelligent resume analysis platform that leverages state-of-the-art NLP models to match resumes with job descriptions. Built with Flask and powered by DistilBERT, it provides detailed compatibility scores, skill gap analysis, and actionable recommendations to help job seekers optimize their applications.

### ✨ Key Highlights

- 🎯 **AI-Powered Matching** — Uses DistilBERT for intelligent text classification and TF-IDF for accurate similarity scoring
- 📊 **Detailed Analytics** — Get breakdowns of Experience Match, Technical Fit, and Skills Match scores
- 📄 **Smart Resume Parsing** — Automatically extracts and categorizes resume sections from PDF files
- 💡 **Skill Gap Analysis** — Identifies missing skills with suggested learning resources
- 🔍 **Job Recommendations** — Live job recommendations via SerpAPI integration
- 📑 **PDF Reports** — Generate comprehensive analysis reports in PDF format
- 🎨 **Modern UI** — Beautiful, responsive interface built with Bootstrap

---

## 🚀 Features

### Resume Analysis
- **Intelligent Section Extraction** — Automatically identifies and parses Education, Experience, Projects, Publications, and Skills sections
- **Multi-format Support** — Accepts PDF and TXT resume formats
- **Text Preprocessing** — NLTK-powered text cleaning, stopword removal, and tokenization

### Job Matching Engine
- **DistilBERT Classification** — Categorizes job posting sentences into SCHOOL, SKILLS, JOBDES, or NONE
- **TF-IDF Vectorization** — Advanced n-gram (1-3) vectorization with sublinear TF scaling
- **Cosine Similarity** — Accurate similarity scoring with fallback methods (Word Overlap, Keyword Matching)
- **Weighted Scoring** — 40% Experience Match + 60% Skills Match for optimal results

### Job Recommendations
- **SerpAPI Integration** — Live job listings from Google Jobs
- **Fallback Recommendations** — Links to major career portals (Microsoft, Google, Amazon, Netflix, Meta)
- **Location-based Search** — Filter recommendations by user location

### Reporting
- **Real-time Analysis** — WebSocket-powered progress updates during processing
- **PDF Report Generation** — Professional reports using ReportLab with charts and tables
- **Export Functionality** — Download comprehensive analysis reports

---

## 🎬 Demo

<p align="center">
  <img src="gifs/Animation.gif" alt="CareerBERT Demo" width="600">
</p>

---

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/UtsavYadav1/CareerBERT.git
   cd CareerBERT
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   # Windows
   python -m venv .venv
   .\.venv\Scripts\activate

   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Set up SerpAPI for live job recommendations**
   ```bash
   # Windows
   set SERPAPI_KEY=your_api_key_here

   # macOS/Linux
   export SERPAPI_KEY=your_api_key_here
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

---

## 📖 Usage

### Web Application

1. Navigate to `http://127.0.0.1:5000`
2. Upload your resume (PDF or TXT format)
3. Paste the job description you want to match against
4. (Optional) Enter your location for job recommendations
5. Click "Analyze" and view your results
6. Download the PDF report for your records

### Command Line Interface

Process a resume directly from the terminal:

```bash
python main.py path/to/resume.pdf
```

This will analyze the resume against job listings in the `job_data/` directory and output the top 10 matching jobs.

---

## 🏗️ Architecture

```
CareerBERT/
├── app.py                  # Main Flask application with SocketIO
├── main.py                 # CLI interface for batch processing
├── BertModel.py            # DistilBERT classifier wrapper
├── ResumeParser.py         # PDF parsing and section extraction
├── utils.py                # Text processing and similarity functions
├── web_scrape.py           # SerpAPI integration for job search
│
├── templates/              # HTML templates
│   ├── index.html          # Main upload page
│   ├── results.html        # Analysis results page
│   ├── about.html          # About page
│   └── contact.html        # Contact page
│
├── static/                 # Static assets
│   ├── css/                # Stylesheets
│   └── js/                 # JavaScript files
│
├── trained_models/         # Pre-trained DistilBERT model weights
├── job_data/               # Sample job listings CSV
├── uploads/                # Temporary upload directory
└── gifs/                   # Demo animations
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Flask, Flask-SocketIO |
| **ML Model** | DistilBERT (Hugging Face Transformers) |
| **NLP** | NLTK, scikit-learn (TF-IDF) |
| **PDF Processing** | pdfminer.six |
| **PDF Generation** | ReportLab |
| **Frontend** | HTML5, CSS3, Bootstrap, JavaScript |
| **Job Search API** | SerpAPI (Google Jobs) |

---

## 🔌 API Reference

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `start` | Client → Server | Initiates resume analysis |
| `progress` | Server → Client | Sends progress updates |
| `error` | Server → Client | Sends error messages |

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page with upload form |
| `/upload` | POST | Handle resume file upload |
| `/results` | GET | Get analysis results (JSON) |
| `/results-page` | GET | Results page (HTML) |
| `/download-pdf` | GET | Download PDF report |

---

## 📝 Resume Format Tips

For optimal parsing results, structure your resume with clear section headers:

- **EDUCATION** — Academic qualifications and certifications
- **EXPERIENCE** — Work history and professional experience
- **PROJECTS** — Personal, academic, or professional projects
- **PUBLICATIONS** — Research papers, articles, or publications
- **SKILLS** — Technical and soft skills

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with debug mode
flask run --debug
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

<p align="center">
  <a href="https://github.com/UtsavYadav1">
    <img src="https://img.shields.io/badge/GitHub-UtsavYadav1-181717?style=for-the-badge&logo=github" alt="GitHub">
  </a>
</p>

---

## 🙏 Acknowledgments

- [Hugging Face](https://huggingface.co/) for the Transformers library
- [DistilBERT](https://huggingface.co/distilbert-base-cased) for the base model architecture
- [SerpAPI](https://serpapi.com/) for job search capabilities
- [ReportLab](https://www.reportlab.com/) for PDF generation

---

<p align="center">
  <strong>⭐ Star this repository if you find it helpful! ⭐</strong>
</p>
