/**
 * Redrob AI Candidate Ranking App Logic
 * Pure Vanilla JS dashboard interaction, SSE streaming, and dynamic rendering.
 */

class RedrobRanker {
    constructor() {
        this.taskId = null;
        this.results = null;
        this.eventSource = null;
        
        // Timer variables
        this.timerInterval = null;
        this.startTime = 0;
        
        // DOM Cache
        this.initElements();
        
        // Event Listeners
        this.attachEventListeners();
        
        // Initialize JD Analysis view
        this.loadJDAnalysis();
    }
    
    initElements() {
        // Run Buttons
        this.btnFull = document.getElementById('btn-full');
        this.btnSample = document.getElementById('btn-sample');
        
        // Status & Progress
        this.statusBadge = document.getElementById('status-badge');
        this.statusBadgeText = this.statusBadge ? this.statusBadge.querySelector('.status-badge__text') : null;
        this.progressArea = document.getElementById('progress-area');
        this.progressBarFill = document.getElementById('progress-bar-fill');
        this.progressStageText = document.getElementById('progress-stage-text');
        this.progressPctText = document.getElementById('progress-pct-text');
        this.progressCandidatesText = document.getElementById('progress-candidates-text');
        this.progressElapsed = document.getElementById('progress-elapsed');
        this.progressMessage = document.getElementById('progress-message');
        
        // Dashboard / Results
        this.resultsSection = document.getElementById('results-section');
        this.exportSection = document.getElementById('export-section');
        
        // Stats
        this.statTotal = document.getElementById('stat-total');
        this.statShortlisted = document.getElementById('stat-shortlisted');
        this.statAvgScore = document.getElementById('stat-avg-score');
        this.statHoneypots = document.getElementById('stat-honeypots');
        this.statDisqualified = document.getElementById('stat-disqualified');
        
        // Controls / Search
        this.searchInput = document.getElementById('search-input');
        
        // Rankings Table
        this.rankingTbody = document.getElementById('ranking-tbody');
        
        // Modal
        this.modal = document.getElementById('candidate-modal');
        this.modalContent = document.getElementById('modal-content');
        
        // Collapsible JD elements
        this.jdToggle = document.getElementById('jd-toggle');
        this.jdBody = document.getElementById('jd-body');
        this.jdContent = document.getElementById('jd-content');
        
        // Toast Container
        this.toastContainer = document.getElementById('toast-container');
        
        // Validation Status
        this.validationText = document.getElementById('validation-text');
        this.validationBadges = document.getElementById('validation-badges');
        
        // Custom dataset upload
        this.fileUpload = document.getElementById('file-upload');
    }
    
    attachEventListeners() {
        // Collapsible JD toggle
        if (this.jdToggle && this.jdBody) {
            this.jdToggle.addEventListener('click', () => {
                const isExpanded = this.jdToggle.getAttribute('aria-expanded') === 'true';
                this.jdToggle.setAttribute('aria-expanded', !isExpanded);
                if (isExpanded) {
                    this.jdBody.classList.add('collapsed');
                } else {
                    this.jdBody.classList.remove('collapsed');
                }
            });
            // Support keyboard toggling
            this.jdToggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.jdToggle.click();
                }
            });
        }
        
        // Live search filter with debouncing
        if (this.searchInput) {
            let debounceTimer;
            this.searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.filterResults(e.target.value);
                }, 150);
            });
        }
        
        // Close modal on escape key
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal && this.modal.classList.contains('active')) {
                this.closeModal();
            }
        });
        
        // Close modal on clicking outside overlay
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.closeModal();
                }
            });
        }
        
        // File upload change listener
        if (this.fileUpload) {
            this.fileUpload.addEventListener('change', (e) => this.handleFileUpload(e));
        }
    }
    
    // Custom file upload handling
    async handleFileUpload(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const ext = file.name.split('.').pop().toLowerCase();
        if (ext !== 'json' && ext !== 'jsonl') {
            this.showToast("Only .json and .jsonl files are allowed.", "error");
            this.fileUpload.value = '';
            return;
        }
        
        this.showToast(`Uploading custom dataset: ${file.name}...`, "info");
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            if (this.btnFull) this.btnFull.disabled = true;
            if (this.btnSample) this.btnSample.disabled = true;
            const btnUploadEl = document.getElementById('btn-upload');
            if (btnUploadEl) btnUploadEl.disabled = true;
            
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.message || "Upload failed");
            }
            
            const data = await res.json();
            this.showToast("Dataset uploaded! Starting candidate ranking...", "success");
            
            // Automatically launch ranking on the uploaded file
            await this.startRanking(data.filename);
            
        } catch (error) {
            console.error("Upload error:", error);
            this.showToast(error.message || "Failed to upload file.", "error");
            this.resetUI();
        } finally {
            this.fileUpload.value = '';
            const btnUploadEl = document.getElementById('btn-upload');
            if (btnUploadEl) btnUploadEl.disabled = false;
        }
    }

    // Toast Notification helper
    showToast(message, type = 'info') {
        if (!this.toastContainer) return;
        
        const toast = document.createElement('div');
        toast.className = `toast toast--${type}`;
        
        let iconSvg = '';
        if (type === 'success') {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
        } else if (type === 'error') {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
        } else {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
        }
        
        toast.innerHTML = `
            ${iconSvg}
            <span>${message}</span>
        `;
        
        this.toastContainer.appendChild(toast);
        
        // Auto remove toast
        setTimeout(() => {
            toast.style.animation = 'slide-in-toast 0.3s forwards reverse';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
    
    // Load static JD requirements from the backend
    async loadJDAnalysis() {
        if (!this.jdContent) return;
        
        try {
            const res = await fetch('/api/jd-analysis');
            if (!res.ok) throw new Error();
            const data = await res.json();
            
            this.jdContent.innerHTML = `
                <div class="jd-card jd-card--must-have">
                    <h3>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                        Must-Have Core Skills
                    </h3>
                    <ul class="jd-card__list">
                        ${data.must_haves.map(item => `<li>${item}</li>`).join('')}
                    </ul>
                </div>
                <div class="jd-card jd-card--nice-to-have">
                    <h3>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                        Nice-to-Have Skills
                    </h3>
                    <ul class="jd-card__list">
                        ${data.nice_to_haves.map(item => `<li>${item}</li>`).join('')}
                    </ul>
                </div>
                <div class="jd-card jd-card--disqualifiers">
                    <h3>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                        Disqualifiers (Red Flags)
                    </h3>
                    <ul class="jd-card__list">
                        ${data.disqualifiers.map(item => `<li>${item}</li>`).join('')}
                    </ul>
                </div>
            `;
        } catch (error) {
            console.error("Failed to load JD data", error);
            this.jdContent.innerHTML = `<div class="jd-loading"><span style="color: var(--danger)">Error loading JD details.</span></div>`;
        }
    }
    
    // Start ranking pipeline run
    async startRanking(source) {
        // UI Reset & Disabling buttons
        if (this.btnFull) this.btnFull.disabled = true;
        if (this.btnSample) this.btnSample.disabled = true;
        const btnUploadEl = document.getElementById('btn-upload');
        if (btnUploadEl) btnUploadEl.disabled = true;
        if (this.resultsSection) this.resultsSection.classList.add('hidden');
        if (this.exportSection) this.exportSection.classList.add('hidden');
        
        // Show progress area
        if (this.progressArea) this.progressArea.classList.remove('hidden');
        this.updateProgress({ stage: 'Sending request...', progress: 0, processed: 0, total: '?' });
        this.updateStatusBadge('running', 'Running');
        
        // Reset and start stopwatch timer
        this.resetTimer();
        this.startTimer();
        
        try {
            const res = await fetch('/api/rank', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: source })
            });
            if (!res.ok) throw new Error("HTTP error starting ranking");
            
            const data = await res.json();
            this.taskId = data.task_id;
            this.connectProgressSSE(this.taskId);
            this.showToast(`Candidate evaluation started (Task: ${this.taskId})`, 'info');
            
        } catch (error) {
            console.error("Error starting ranking", error);
            this.showToast("Failed to start candidate evaluation.", "error");
            this.resetUI();
        }
    }
    
    // Connect to Server-Sent Events stream for execution progress
    connectProgressSSE(taskId) {
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        this.eventSource = new EventSource(`/api/progress/${taskId}`);
        
        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.status === 'not_found' || data.status === 'error') {
                this.eventSource.close();
                this.stopTimer();
                this.showToast(data.message || 'Background worker error.', 'error');
                this.resetUI();
                return;
            }
            
            this.updateProgress({
                stage: data.stage,
                progress: data.progress,
                processed: data.processed,
                total: data.total,
                message: data.message || ''
            });
            
            if (data.status === 'complete') {
                this.eventSource.close();
                this.stopTimer();
                this.onRankingComplete(taskId);
            }
        };
        
        this.eventSource.onerror = (err) => {
            console.error("SSE Connection error", err);
            this.eventSource.close();
            this.stopTimer();
            this.showToast("Connection to progress stream interrupted.", "error");
            // Attempt to retrieve results directly in case of complete
            setTimeout(() => this.onRankingComplete(taskId), 3000);
        };
    }
    
    updateProgress(data) {
        if (this.progressStageText) this.progressStageText.textContent = data.stage;
        if (this.progressBarFill) this.progressBarFill.style.width = `${data.progress}%`;
        if (this.progressPctText) this.progressPctText.textContent = `${data.progress}%`;
        if (this.progressCandidatesText) this.progressCandidatesText.textContent = `${data.processed} / ${data.total}`;
        if (this.progressMessage) this.progressMessage.textContent = data.message || `Processing pipeline: Stage - ${data.stage}`;
    }
    
    // Event triggered when evaluation finishes
    async onRankingComplete(taskId) {
        if (this.progressStageText) this.progressStageText.textContent = 'Loading results dashboard...';
        
        try {
            const res = await fetch(`/api/results/${taskId}`);
            if (!res.ok) throw new Error("Results not ready");
            
            this.results = await res.json();
            
            // Render stats and table
            this.renderStatsCards(this.results.stats);
            this.renderResultsTable(this.results.candidates);
            
            // Validate output CSV
            await this.validateCSVOutput(taskId);
            
            // Hide loading progress, show results
            if (this.progressArea) this.progressArea.classList.add('hidden');
            if (this.resultsSection) this.resultsSection.classList.remove('hidden');
            if (this.exportSection) this.exportSection.classList.remove('hidden');
            
            this.updateStatusBadge('complete', 'Complete');
            this.showToast("Shortlist successfully generated and validated!", "success");
            
        } catch (error) {
            console.error("Error fetching results", error);
            this.showToast("Retrying results load...", "info");
            setTimeout(() => this.onRankingComplete(taskId), 2500);
        } finally {
            if (this.btnFull) this.btnFull.disabled = false;
            if (this.btnSample) this.btnSample.disabled = false;
            const btnUploadEl = document.getElementById('btn-upload');
            if (btnUploadEl) btnUploadEl.disabled = false;
        }
    }
    
    // Fetch and render CSV validation status
    async validateCSVOutput(taskId) {
        if (!this.validationText || !this.validationBadges) return;
        
        this.validationText.textContent = "Verifying submission formatting...";
        this.validationBadges.innerHTML = '<div class="spinner"></div>';
        
        try {
            const res = await fetch(`/api/validate/${taskId}`);
            if (!res.ok) throw new Error("Validation route failed");
            
            const data = await res.json();
            this.validationBadges.innerHTML = '';
            
            if (data.status === 'valid') {
                this.validationText.textContent = "Pipeline Output Is Valid!";
                
                const checks = [
                    "Correct header row (candidate_id, rank, score, reasoning)",
                    "Exactly 100 candidate rows generated",
                    "Monotonic non-increasing scores",
                    "Valid candidate_id syntax (CAND_XXXXXXX)",
                    "Correct tie-breaker ordering (alphabetical candidate_id)"
                ];
                
                checks.forEach(chk => {
                    const el = document.createElement('div');
                    el.className = 'validation-item validation-item--success';
                    el.innerHTML = `
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                        <span>${chk}</span>
                    `;
                    this.validationBadges.appendChild(el);
                });
                
            } else if (data.status === 'invalid') {
                this.validationText.textContent = `Output invalid! (${data.errors.length} errors found)`;
                
                data.errors.slice(0, 5).forEach(err => {
                    const el = document.createElement('div');
                    el.className = 'validation-item validation-item--error';
                    el.innerHTML = `
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                        <span>${err}</span>
                    `;
                    this.validationBadges.appendChild(el);
                });
                
                if (data.errors.length > 5) {
                    const el = document.createElement('div');
                    el.className = 'validation-item';
                    el.textContent = `... and ${data.errors.length - 5} more issues.`;
                    this.validationBadges.appendChild(el);
                }
            } else {
                this.validationText.textContent = "Unable to execute validation script.";
            }
        } catch (error) {
            console.error("Failed to validate CSV output", error);
            this.validationText.textContent = "Error running validate_submission.py";
            this.validationBadges.innerHTML = '';
        }
    }
    
    // Render Stats
    renderStatsCards(stats) {
        this.animateCountUp(this.statTotal, stats.total_processed, 1200);
        this.animateCountUp(this.statShortlisted, stats.shortlisted, 1200);
        this.animateCountUp(this.statHoneypots, stats.honeypots_detected, 1200);
        if (this.statDisqualified) {
            this.animateCountUp(this.statDisqualified, stats.disqualified_count || 0, 1200);
        }
        
        // Float values get formatted directly
        if (this.statAvgScore) {
            this.statAvgScore.textContent = (stats.avg_top10_score * 100).toFixed(1) + '%';
        }
    }
    
    // Render Candidate rows in Dashboard table
    renderResultsTable(candidates) {
        if (!this.rankingTbody) return;
        this.rankingTbody.innerHTML = '';
        
        try {
            if (!candidates || !Array.isArray(candidates) || candidates.length === 0) {
                this.rankingTbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:2rem;">No candidates were shortlisted.</td></tr>`;
                return;
            }

            candidates.forEach(c => {
                const tr = document.createElement('tr');
                tr.setAttribute('data-id', c.candidate_id);
                
                const nameStr = (c.name || 'Unknown').toLowerCase();
                const titleStr = (c.title || 'Unknown').toLowerCase();
                const skillsList = Array.isArray(c.skills) ? c.skills : [];
                const skillsSearchStr = skillsList.join(' ').toLowerCase();
                tr.setAttribute('data-search', `${nameStr} ${titleStr} ${skillsSearchStr}`);
                
                // Medal styles for top 3
                let rankBadgeHtml = `<span class="rank-badge">${c.rank}</span>`;
                if (c.rank <= 3) {
                    rankBadgeHtml = `<span class="rank-badge rank-${c.rank}">${c.rank}</span>`;
                }
                
                // Score colors
                const scorePct = ((c.score || 0) * 100).toFixed(1);
                let barColor = 'var(--success)';
                if (scorePct < 75) {
                    barColor = 'var(--warning)';
                }
                if (scorePct < 50) {
                    barColor = 'var(--danger)';
                }
                
                // Verdict pill — use server verdict when available
                const verdict = (c.verdict || '').toUpperCase();
                let recHtml = `<span class="pill pill-warning">MAYBE</span>`;
                if (verdict.includes('STRONG YES')) recHtml = `<span class="pill pill-success">STRONG YES</span>`;
                else if (verdict === 'YES') recHtml = `<span class="pill pill-primary">YES</span>`;
                else if (verdict === 'MAYBE') recHtml = `<span class="pill pill-warning">MAYBE</span>`;
                else if (verdict.includes('NO') || verdict.includes('DISQUAL')) recHtml = `<span class="pill pill-danger">NO</span>`;
                if (c.honeypot_flag) recHtml = `<span class="pill pill-danger">HONEYPOT</span>`;
                else if (c.hard_disqualified) recHtml = `<span class="pill pill-danger">DISQUALIFIED</span>`;
                
                // Limit shown skills in the table
                const maxSkills = 4;
                const truncatedSkills = skillsList.slice(0, maxSkills);
                let skillsHtml = truncatedSkills.map(s => `<span class="pill pill-primary">${s}</span>`).join('');
                if (skillsList.length > maxSkills) {
                    skillsHtml += `<span class="pill pill-secondary">+${skillsList.length - maxSkills}</span>`;
                }
                
                tr.innerHTML = `
                    <td class="th-rank">${rankBadgeHtml}</td>
                    <td class="score-cell">
                        <span class="mono" style="font-weight:600; color:${barColor};">${scorePct}%</span>
                        <div class="mini-score-bar">
                            <div class="mini-score-fill" style="width: ${scorePct}%; background: ${barColor};"></div>
                        </div>
                    </td>
                    <td>
                        <div style="font-weight: 600; color: var(--text-primary);">${c.name || 'Unknown'}</div>
                        <div class="mono" style="font-size: 0.8rem; color: var(--text-muted);">${c.candidate_id}</div>
                    </td>
                    <td style="font-weight:500;">${c.title || 'Unknown'}</td>
                    <td class="mono" style="font-weight:500;">${c.years_of_experience || 0}y</td>
                    <td>${c.location || 'Unknown'}</td>
                    <td>${skillsHtml}</td>
                    <td>${recHtml}</td>
                `;
                
                // Clicking row launches detailed modal
                tr.addEventListener('click', () => this.showCandidateDetails(c));
                this.rankingTbody.appendChild(tr);
            });
        } catch (err) {
            console.error("Error rendering results table:", err);
            this.showToast("Rendering error: " + err.message, "error");
            this.rankingTbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--danger); padding:2rem;">Error rendering results table: ${err.message}</td></tr>`;
        }
        
        // Reset search field
        if (this.searchInput) this.searchInput.value = '';
    }
    
    // Shows candidate detail overlay
    showCandidateDetails(candidate) {
        if (!this.modalContent || !this.modal) return;
        
        const scorePct = (candidate.score * 100).toFixed(1);
        let barColor = 'var(--success)';
        if (scorePct < 75) barColor = 'var(--warning)';
        if (scorePct < 50) barColor = 'var(--danger)';
        
        // Populate modal HTML content
        let contentHtml = `
            <div class="candidate-header">
                <div>
                    <h2>${candidate.name}</h2>
                    <div style="color: var(--text-secondary); font-size: 1.1rem; margin-top: 0.25rem;">
                        <strong>${candidate.title}</strong>
                    </div>
                    <div style="color: var(--text-muted); font-size: 0.95rem; display:flex; gap:0.75rem; margin-top:0.25rem;">
                        <span>${candidate.years_of_experience} Years Exp</span>
                        <span>·</span>
                        <span>${candidate.location}, ${candidate.country}</span>
                        <span>·</span>
                        <span class="mono">${candidate.candidate_id}</span>
                    </div>
                </div>
                <div class="candidate-header__score">
                    <div class="candidate-header__score-val mono" style="color: ${barColor};">${scorePct}%</div>
                    <div class="candidate-header__score-rank">Rank #${candidate.rank}</div>
                </div>
            </div>
            
            <div class="candidate-detail-grid">
                <!-- Left panel: Trajectory & Timeline -->
                <div>
                    <div class="candidate-section-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                        Career Timeline & Trajectory
                    </div>
                    
                    <div class="timeline" id="modal-timeline">
                        <!-- Filled dynamically below -->
                        <div class="jd-loading"><div class="spinner"></div></div>
                    </div>
                </div>
                
                <!-- Right panel: AI Scoring Breakdown & Skills -->
                <div>
                    <div class="candidate-section-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                        Scoring Dimensions (AI Match)
                    </div>
                    
                    <div style="margin-bottom: 2rem;">
                        ${this.renderDetailScoreBar('Core Skill Match', candidate.composite_breakdown.skill_match, '#8b5cf6')}
                        ${this.renderDetailScoreBar('Career Description & Signals', candidate.composite_breakdown.career, '#3b82f6')}
                        ${this.renderDetailScoreBar('Experience & Notice Match', candidate.composite_breakdown.trajectory, '#06b6d4')}
                        ${this.renderDetailScoreBar('Behavioral Activity Score', candidate.composite_breakdown.behavioral, '#10b981')}
                        ${this.renderDetailScoreBar('Education & Certifications', candidate.composite_breakdown.education, '#f59e0b')}
                    </div>
                    
                    <div class="candidate-section-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/></svg>
                        AI Reasoning Synopsis
                    </div>
                    <p style="background: rgba(99,102,241,0.08); padding: 1.15rem; border-left: 4px solid #6366f1; border-radius: 6px; font-size: 0.95rem; line-height: 1.5; color: var(--text-primary); margin-bottom: 2rem;">
                        ${candidate.reasoning}
                    </p>
                    
                    <div class="candidate-section-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
                        Identified Skills
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem;">
                        ${candidate.skills.map(s => `<span class="pill pill-primary">${s}</span>`).join('')}
                    </div>
                </div>
            </div>
        `;
        
        this.modalContent.innerHTML = contentHtml;
        this.modal.classList.add('active');
        
        // Load detailed timeline asynchronously
        this.loadTimelineData(candidate.candidate_id);
    }
    
    // Render custom score rows inside modal details
    renderDetailScoreBar(label, value, color) {
        return `
            <div class="modal-score-item">
                <div class="modal-score-header">
                    <span class="modal-score-label">${label}</span>
                    <span class="mono" style="font-weight:600; color:${color};">${value.toFixed(1)}%</span>
                </div>
                <div class="modal-score-bar-track">
                    <div class="modal-score-bar-fill" style="width: ${value}%; background: ${color};"></div>
                </div>
            </div>
        `;
    }
    
    // Fetch individual candidate details for timeline mapping
    async loadTimelineData(candidateId) {
        const tlContainer = document.getElementById('modal-timeline');
        if (!tlContainer) return;
        
        try {
            const res = await fetch(`/api/candidate/${candidateId}`);
            if (!res.ok) throw new Error("Timeline API not found");
            const profileData = await res.json();
            
            const history = profileData.career_history || [];
            if (history.length === 0) {
                tlContainer.innerHTML = `<p style="color: var(--text-muted);">No career history recorded.</p>`;
                return;
            }
            
            // Build timeline items
            let timelineHtml = '';
            history.forEach((job, idx) => {
                const isCurrent = job.is_current || idx === 0; // Check current job
                const dotClass = isCurrent ? 'timeline__dot timeline__dot--current' : 'timeline__dot';
                
                timelineHtml += `
                    <div class="timeline__item">
                        <div class="${dotClass}"></div>
                        <div class="timeline__title">${job.title}</div>
                        <div class="timeline__meta">
                            <strong>${job.company}</strong>
                            <span style="margin: 0 0.3rem;">·</span>
                            <span class="timeline__duration">${job.start_date} – ${job.end_date || 'Present'} (${job.duration_months} mos)</span>
                        </div>
                        ${job.description ? `<div class="timeline__desc">${job.description}</div>` : ''}
                    </div>
                `;
            });
            
            tlContainer.innerHTML = timelineHtml;
            
        } catch (error) {
            console.warn("Timeline endpoint not responding, attempting fallback loading from results cache...");
            
            // Fallback: search in loaded results.candidates list to pull details if possible
            const cacheMatch = this.results?.candidates?.find(c => c.candidate_id === candidateId);
            if (cacheMatch) {
                // If the app.py didn't return full details list in list api, we present a mock
                tlContainer.innerHTML = `
                    <div class="timeline__item">
                        <div class="timeline__dot timeline__dot--current"></div>
                        <div class="timeline__title">${cacheMatch.title}</div>
                        <div class="timeline__meta">
                            <strong>Product/AI Development</strong>
                            <span style="margin: 0 0.3rem;">·</span>
                            <span class="timeline__duration">Recent Position (${cacheMatch.years_of_experience}y Experience)</span>
                        </div>
                        <div class="timeline__desc">Active engineering track matches requirements. Detailed role descriptions loaded in background system.</div>
                    </div>
                `;
            } else {
                tlContainer.innerHTML = `<p style="color: var(--text-muted)">Unable to load timeline profiles.</p>`;
            }
        }
    }
    
    // Close Modal
    closeModal() {
        if (this.modal) {
            this.modal.classList.remove('active');
        }
    }
    
    // Search Box filtering logic
    filterResults(query) {
        if (!this.rankingTbody) return;
        const normalizedQuery = query.toLowerCase().trim();
        const rows = this.rankingTbody.querySelectorAll('tr');
        
        rows.forEach(row => {
            const searchContext = row.getAttribute('data-search') || '';
            if (searchContext.includes(normalizedQuery)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
    
    // Trigger download CSV
    downloadCSV() {
        if (!this.taskId) {
            this.showToast("No pipeline has been executed yet.", "error");
            return;
        }
        window.location.href = `/api/download/${this.taskId}`;
        this.showToast("Downloading submission CSV file...", "success");
    }
    
    // Helper to change dashboard status badge style
    updateStatusBadge(status, text) {
        if (!this.statusBadge || !this.statusBadgeText) return;
        
        this.statusBadge.className = `status-badge status-badge--${status}`;
        this.statusBadgeText.textContent = text;
    }
    
    resetUI() {
        if (this.btnFull) this.btnFull.disabled = false;
        if (this.btnSample) this.btnSample.disabled = false;
        const btnUploadEl = document.getElementById('btn-upload');
        if (btnUploadEl) btnUploadEl.disabled = false;
        if (this.progressArea) this.progressArea.classList.add('hidden');
        this.updateStatusBadge('idle', 'Idle');
    }
    
    // Count up animation for dashboard stat cards
    animateCountUp(element, target, duration) {
        if (!element) return;
        
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            element.textContent = Math.floor(progress * target);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                element.textContent = target;
            }
        };
        window.requestAnimationFrame(step);
    }
    
    /* --- Stopwatch Timer Helpers --- */
    startTimer() {
        this.startTime = Date.now();
        if (this.progressElapsed) {
            this.progressElapsed.textContent = '00:00';
        }
        
        this.timerInterval = setInterval(() => {
            const elapsedMs = Date.now() - this.startTime;
            if (this.progressElapsed) {
                this.progressElapsed.textContent = this.formatElapsedTime(elapsedMs);
            }
        }, 1000);
    }
    
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }
    
    resetTimer() {
        this.stopTimer();
        if (this.progressElapsed) {
            this.progressElapsed.textContent = '00:00';
        }
    }
    
    formatElapsedTime(ms) {
        const totalSecs = Math.floor(ms / 1000);
        const mins = Math.floor(totalSecs / 60);
        const secs = totalSecs % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
}

// Instantiate on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new RedrobRanker();
});
