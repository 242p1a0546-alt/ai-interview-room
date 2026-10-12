/**
 * AI Interview Room - Main Application Controller (Resume-Driven v3.0)
 * Handles resume PDF upload, drag-and-drop, AI resume analysis confirmation,
 * speech recognition, adaptive interview room, and resume-aware reporting.
 */

document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------
    // APPLICATION STATE
    // -------------------------------------------------------------
    const state = {
        sessionId: null,
        selectedFile: null,
        resumeData: null,
        currentQuestionNum: 1,
        isFollowup: false,
        difficulty: 'Medium',
        startTime: null,
        elapsedTimerInterval: null,
        webcamStream: null,
        isWebcamActive: false,
        isMutedTts: false,
        speech: null
    };

    // Initialize speech module
    state.speech = new window.InterviewSpeechModule();

    // -------------------------------------------------------------
    // DOM ELEMENTS
    // -------------------------------------------------------------
    // Views
    const homeView = document.getElementById('homeView');
    const setupView = document.getElementById('setupView');
    const roomView = document.getElementById('roomView');
    const reportView = document.getElementById('reportView');

    // Navigation & CTAs
    const navBrandLink = document.getElementById('navBrandLink');
    const navStartBtn = document.getElementById('navStartBtn');
    const heroStartBtn = document.getElementById('heroStartBtn');
    const heroHowItWorksBtn = document.getElementById('heroHowItWorksBtn');

    // Resume Upload & Confirmation Elements
    const resumeUploadCard = document.getElementById('resumeUploadCard');
    const resumeDropzone = document.getElementById('resumeDropzone');
    const browseFilesBtn = document.getElementById('browseFilesBtn');
    const resumeFileInput = document.getElementById('resumeFileInput');
    const selectedFileChip = document.getElementById('selectedFileChip');
    const selectedFileName = document.getElementById('selectedFileName');
    const selectedFileSize = document.getElementById('selectedFileSize');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const analyzeResumeBtn = document.getElementById('analyzeResumeBtn');
    const uploadProgressBanner = document.getElementById('uploadProgressBanner');

    const resumeConfirmationCard = document.getElementById('resumeConfirmationCard');
    const confirmedCandidateName = document.getElementById('confirmedCandidateName');
    const confirmedCandidateEducation = document.getElementById('confirmedCandidateEducation');
    const confirmedSkillsList = document.getElementById('confirmedSkillsList');
    const skillsCountBadge = document.getElementById('skillsCountBadge');
    const confirmedProjectsList = document.getElementById('confirmedProjectsList');
    const projectsCountBadge = document.getElementById('projectsCountBadge');
    const confirmedCertsList = document.getElementById('confirmedCertsList');
    const confirmedExpList = document.getElementById('confirmedExpList');
    const launchInterviewBtn = document.getElementById('launchInterviewBtn');
    const reuploadResumeBtn = document.getElementById('reuploadResumeBtn');

    // Room Elements
    const roomTypeBadge = document.getElementById('roomTypeBadge');
    const roomDifficultyBadge = document.getElementById('roomDifficultyBadge');
    const interviewElapsedTimer = document.getElementById('interviewElapsedTimer');
    const ttsVoiceToggle = document.getElementById('ttsVoiceToggle');
    const ttsIcon = document.getElementById('ttsIcon');
    const webcamToggle = document.getElementById('webcamToggle');
    const camIcon = document.getElementById('camIcon');
    const earlyEndBtn = document.getElementById('earlyEndBtn');

    const aiVideoCard = document.getElementById('aiVideoCard');
    const aiStatusText = document.getElementById('aiStatusText');
    const candidateDisplayName = document.getElementById('candidateDisplayName');
    const candidateDisplayCollege = document.getElementById('candidateDisplayCollege');
    const webcamVideoElement = document.getElementById('webcamVideoElement');
    const candidatePlaceholder = document.getElementById('candidatePlaceholder');
    const audioLevelMeter = document.getElementById('audioLevelMeter');
    const audioLevelFill = document.getElementById('audioLevelFill');

    const questionCounterLabel = document.getElementById('questionCounterLabel');
    const questionCategoryTag = document.getElementById('questionCategoryTag');
    const followupBadgeContainer = document.getElementById('followupBadgeContainer');
    const questionTextBox = document.getElementById('questionTextBox');

    // Mic & Answer Controls
    const micStatusIndicator = document.getElementById('micStatusIndicator');
    const micStatusText = document.getElementById('micStatusText');
    const recordingTimer = document.getElementById('recordingTimer');
    const liveTranscriptBox = document.getElementById('liveTranscriptBox');
    const startAnswerBtn = document.getElementById('startAnswerBtn');
    const stopAnswerBtn = document.getElementById('stopAnswerBtn');
    const retryAnswerBtn = document.getElementById('retryAnswerBtn');
    const submitAnswerBtn = document.getElementById('submitAnswerBtn');
    const evaluatingBanner = document.getElementById('evaluatingBanner');

    // Report Elements
    const reportScoreCircle = document.getElementById('reportScoreCircle');
    const reportOverallScore = document.getElementById('reportOverallScore');
    const reportRecBadge = document.getElementById('reportRecBadge');
    const reportCandidateTitle = document.getElementById('reportCandidateTitle');
    const reportSummaryVerdict = document.getElementById('reportSummaryVerdict');
    const reportMetaEducation = document.getElementById('reportMetaEducation');
    const reportMetaSkills = document.getElementById('reportMetaSkills');
    const reportMetaQuestions = document.getElementById('reportMetaQuestions');
    const reportMetaDuration = document.getElementById('reportMetaDuration');

    const metricAccuracyVal = document.getElementById('metricAccuracyVal');
    const metricAccuracyBar = document.getElementById('metricAccuracyBar');
    const metricProjVal = document.getElementById('metricProjVal');
    const metricProjBar = document.getElementById('metricProjBar');
    const metricAuthVal = document.getElementById('metricAuthVal');
    const metricAuthBar = document.getElementById('metricAuthBar');
    const metricDepthVal = document.getElementById('metricDepthVal');
    const metricDepthBar = document.getElementById('metricDepthBar');
    const metricClarityVal = document.getElementById('metricClarityVal');
    const metricClarityBar = document.getElementById('metricClarityBar');
    const metricConfidenceVal = document.getElementById('metricConfidenceVal');
    const metricConfidenceBar = document.getElementById('metricConfidenceBar');

    const reportStrengthsList = document.getElementById('reportStrengthsList');
    const reportImprovementsList = document.getElementById('reportImprovementsList');
    const reportSkillsToRevise = document.getElementById('reportSkillsToRevise');
    const reportProjectTopics = document.getElementById('reportProjectTopics');
    const reportQuestionsList = document.getElementById('reportQuestionsList');
    const reportPrintBtn = document.getElementById('reportPrintBtn');
    const reportRetakeBtn = document.getElementById('reportRetakeBtn');
    const toastContainer = document.getElementById('toastContainer');

    // -------------------------------------------------------------
    // NAVIGATION & VIEW CONTROLS
    // -------------------------------------------------------------
    function switchView(viewName) {
        if (viewName !== 'room') {
            state.speech.stopSpeaking();
            state.speech.stopRecording();
            stopElapsedTimer();
            stopWebcam();
        }

        [homeView, setupView, roomView, reportView].forEach(v => {
            if (v) v.classList.remove('active');
        });

        if (viewName === 'home' && homeView) homeView.classList.add('active');
        else if (viewName === 'setup' && setupView) setupView.classList.add('active');
        else if (viewName === 'room' && roomView) roomView.classList.add('active');
        else if (viewName === 'report' && reportView) reportView.classList.add('active');

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    if (navBrandLink) {
        // Allow default link navigation to home /
    }
    if (navStartBtn) navStartBtn.addEventListener('click', () => {
        if (setupView) switchView('setup');
        else window.location.href = '/interview';
    });
    if (heroStartBtn) heroStartBtn.addEventListener('click', () => {
        if (setupView) switchView('setup');
        else window.location.href = '/interview';
    });
    if (heroHowItWorksBtn) heroHowItWorksBtn.addEventListener('click', () => {
        const target = document.getElementById('howItWorksSection');
        if (target) target.scrollIntoView({ behavior: 'smooth' });
    });

    // -------------------------------------------------------------
    // RESUME PDF UPLOAD & DRAG AND DROP
    // -------------------------------------------------------------
    if (browseFilesBtn && resumeFileInput) {
        browseFilesBtn.addEventListener('click', () => resumeFileInput.click());
    }
    if (resumeDropzone && resumeFileInput) {
        resumeDropzone.addEventListener('click', (e) => {
            if (e.target !== browseFilesBtn) {
                resumeFileInput.click();
            }
        });
    }

    resumeFileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleSelectedFile(e.target.files[0]);
        }
    });

    // Drag and drop event listeners
    ['dragenter', 'dragover'].forEach(eventName => {
        resumeDropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            resumeDropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        resumeDropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            resumeDropzone.classList.remove('dragover');
        });
    });

    resumeDropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt && dt.files && dt.files.length > 0) {
            handleSelectedFile(dt.files[0]);
        }
    });

    function handleSelectedFile(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showToast("Invalid file type. Please upload a PDF resume.", "error");
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            showToast("File size exceeds 10MB limit. Please upload a smaller PDF.", "error");
            return;
        }

        state.selectedFile = file;
        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = formatBytes(file.size);
        selectedFileChip.style.display = 'flex';
        analyzeResumeBtn.disabled = false;
        showToast("Resume PDF selected. Click 'Analyze Resume' to proceed.", "info");
    }

    removeFileBtn.addEventListener('click', () => {
        state.selectedFile = null;
        resumeFileInput.value = '';
        selectedFileChip.style.display = 'none';
        analyzeResumeBtn.disabled = true;
    });

    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // -------------------------------------------------------------
    // ANALYZE RESUME API CALL & CONFIRMATION VIEW
    // -------------------------------------------------------------
    analyzeResumeBtn.addEventListener('click', async () => {
        if (!state.selectedFile) return;

        uploadProgressBanner.style.display = 'flex';
        analyzeResumeBtn.disabled = true;

        const formData = new FormData();
        formData.append('resume', state.selectedFile);

        try {
            const resp = await fetch('/api/resume/upload', {
                method: 'POST',
                body: formData
            });

            const data = await resp.json();
            if (!resp.ok || !data.success) {
                throw new Error(data.error || "Failed to analyze resume.");
            }

            state.resumeData = data.resume_data;
            renderResumeConfirmation(data.resume_data);

            // Hide Upload Card, Show Confirmation Card
            resumeUploadCard.style.display = 'none';
            resumeConfirmationCard.style.display = 'block';
            showToast("Resume successfully analyzed!", "info");
        } catch (err) {
            console.error("Resume analysis error:", err);
            showToast(err.message || "Could not analyze resume. Please try another PDF.", "error");
        } finally {
            uploadProgressBanner.style.display = 'none';
            analyzeResumeBtn.disabled = false;
        }
    });

    function renderResumeConfirmation(resData) {
        const candidate = resData.candidate || {};
        confirmedCandidateName.textContent = candidate.name || "Candidate";
        confirmedCandidateEducation.textContent = resData.education || `${candidate.degree || 'Degree'} in ${candidate.branch || 'CSE'}, ${candidate.college || 'University'}`;

        // Render Skills
        confirmedSkillsList.innerHTML = '';
        const skills = resData.skills || [];
        skillsCountBadge.textContent = skills.length;
        skills.forEach(skill => {
            const tag = document.createElement('span');
            tag.className = 'skill-tag';
            tag.textContent = skill;
            confirmedSkillsList.appendChild(tag);
        });

        // Render Projects
        confirmedProjectsList.innerHTML = '';
        const projects = resData.projects || [];
        projectsCountBadge.textContent = projects.length;
        if (projects.length === 0) {
            confirmedProjectsList.innerHTML = '<div class="confirmation-subtext">No explicit projects section detected</div>';
        } else {
            projects.forEach(p => {
                const card = document.createElement('div');
                card.className = 'project-confirm-card';

                const techPills = (p.technologies || []).map(t => `<span class="tech-mini-pill">${t}</span>`).join(' ');
                const claimText = (p.claims && p.claims.length > 0) ? `<div style="font-size:0.8rem; color:#38bdf8; margin-top:6px;"><strong>Highlight:</strong> "${p.claims[0]}"</div>` : '';

                card.innerHTML = `
                    <div class="project-confirm-title">${p.name}</div>
                    <div class="project-confirm-desc">${p.description}</div>
                    <div class="project-confirm-tech">${techPills}</div>
                    ${claimText}
                `;
                confirmedProjectsList.appendChild(card);
            });
        }

        // Render Certifications
        const certs = resData.certifications || [];
        if (certs.length > 0) {
            confirmedCertsList.innerHTML = certs.map(c => `<div>• ${c}</div>`).join('');
        } else {
            confirmedCertsList.textContent = "No certifications detected";
        }

        // Render Experience
        confirmedExpList.textContent = resData.experience || "No professional experience detected";
    }

    reuploadResumeBtn.addEventListener('click', () => {
        resumeConfirmationCard.style.display = 'none';
        resumeUploadCard.style.display = 'block';
    });

    // -------------------------------------------------------------
    // LAUNCH RESUME-DRIVEN INTERVIEW ROOM
    // -------------------------------------------------------------
    launchInterviewBtn.addEventListener('click', async () => {
        if (!state.resumeData) return;

        const origText = launchInterviewBtn.innerHTML;
        launchInterviewBtn.innerHTML = '<span>⏳ Starting Session...</span>';
        launchInterviewBtn.disabled = true;

        try {
            const resp = await fetch('/api/interview/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ resume_data: state.resumeData })
            });

            if (!resp.ok) throw new Error("Failed to start session.");

            const data = await resp.json();
            state.sessionId = data.session_id;
            state.currentQuestionNum = data.question_number || 1;
            state.difficulty = data.difficulty || 'Medium';

            // Setup Room
            const candidate = state.resumeData.candidate || {};
            candidateDisplayName.textContent = candidate.name || 'Candidate';
            candidateDisplayCollege.textContent = candidate.college || 'University';
            roomTypeBadge.textContent = `Resume: ${candidate.branch || 'Engineering'}`;
            roomDifficultyBadge.textContent = state.difficulty;
            roomDifficultyBadge.className = `difficulty-badge diff-${state.difficulty.toLowerCase()}`;

            // Switch to Room View
            switchView('room');
            startElapsedTimer();

            // Display Question 1
            displayQuestion(data.question, data.question_number, data.category || "Introduction", false);

            // AI Voice speaks welcome & Question 1
            const fullIntro = `${data.welcome_message} ${data.question}`;
            playAiSpeech(fullIntro);

            showToast("Connected to Resume-Driven Interview Room. Good luck!", "info");
        } catch (err) {
            console.error("Start error:", err);
            showToast("Failed to launch interview session. Please try again.", "error");
        } finally {
            launchInterviewBtn.innerHTML = origText;
            launchInterviewBtn.disabled = false;
        }
    });

    // -------------------------------------------------------------
    // INTERVIEW ROOM LOGIC & CONTROLS
    // -------------------------------------------------------------
    function displayQuestion(questionText, qNum, category, isFollowup) {
        state.currentQuestionNum = qNum;
        state.isFollowup = isFollowup;

        questionCounterLabel.textContent = `Question ${qNum}`;
        questionCategoryTag.textContent = category || "Technical";
        followupBadgeContainer.style.display = isFollowup ? 'inline-flex' : 'none';

        // Smooth text reveal
        questionTextBox.style.opacity = '0';
        questionTextBox.textContent = questionText;
        setTimeout(() => {
            questionTextBox.style.transition = 'opacity 0.4s ease';
            questionTextBox.style.opacity = '1';
        }, 80);

        liveTranscriptBox.textContent = "";
        submitAnswerBtn.disabled = true;
        resetMicUI();
    }

    function playAiSpeech(text) {
        aiVideoCard.classList.add('speaking');
        aiStatusText.textContent = "AI Speaking...";

        state.speech.speak(text, () => {
            aiVideoCard.classList.remove('speaking');
            aiStatusText.textContent = "AI Listening...";
        });
    }

    ttsVoiceToggle.addEventListener('click', () => {
        const isMuted = state.speech.toggleMuteTts();
        state.isMutedTts = isMuted;
        ttsIcon.textContent = isMuted ? '🔇' : '🔊';
        ttsVoiceToggle.classList.toggle('active', isMuted);
        showToast(isMuted ? "AI Voice Muted" : "AI Voice Unmuted", "info");
    });

    webcamToggle.addEventListener('click', async () => {
        if (state.isWebcamActive) {
            stopWebcam();
        } else {
            await startWebcam();
        }
    });

    async function startWebcam() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }
            });
            state.webcamStream = stream;
            webcamVideoElement.srcObject = stream;
            webcamVideoElement.style.display = 'block';
            candidatePlaceholder.style.display = 'none';
            state.isWebcamActive = true;
            webcamToggle.classList.add('active');
            camIcon.textContent = '📹';
        } catch (err) {
            console.warn("Camera access error:", err);
            showToast("Camera access was not granted. Using profile avatar.", "info");
        }
    }

    function stopWebcam() {
        if (state.webcamStream) {
            state.webcamStream.getTracks().forEach(track => track.stop());
            state.webcamStream = null;
        }
        webcamVideoElement.srcObject = null;
        webcamVideoElement.style.display = 'none';
        candidatePlaceholder.style.display = 'flex';
        state.isWebcamActive = false;
        webcamToggle.classList.remove('active');
        camIcon.textContent = '📷';
    }

    function startElapsedTimer() {
        stopElapsedTimer();
        state.startTime = Date.now();
        state.elapsedTimerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
            const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const s = String(elapsed % 60).padStart(2, '0');
            interviewElapsedTimer.textContent = `${m}:${s}`;
        }, 1000);
    }

    function stopElapsedTimer() {
        if (state.elapsedTimerInterval) {
            clearInterval(state.elapsedTimerInterval);
            state.elapsedTimerInterval = null;
        }
    }

    // -------------------------------------------------------------
    // MICROPHONE & ANSWER SUBMISSION
    // -------------------------------------------------------------
    state.speech.onTranscriptUpdate = (fullText) => {
        liveTranscriptBox.textContent = fullText;
        liveTranscriptBox.scrollTop = liveTranscriptBox.scrollHeight;
        if (fullText.trim().length > 0) {
            submitAnswerBtn.disabled = false;
        }
    };

    state.speech.onStatusChange = (status) => {
        if (status === 'listening') {
            micStatusIndicator.classList.add('recording-active');
            micStatusText.textContent = "Listening... Speak clearly into your microphone.";
            startAnswerBtn.style.display = 'none';
            stopAnswerBtn.style.display = 'inline-flex';
            audioLevelMeter.style.display = 'block';
        } else {
            micStatusIndicator.classList.remove('recording-active');
            micStatusText.textContent = "Microphone stopped. Review transcript or click Submit Answer.";
            startAnswerBtn.style.display = 'inline-flex';
            stopAnswerBtn.style.display = 'none';
            audioLevelMeter.style.display = 'none';
            audioLevelFill.style.width = '0%';
        }
    };

    state.speech.onTimerTick = (formattedTime) => {
        recordingTimer.textContent = formattedTime;
    };

    state.speech.onAudioLevel = (pct) => {
        audioLevelFill.style.width = `${pct}%`;
    };

    state.speech.onError = (message) => {
        showToast(message, "error");
        resetMicUI();
    };

    function resetMicUI() {
        micStatusIndicator.classList.remove('recording-active');
        micStatusText.textContent = "Microphone Ready. Click Start Answer to respond.";
        recordingTimer.textContent = "00:00";
        startAnswerBtn.style.display = 'inline-flex';
        stopAnswerBtn.style.display = 'none';
        audioLevelMeter.style.display = 'none';
    }

    startAnswerBtn.addEventListener('click', async () => {
        const started = await state.speech.startRecording();
        if (started) {
            submitAnswerBtn.disabled = false;
        }
    });

    stopAnswerBtn.addEventListener('click', () => {
        state.speech.stopRecording();
    });

    retryAnswerBtn.addEventListener('click', () => {
        state.speech.resetRecording();
        liveTranscriptBox.textContent = "";
        submitAnswerBtn.disabled = true;
        resetMicUI();
        showToast("Transcript reset. You can record again.", "info");
    });

    liveTranscriptBox.addEventListener('input', () => {
        const txt = liveTranscriptBox.textContent.trim();
        submitAnswerBtn.disabled = (txt.length === 0);
    });

    submitAnswerBtn.addEventListener('click', async () => {
        const answerText = liveTranscriptBox.textContent.trim();
        if (!answerText) {
            showToast("Please speak or enter an answer before submitting.", "error");
            return;
        }

        state.speech.stopRecording();
        evaluatingBanner.style.display = 'flex';
        startAnswerBtn.disabled = true;
        retryAnswerBtn.disabled = true;
        submitAnswerBtn.disabled = true;

        try {
            const resp = await fetch('/api/interview/submit-answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    answer: answerText
                })
            });

            if (!resp.ok) throw new Error("Failed to process answer.");

            const data = await resp.json();

            if (data.is_completed) {
                evaluatingBanner.style.display = 'none';
                handleInterviewComplete(data);
                return;
            }

            // Interview continues
            evaluatingBanner.style.display = 'none';
            state.difficulty = data.difficulty || state.difficulty;
            roomDifficultyBadge.textContent = state.difficulty;
            roomDifficultyBadge.className = `difficulty-badge diff-${state.difficulty.toLowerCase()}`;

            displayQuestion(data.question, data.question_number, data.category, data.is_followup);
            playAiSpeech(data.question);

            if (data.is_followup) {
                showToast("The AI is asking a follow-up probing your response.", "info");
            } else if (data.difficulty_changed) {
                const dir = data.difficulty_direction === 'up' ? 'elevated' : 'adjusted';
                showToast(`Performance evaluated. Difficulty has been ${dir} to ${state.difficulty}.`, "info");
            }
        } catch (err) {
            console.error("Submit error:", err);
            evaluatingBanner.style.display = 'none';
            showToast("Failed to process answer. Please try submitting again.", "error");
        } finally {
            startAnswerBtn.disabled = false;
            retryAnswerBtn.disabled = false;
        }
    });

    earlyEndBtn.addEventListener('click', async () => {
        const confirmEnd = confirm("Conclude the interview now and generate your performance report?");
        if (!confirmEnd) return;

        state.speech.stopRecording();
        state.speech.stopSpeaking();

        try {
            const resp = await fetch('/api/interview/end', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.sessionId })
            });

            const data = await resp.json();
            handleInterviewComplete(data);
        } catch (err) {
            console.error("End error:", err);
            loadFinalReport(state.sessionId);
        }
    });

    // -------------------------------------------------------------
    // INTERVIEW CONCLUSION & RESUME REPORT
    // -------------------------------------------------------------
    async function handleInterviewComplete(data) {
        stopElapsedTimer();
        stopWebcam();
        state.speech.stopRecording();

        const reason = (data && data.completion_reason) ? data.completion_reason : "Interview concluded!";
        showToast(reason, "info");
        playAiSpeech("Thank you! That concludes our interview session. Let us review your resume performance analysis.");

        setTimeout(() => {
            loadFinalReport(state.sessionId);
        }, 1500);
    }

    async function loadFinalReport(sessionId) {
        try {
            const resp = await fetch(`/api/interview/report/${sessionId}`);
            if (!resp.ok) throw new Error("Could not fetch report.");

            const report = await resp.json();
            renderResumeReport(report);
            switchView('report');
        } catch (err) {
            console.error("Fetch report error:", err);
            showToast("Could not load report. Please try again.", "error");
        }
    }

    function renderResumeReport(report) {
        const score = report.overall_score || 0;
        reportOverallScore.textContent = score;
        reportScoreCircle.style.setProperty('--score-pct', score);

        reportRecBadge.textContent = report.recommendation || "Completed";
        reportRecBadge.className = `recommendation-pill ${report.badge_class || 'badge-hire'}`;

        reportCandidateTitle.textContent = `${report.candidate?.name || 'Candidate'}'s Interview Performance`;
        reportSummaryVerdict.textContent = report.summary_verdict || report.completion_reason || "Interview successfully evaluated.";

        reportMetaEducation.textContent = report.education || "Computer Science";
        reportMetaSkills.textContent = report.skills_detected?.length || 6;
        reportMetaQuestions.textContent = report.total_questions || report.question_breakdown?.length || 0;
        reportMetaDuration.textContent = report.duration || '06:00';

        // 6 Metrics
        const m = report.metrics || {};
        metricAccuracyVal.textContent = `${m.technical_knowledge || 80}%`;
        metricAccuracyBar.style.width = `${m.technical_knowledge || 80}%`;

        metricProjVal.textContent = `${m.project_understanding || 80}%`;
        metricProjBar.style.width = `${m.project_understanding || 80}%`;

        metricAuthVal.textContent = `${m.resume_knowledge || 85}%`;
        metricAuthBar.style.width = `${m.resume_knowledge || 85}%`;

        metricDepthVal.textContent = `${m.problem_solving || 75}%`;
        metricDepthBar.style.width = `${m.problem_solving || 75}%`;

        metricClarityVal.textContent = `${m.communication || 80}%`;
        metricClarityBar.style.width = `${m.communication || 80}%`;

        metricConfidenceVal.textContent = `${m.confidence || 80}%`;
        metricConfidenceBar.style.width = `${m.confidence || 80}%`;

        // Resume Strengths
        reportStrengthsList.innerHTML = '';
        (report.resume_strengths || ["Confirmed technical foundation across resume claims."]).forEach(s => {
            const li = document.createElement('li');
            li.className = 'bullet-item';
            li.innerHTML = `<span class="bullet-icon">✅</span> <span>${s}</span>`;
            reportStrengthsList.appendChild(li);
        });

        // Weak Areas
        reportImprovementsList.innerHTML = '';
        (report.weak_areas || ["Elaborate more deeply on architectural trade-offs."]).forEach(w => {
            const li = document.createElement('li');
            li.className = 'bullet-item';
            li.innerHTML = `<span class="bullet-icon">💡</span> <span>${w}</span>`;
            reportImprovementsList.appendChild(li);
        });

        // Skills to Revise
        reportSkillsToRevise.innerHTML = '';
        (report.skills_to_revise || ["Python", "SQL"]).forEach(sk => {
            const tag = document.createElement('span');
            tag.className = 'skill-tag';
            tag.textContent = sk;
            reportSkillsToRevise.appendChild(tag);
        });

        // Project Topics to Prepare
        reportProjectTopics.innerHTML = '';
        (report.project_topics_to_prepare || ["Review system architecture and benchmark comparisons."]).forEach(pt => {
            const li = document.createElement('li');
            li.className = 'bullet-item';
            li.innerHTML = `<span class="bullet-icon">📌</span> <span>${pt}</span>`;
            reportProjectTopics.appendChild(li);
        });

        // Question Audit
        reportQuestionsList.innerHTML = '';
        (report.question_breakdown || []).forEach(item => {
            const card = document.createElement('div');
            card.className = 'breakdown-card';

            const catBadge = item.category ? `<span class="question-category-tag" style="font-size:0.75rem; margin-left:8px;">${item.category}</span>` : '';
            const fuBadge = item.is_followup ? `<span class="followup-badge" style="font-size:0.75rem; margin-left:8px;">Follow-up</span>` : '';

            card.innerHTML = `
                <div class="breakdown-header">
                    <div class="breakdown-q-title">
                        <span>Q${item.question_number}: ${item.question}</span>
                        ${catBadge}
                        ${fuBadge}
                    </div>
                    <span class="breakdown-score-badge">${item.score}/100</span>
                </div>
                <div class="breakdown-ans">
                    <strong>Spoken Transcript:</strong> "${item.candidate_answer}"
                </div>
                <div class="breakdown-feedback">
                    <strong>AI Evaluation:</strong> ${item.feedback}
                </div>
            `;
            reportQuestionsList.appendChild(card);
        });
    }

    reportPrintBtn.addEventListener('click', () => window.print());
    reportRetakeBtn.addEventListener('click', () => {
        resumeConfirmationCard.style.display = 'none';
        resumeUploadCard.style.display = 'block';
        switchView('setup');
    });

    // -------------------------------------------------------------
    // TOAST NOTIFICATIONS
    // -------------------------------------------------------------
    function showToast(msg, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        const icon = type === 'error' ? '⚠️' : 'ℹ️';
        toast.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;

        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
});
