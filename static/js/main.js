// CareerBERT Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Socket.IO connection
    const socket = io();
    
    // Get form elements
    const uploadForm = document.getElementById('uploadForm');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const submitBtn = document.getElementById('submitBtn');
    
    // Debug: Check if elements are found
    console.log('Form elements found:', {
        uploadForm: !!uploadForm,
        progressContainer: !!progressContainer,
        progressBar: !!progressBar,
        progressText: !!progressText,
        submitBtn: !!submitBtn
    });
    
    // Form submission handler
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('Form submission started');
            
            // Show progress bar
            showProgressBar();
            
            // Animate progress bar
            animateProgressBar();
            
            // Disable submit button
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Analyzing...';
            
            // Create FormData
            const formData = new FormData();
            const resumeFile = document.getElementById('resumeFile').files[0];
            const jobDescription = document.getElementById('jobDescription').value;
            const jobLocation = (document.getElementById('jobLocation')?.value || '').trim();
            
            console.log('Resume file:', resumeFile);
            console.log('Job description length:', jobDescription.length);
            console.log('Location:', jobLocation);
            
            if (!resumeFile || !jobDescription) {
                hideProgressBar();
                showAlert('Please select a resume file and enter a job description', 'danger');
                resetSubmitButton();
                return;
            }
            
            formData.append('resume', resumeFile);
            formData.append('job_description', jobDescription);
            if (jobLocation) formData.append('location', jobLocation);
            
            // Send request
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(async response => {
                // Try to parse JSON safely
                let data = null;
                try { data = await response.json(); } catch (e) {}
                if (!response.ok || !data) {
                    throw new Error((data && data.message) || 'Upload failed');
                }
                return data;
            })
            .then(data => {
                if (data.success && data.filename) {
                    // Start server-side processing via Socket.IO
                    socket.emit('start', {
                        filename: data.filename,
                        job_description: jobDescription,
                        location: jobLocation || undefined
                    });
                    // Progress handler will redirect when complete
                } else {
                    hideProgressBar();
                    showAlert((data && data.message) || 'An error occurred', 'danger');
                    resetSubmitButton();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                hideProgressBar();
                showAlert('An error occurred while processing your request', 'danger');
                resetSubmitButton();
            });
        });
    }
    
    // Socket.IO event listeners
    let hasRedirectedToResults = false;
    socket.on('progress', function(data) {
        const job = data.job_progress || 0;
        const sent = data.sentence_progress || 0;
        updateProgressBar(job, sent);
        if (!hasRedirectedToResults && job >= 100 && sent >= 100) {
            hasRedirectedToResults = true;
            completeProgressBar();
            setTimeout(() => {
                window.location.href = '/results-page';
            }, 600);
        }
    });
    
    socket.on('error', function(data) {
        hideProgressBar();
        showAlert(data.message || 'An error occurred', 'danger');
        resetSubmitButton();
    });
    
    // Progress bar functions
    function showProgressBar() {
        if (progressContainer) {
            progressContainer.style.display = 'block';
            progressContainer.classList.add('animate-fade-in');
        }
    }
    
    function hideProgressBar() {
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
        if (progressBar) {
            progressBar.style.width = '0%';
        }
    }
    
    function animateProgressBar() {
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) {
                progress = 90;
                clearInterval(interval);
            }
            updateProgressBar(progress, progress);
        }, 200);
    }
    
    function updateProgressBar(jobProgress, sentenceProgress) {
        const overallProgress = Math.round((jobProgress + sentenceProgress) / 2);
        if (progressBar) {
            progressBar.style.width = overallProgress + '%';
            progressBar.setAttribute('aria-valuenow', overallProgress);
        }
        
        if (progressText) {
            if (overallProgress < 30) {
                progressText.textContent = 'Uploading and parsing resume...';
            } else if (overallProgress < 60) {
                progressText.textContent = 'Analyzing job description...';
            } else if (overallProgress < 90) {
                progressText.textContent = 'Calculating similarity scores...';
            } else {
                progressText.textContent = 'Finalizing results...';
            }
        }
    }
    
    function completeProgressBar() {
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.classList.remove('progress-bar-animated');
            progressBar.classList.add('bg-success');
        }
        if (progressText) {
            progressText.textContent = 'Analysis complete! Redirecting...';
        }
    }
    
    function resetSubmitButton() {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-magic me-2"></i>Analyze Resume';
        }
    }
    
    // Alert function
    function showAlert(message, type) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());
        
        // Create new alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    // File input validation - Updated to support both PDF and TXT
    const resumeFileInput = document.getElementById('resumeFile');
    if (resumeFileInput) {
        resumeFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const allowedTypes = ['application/pdf', 'text/plain'];
                if (!allowedTypes.includes(file.type)) {
                    showAlert('Please select a PDF or TXT file', 'warning');
                    e.target.value = '';
                    return;
                }
                
                if (file.size > 10 * 1024 * 1024) { // 10MB limit
                    showAlert('File size too large. Please select a file smaller than 10MB', 'warning');
                    e.target.value = '';
                    return;
                }
                
                // Show file name in the drag-drop area
                const fileName = document.getElementById('fileName');
                if (fileName) {
                    fileName.textContent = `✓ ${file.name}`;
                    fileName.style.display = 'block';
                }
                
                showAlert('File selected successfully', 'success');
            }
        });
    }
    
    // Textarea character counter
    const jobDescriptionTextarea = document.getElementById('jobDescription');
    if (jobDescriptionTextarea) {
        const maxLength = 5000;
        const counter = document.createElement('div');
        counter.className = 'form-text text-end';
        counter.textContent = `0/${maxLength} characters`;
        jobDescriptionTextarea.parentNode.appendChild(counter);
        
        jobDescriptionTextarea.addEventListener('input', function() {
            const length = this.value.length;
            counter.textContent = `${length}/${maxLength} characters`;
            
            if (length > maxLength * 0.9) {
                counter.classList.add('text-warning');
            } else {
                counter.classList.remove('text-warning');
            }
            
            if (length > maxLength) {
                counter.classList.add('text-danger');
                this.value = this.value.substring(0, maxLength);
            } else {
                counter.classList.remove('text-danger');
            }
        });
    }
    
    // Add loading animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('slide-up');
    });
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add hover effects to interactive elements
    const interactiveElements = document.querySelectorAll('.btn, .card, .job-item');
    interactiveElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        element.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});

// Utility functions
function formatNumber(num) {
    return num.toLocaleString();
}

// Render resume sections in the Resume Analysis card with enhanced formatting
function renderResumeSections(sections) {
    const fill = (id, text, sectionType, fallback) => {
        const el = document.getElementById(id);
        if (!el) return;
        
        // Use the enhanced formatting function if available
        if (typeof formatResumeContent === 'function') {
            el.innerHTML = formatResumeContent(text, sectionType);
        } else {
            // Fallback to basic formatting
            const content = (text && String(text).trim() && text !== "Section not found.") ? text : fallback;
            if (sectionType === 'Skills' && content !== fallback) {
                // Format skills as tags
                const skills = content.split(/[,\n]/).map(s => s.trim()).filter(s => s.length > 0);
                if (skills.length > 0) {
                    el.innerHTML = `<div class="skill-tags">
                        ${skills.map(skill => `<span class="skill-tag">${skill}</span>`).join('')}
                    </div>`;
                } else {
                    el.innerHTML = `<div class="resume-content"><p>${content}</p></div>`;
                }
            } else {
                el.innerHTML = content !== fallback ? 
                    `<div class="resume-content"><p>${content.replace(/\n/g, '</p><p>')}</p></div>` : 
                    `<div class="content-placeholder"><i class="bi bi-info-circle me-2"></i><span>${fallback}</span></div>`;
            }
        }
    };
    
    fill('educationContent', sections.education || sections.Education, 'Education', 'No education information found');
    fill('skillsContent', sections.skills || sections.Skills, 'Skills', 'No skills information found');
    fill('experienceContent', sections.experience || sections.Experience, 'Experience', 'No experience information found');
    fill('projectsContent', sections.projects || sections.Projects, 'Projects', 'No projects information found');
}

// Render job recommendation list
function renderRecommendations(recs) {
    const container = document.getElementById('jobRecommendations');
    if (!container) return;
    if (!Array.isArray(recs) || recs.length === 0) {
        container.innerHTML = `
            <i class="bi bi-search display-4 text-muted mb-3"></i>
            <p class="text-muted">No specific job recommendations available at this time.</p>
            <p class="text-muted small">Try uploading a different resume or job description for more targeted results.</p>
        `;
        return;
    }
    const frag = document.createDocumentFragment();
    container.innerHTML = '';
    // Meta banner
    const meta = currentResults?.rec_meta || {};
    if (!container.dataset.metaRendered) {
        const banner = document.createElement('div');
        banner.className = 'd-flex justify-content-between align-items-center mb-3';
        const src = meta.source === 'serpapi' ? 'Live jobs (SerpAPI)' : 'Fallback results';
        const loc = meta.location ? ` • ${meta.location}` : '';
        banner.innerHTML = `
            <div class="text-muted small">${src}${loc}</div>
            ${meta.source === 'fallback' ? '<div class="text-warning small">Tip: Add a Location and set SERPAPI_KEY to get localized apply links.</div>' : ''}
        `;
        container.appendChild(banner);
        container.dataset.metaRendered = '1';
    }

    recs.forEach(item => {
        const wrap = document.createElement('div');
        wrap.className = 'job-recommendation-item mb-3';
        wrap.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <h6 class="mb-1">${(item.job || '').slice(0, 140)}</h6>
                    <div class="text-muted small mb-1">
                        ${(item.company || '').trim()}${item.company && item.location ? ' • ' : ''}${(item.location || '').trim()}
                    </div>
                    <div class="job-meta">
                        <span class="badge bg-primary me-2">Score: ${item.score ?? 'N/A'}</span>
                        <span class="text-muted small">Full-time • Remote</span>
                    </div>
                </div>
                ${item.link ? `<a href="${item.link}" class="btn btn-sm btn-outline-primary" target="_blank"><i class="bi bi-box-arrow-up-right me-1"></i>View Job</a>` : ''}
            </div>
        `;
        frag.appendChild(wrap);
    });
    container.appendChild(frag);
}

// Fetch JSON from /results and populate the UI on results-page
async function fetchAndRenderResults() {
    try {
        const res = await fetch('/results');
        const data = await res.json();
        currentResults = data;
        // Populate badges
        console.debug('Results JSON:', data);
        setBadgeValue('overallScoreBadge', data.overall);
        setBadgeValue('jobDescScoreBadge', data.job_match);
        setBadgeValue('skillsScoreBadge', data.skills_match);
        
        // Update additional score elements
        setBadgeValue('overallMatchScore', data.overall);
        setBadgeValue('overallMatchPercentage', data.overall);
        setBadgeValue('jobMatchPercentage', data.job_match);
        setBadgeValue('skillsMatchPercentage', data.skills_match);
        
        // Update progress bars
        updateProgressBarWidth('overallMatchProgress', data.overall);
        updateProgressBarWidth('jobMatchProgress', data.job_match);
        updateProgressBarWidth('skillsMatchProgress', data.skills_match);
        
        // Update breakdown scores
        const experienceEl = document.getElementById('experienceScore');
        if (experienceEl) experienceEl.textContent = `Experience Relevance: ${data.job_match}%`;
        const skillsEl = document.getElementById('skillsScore');
        if (skillsEl) skillsEl.textContent = `Technical Fit: ${data.skills_match}%`;
        const educationEl = document.getElementById('educationScore');
        if (educationEl) educationEl.textContent = `Background Match: ${Math.min(data.overall + 10, 100)}%`;
        
        // Re-animate badges with new values
        animateScoreBadges();
        // Populate job header content
        const titleEl = document.getElementById('jobTitle');
        if (titleEl) titleEl.textContent = data.job_title || 'Job Analysis Results';
        const textEl = document.getElementById('jobDescriptionText');
        if (textEl) textEl.textContent = (data.job_text || '').slice(0, 500);
        // Render charts using currentResults
        initResultsCharts();
        // Populate skill gap (Areas for Improvement)
        updateSkillTags('improvementAreas', Array.isArray(data.missing_skills) ? data.missing_skills : [], 'improvement');
        // Populate resume sections
        renderResumeSections(data.resume_sections || {});
        // Populate job recommendations
        renderRecommendations(data.recommendations || []);
    } catch (e) {
        console.error('Failed to fetch results JSON:', e);
        // Fallback to placeholder charts
        initResultsCharts();
    }
}

function setBadgeValue(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    const val = parseInt(value || 0, 10);
    el.textContent = isNaN(val) ? '0%' : String(val) + '%';
}

function updateProgressBarWidth(id, percentage) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.width = percentage + '%';
    // Update color based on score
    el.className = el.className.replace(/bg-\w+/, '');
    if (percentage >= 70) {
        el.classList.add('bg-success');
    } else if (percentage >= 50) {
        el.classList.add('bg-warning');
    } else {
        el.classList.add('bg-danger');
    }
}

function getScoreColor(score) {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'danger';
}

// Results page specific functionality
function initializeResultsPage() {
    // Animate score badges on page load
    animateScoreBadges();
    
    // Initialize skill gap analysis
    initializeSkillGapAnalysis();
    
    // Initialize charts
    initResultsCharts();
    
    // Setup download report button
    setupDownloadReportButton();
    
    // Add scroll animations
    addScrollAnimations();
}

function animateScoreBadges() {
    const badges = document.querySelectorAll('.score-badge-value');
    badges.forEach((badge, index) => {
        const targetValue = parseInt(badge.textContent);
        if (isNaN(targetValue)) return;
        
        let currentValue = 0;
        const increment = targetValue / 50;
        const delay = index * 200; // Stagger animations
        
        setTimeout(() => {
            const timer = setInterval(() => {
                currentValue += increment;
                if (currentValue >= targetValue) {
                    currentValue = targetValue;
                    clearInterval(timer);
                }
                badge.textContent = Math.round(currentValue);
            }, 30);
        }, delay);
    });
}

function initializeSkillGapAnalysis() {
    // Add click handlers to skill tags
    const skillTags = document.querySelectorAll('.skill-tag');
    skillTags.forEach(tag => {
        tag.addEventListener('click', function() {
            const skillName = this.textContent;
            showSkillDetails(skillName, this.classList.contains('strong') ? 'strong' : 
                           this.classList.contains('improvement') ? 'improvement' : 'recommended');
        });
    });
}

function showSkillDetails(skillName, type) {
    const messages = {
        strong: `Great! You have strong experience with ${skillName}. This is a key strength for this position.`,
        improvement: `${skillName} is mentioned in the job requirements but not prominently featured in your resume. Consider highlighting related experience.`,
        recommended: `Learning ${skillName} would significantly improve your match for this type of position.`
    };
    
    showAlert(messages[type] || `Information about ${skillName}`, 'info');
}

function setupDownloadReportButton() {
    const downloadBtn = document.getElementById('downloadReportBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            downloadReport();
        });
    }
}

// Global download report function
function downloadReport() {
    // Show loading state
    const downloadBtns = document.querySelectorAll('[onclick="downloadReport()"], #downloadReportBtn, .btn[onclick*="downloadReport"]');
    downloadBtns.forEach(btn => {
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Generating...';
        btn.disabled = true;
        btn.setAttribute('data-original-text', originalText);
    });
    
    // Call the server endpoint to generate PDF
    fetch('/download-report')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to generate report');
            }
            return response.blob();
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Get filename with timestamp
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            a.download = `CareerBERT_Report_${timestamp}.pdf`;
            
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            // Show success message
            showAlert('Report downloaded successfully!', 'success');
        })
        .catch(error => {
            console.error('Error downloading report:', error);
            showAlert('Failed to generate report. Please try again.', 'danger');
        })
        .finally(() => {
            // Reset button state
            downloadBtns.forEach(btn => {
                const originalText = btn.getAttribute('data-original-text') || '<i class="bi bi-download me-2"></i>Download Report';
                btn.innerHTML = originalText;
                btn.disabled = false;
                btn.removeAttribute('data-original-text');
            });
        });
}

// Make downloadReport available globally
window.downloadReport = downloadReport;

function addScrollAnimations() {
    // Add fade-in animation to cards as they come into view
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);
    
    // Observe all cards
    const cards = document.querySelectorAll('.card, .score-badge-card');
    cards.forEach(card => {
        observer.observe(card);
    });
}

// Enhanced skill gap analysis with dynamic content
function generateSkillGapAnalysis() {
    // This would typically be called with actual analysis data
    const skillData = {
        strong: ['Python', 'JavaScript', 'React.js', 'Node.js', 'SQL'],
        improvement: ['Docker', 'AWS', 'GraphQL', 'TypeScript'],
        recommended: ['Microservices', 'CI/CD', 'Testing', 'DevOps']
    };
    
    // Update skill tags dynamically
    updateSkillTags('strongMatches', skillData.strong, 'strong');
    updateSkillTags('improvementAreas', skillData.improvement, 'improvement');
    updateSkillTags('recommendedLearning', skillData.recommended, 'recommended');
}

function updateSkillTags(containerId, skills, type) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = '';
    skills.forEach(skill => {
        const tag = document.createElement('span');
        tag.className = `skill-tag ${type}`;
        tag.textContent = skill;
        tag.addEventListener('click', () => showSkillDetails(skill, type));
        container.appendChild(tag);
    });
}

// Initialize results page if we're on the results page
if (window.location.pathname.includes('/results')) {
    document.addEventListener('DOMContentLoaded', () => {
        initializeResultsPage();
        // Initialize charts immediately with default values
        setTimeout(initResultsCharts, 100);
    });
}
if (window.location.pathname.includes('/results-page')) {
    document.addEventListener('DOMContentLoaded', () => {
        initializeResultsPage();
        // Initialize charts immediately
        setTimeout(initResultsCharts, 100);
        fetchAndRenderResults();
    });
    window.addEventListener('load', () => {
        // Ensure fetch runs once page fully loaded
        if (!currentResults) {
            fetchAndRenderResults();
            // Retry once after a short delay in case server results arrive just after redirect
            setTimeout(() => {
                if (!currentResults) {
                    fetchAndRenderResults();
                } else {
                    // Update charts with real data
                    initResultsCharts();
                }
            }, 300);
        }
    });
}

// Chart.js: Results charts (bar and pie) with placeholder values
let scoresBarChartInstance = null;
let skillsPieChartInstance = null;

let currentResults = null;

function initResultsCharts() {
    // Prefer server-provided values if available
    const overall = currentResults?.overall ?? 72;
    const jobdesc = currentResults?.job_match ?? 68;
    const skills = currentResults?.skills_match ?? 75;
    const skillsMissing = Math.max(0, 100 - skills);

    // Create gradients for charts
    const createGradient = (ctx, color1, color2) => {
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, color1);
        gradient.addColorStop(1, color2);
        return gradient;
    };

    // Bar chart: Overall / JobDesc / Skills with advanced styling
    const barCanvas = document.getElementById('scoreChart');
    if (barCanvas && window.Chart) {
        const ctxBar = barCanvas.getContext('2d');
        if (scoresBarChartInstance) {
            scoresBarChartInstance.destroy();
        }
        
        // Add loaded class to container
        const barContainer = barCanvas.closest('.chart-container');
        if (barContainer) {
            barContainer.classList.add('loaded');
        }

        // Create gradients for each bar
        const overallGradient = createGradient(ctxBar, '#2563EB', '#1D4ED8');
        const jobdescGradient = createGradient(ctxBar, '#9333EA', '#7C3AED');
        const skillsGradient = createGradient(ctxBar, '#10B981', '#059669');

        scoresBarChartInstance = new Chart(ctxBar, {
            type: 'bar',
            data: {
                labels: ['Compatibility Score', 'Experience Match', 'Technical Fit'],
                datasets: [{
                    label: 'Match Score',
                    data: [overall, jobdesc, skills],
                    backgroundColor: [overallGradient, jobdescGradient, skillsGradient],
                    borderColor: ['#2563EB', '#9333EA', '#10B981'],
                    borderWidth: 2,
                    borderRadius: 12,
                    borderSkipped: false,
                    maxBarThickness: 60,
                    hoverBackgroundColor: ['#1D4ED8', '#7C3AED', '#059669'],
                    hoverBorderWidth: 3,
                    hoverBorderColor: ['#1E40AF', '#6D28D9', '#047857']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 800,
                    easing: 'easeOutQuart'
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#6B7280',
                            font: {
                                size: 12,
                                weight: '500'
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(107, 114, 128, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#6B7280',
                            font: {
                                size: 11
                            },
                            callback: (value) => value + '%'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        titleColor: '#F9FAFB',
                        bodyColor: '#E5E7EB',
                        borderColor: '#374151',
                        borderWidth: 1,
                        cornerRadius: 12,
                        displayColors: true,
                        padding: 12,
                        titleFont: {
                            size: 14,
                            weight: '600'
                        },
                        bodyFont: {
                            size: 13
                        },
                        callbacks: {
                            title: (ctx) => ctx[0].label,
                            label: (ctx) => `Score: ${ctx.parsed.y}%`,
                            afterLabel: (ctx) => {
                                const score = ctx.parsed.y;
                                if (score >= 80) return '🎉 Excellent match!';
                                if (score >= 70) return '👍 Good match';
                                if (score >= 60) return '⚡ Fair match';
                                return '💪 Room for improvement';
                            }
                        }
                    }
                }
            }
        });
    }

    // Advanced Doughnut chart: Matched vs Missing skills
    const pieCanvas = document.getElementById('pieChart');
    if (pieCanvas && window.Chart) {
        const ctxPie = pieCanvas.getContext('2d');
        if (skillsPieChartInstance) {
            skillsPieChartInstance.destroy();
        }
        
        // Add loaded class to container
        const pieContainer = pieCanvas.closest('.chart-container');
        if (pieContainer) {
            pieContainer.classList.add('loaded');
        }

        // Create gradients for pie chart
        const matchedGradient = createGradient(ctxPie, '#10B981', '#059669');
        const missingGradient = createGradient(ctxPie, '#E5E7EB', '#D1D5DB');

        skillsPieChartInstance = new Chart(ctxPie, {
            type: 'doughnut',
            data: {
                labels: ['Matched Skills', 'Missing Skills'],
                datasets: [{
                    data: [skills, skillsMissing],
                    backgroundColor: [matchedGradient, missingGradient],
                    borderColor: ['#10B981', '#D1D5DB'],
                    borderWidth: 3,
                    hoverBackgroundColor: ['#059669', '#9CA3AF'],
                    hoverBorderColor: ['#047857', '#6B7280'],
                    hoverBorderWidth: 4,
                    cutout: '65%',
                    spacing: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 600,
                    easing: 'easeOutQuart'
                },
                interaction: {
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 20,
                            font: {
                                size: 13,
                                weight: '500'
                            },
                            color: '#6B7280',
                            generateLabels: (chart) => {
                                const data = chart.data;
                                return data.labels.map((label, i) => ({
                                    text: `${label} (${data.datasets[0].data[i]}%)`,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    strokeStyle: data.datasets[0].borderColor[i],
                                    lineWidth: 2,
                                    pointStyle: 'circle',
                                    hidden: false,
                                    index: i
                                }));
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        titleColor: '#F9FAFB',
                        bodyColor: '#E5E7EB',
                        borderColor: '#374151',
                        borderWidth: 1,
                        cornerRadius: 12,
                        displayColors: true,
                        padding: 12,
                        titleFont: {
                            size: 14,
                            weight: '600'
                        },
                        bodyFont: {
                            size: 13
                        },
                        callbacks: {
                            title: (ctx) => ctx[0].label,
                            label: (ctx) => `${ctx.parsed}% of total skills`,
                            afterLabel: (ctx) => {
                                const isMatched = ctx.dataIndex === 0;
                                return isMatched ? '✅ Skills you have' : '📚 Skills to learn';
                            }
                        }
                    }
                }
            },
            plugins: [{
                id: 'centerText',
                beforeDraw: (chart) => {
                    const { ctx, chartArea: { top, width, height } } = chart;
                    ctx.save();
                    
                    const centerX = width / 2;
                    const centerY = top + height / 2;
                    
                    // Draw center text
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    
                    // Main percentage
                    ctx.font = 'bold 28px Inter, sans-serif';
                    ctx.fillStyle = '#1F2937';
                    ctx.fillText(`${skills}%`, centerX, centerY - 8);
                    
                    // Label
                    ctx.font = '500 14px Inter, sans-serif';
                    ctx.fillStyle = '#6B7280';
                    ctx.fillText('Skills Match', centerX, centerY + 16);
                    
                    ctx.restore();
                }
            }]
        });
    }
}

// Export functions for use in other scripts
window.CareerBERT = {
    showAlert: function(message, type) {
        // This will be available globally
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    },
    
    // Results page functions
    animateScoreBadges: animateScoreBadges,
    generateSkillGapAnalysis: generateSkillGapAnalysis
};
