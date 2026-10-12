/**
 * Speech Recognition & Audio Interaction Module for AI Interview Room
 * Integrates Web Speech API (webkitSpeechRecognition/SpeechRecognition)
 * and Web Speech Synthesis (Text-To-Speech) with graceful error handling.
 */

class InterviewSpeechModule {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.speechSynthesis = window.speechSynthesis;
        this.currentUtterance = null;
        this.isTtsMuted = false;
        this.transcript = "";
        this.timerInterval = null;
        this.secondsRecorded = 0;
        this.audioContext = null;
        this.analyser = null;
        this.mediaStream = null;
        this.animFrameId = null;

        // Callback hooks
        this.onTranscriptUpdate = null;
        this.onStatusChange = null;
        this.onError = null;
        this.onTimerTick = null;
        this.onAudioLevel = null;
        this.onTtsStart = null;
        this.onTtsEnd = null;

        this.initRecognition();
    }

    initRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn("Web Speech API not supported in this browser.");
            return false;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            this.isListening = true;
            this.startTimer();
            if (this.onStatusChange) this.onStatusChange("listening");
        };

        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = 0; i < event.results.length; ++i) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalTranscript += result[0].transcript + ' ';
                } else {
                    interimTranscript += result[0].transcript;
                }
            }

            const combined = (finalTranscript + interimTranscript).trim();
            this.transcript = combined;
            if (this.onTranscriptUpdate) {
                this.onTranscriptUpdate(combined, interimTranscript);
            }
        };

        this.recognition.onerror = (event) => {
            console.error("Speech Recognition error:", event.error);
            let message = "Speech recognition encountered an error: " + event.error;
            if (event.error === 'not-allowed') {
                message = "Microphone access was denied. Please allow microphone permissions in your browser.";
            } else if (event.error === 'no-speech') {
                message = "No speech was detected. Please check your microphone and try again.";
            }
            if (this.onError) this.onError(message, event.error);
            this.stopRecording();
        };

        this.recognition.onend = () => {
            if (this.isListening) {
                // If it ended prematurely while user still wants to record, restart
                try {
                    this.recognition.start();
                } catch (e) {
                    this.isListening = false;
                    this.stopTimer();
                    if (this.onStatusChange) this.onStatusChange("stopped");
                }
            } else {
                this.stopTimer();
                if (this.onStatusChange) this.onStatusChange("stopped");
            }
        };

        return true;
    }

    async startRecording() {
        this.transcript = "";
        this.secondsRecorded = 0;

        if (!this.recognition) {
            const supported = this.initRecognition();
            if (!supported) {
                if (this.onError) {
                    this.onError("Your browser does not support the Web Speech API. Please use Chrome, Edge, or Safari, or use text fallback.");
                }
                return false;
            }
        }

        // Request audio stream for visualizer and verification
        try {
            if (!this.mediaStream) {
                this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.setupAudioVisualizer(this.mediaStream);
            }
        } catch (err) {
            console.error("Microphone getUserMedia failed:", err);
            if (this.onError) {
                this.onError("Microphone permission denied or device not found. Please enable microphone access.");
            }
            return false;
        }

        // Cancel any active AI speaking
        this.stopSpeaking();

        try {
            this.isListening = true;
            this.recognition.start();
            return true;
        } catch (err) {
            console.warn("Recognition start error (may already be running):", err);
            return true;
        }
    }

    stopRecording() {
        this.isListening = false;
        this.stopTimer();
        if (this.recognition) {
            try {
                this.recognition.stop();
            } catch (e) {
                // Ignore
            }
        }
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }
        if (this.onStatusChange) {
            this.onStatusChange("stopped");
        }
    }

    resetRecording() {
        this.stopRecording();
        this.transcript = "";
        this.secondsRecorded = 0;
        if (this.onTranscriptUpdate) {
            this.onTranscriptUpdate("", "");
        }
    }

    startTimer() {
        this.stopTimer();
        this.secondsRecorded = 0;
        this.timerInterval = setInterval(() => {
            this.secondsRecorded++;
            if (this.onTimerTick) {
                this.onTimerTick(this.formatTime(this.secondsRecorded));
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    formatTime(totalSecs) {
        const mins = Math.floor(totalSecs / 60);
        const secs = totalSecs % 60;
        return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }

    setupAudioVisualizer(stream) {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;

            if (!this.audioContext) {
                this.audioContext = new AudioContext();
            }
            if (this.audioContext.state === 'suspended') {
                this.audioContext.resume();
            }

            const source = this.audioContext.createMediaStreamSource(stream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            source.connect(this.analyser);

            const bufferLength = this.analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);

            const updateLevel = () => {
                if (!this.isListening) {
                    if (this.onAudioLevel) this.onAudioLevel(0, dataArray);
                    return;
                }
                this.analyser.getByteFrequencyData(dataArray);
                let sum = 0;
                for (let i = 0; i < bufferLength; i++) {
                    sum += dataArray[i];
                }
                const avg = sum / bufferLength;
                const normalized = Math.min(100, Math.round((avg / 128) * 100));

                if (this.onAudioLevel) {
                    this.onAudioLevel(normalized, dataArray);
                }
                this.animFrameId = requestAnimationFrame(updateLevel);
            };

            updateLevel();
        } catch (e) {
            console.warn("Visualizer initialization skipped:", e);
        }
    }

    // ---------------------------------------------------------
    // AI Text-To-Speech (Interviewer Speaking)
    // ---------------------------------------------------------
    speak(text, onComplete) {
        if (this.isTtsMuted || !this.speechSynthesis) {
            if (onComplete) setTimeout(onComplete, 1200);
            return;
        }

        this.stopSpeaking();

        // Clean text (remove markdown symbols)
        const cleanText = text.replace(/[*_#`]/g, '').trim();
        const utterance = new SpeechSynthesisUtterance(cleanText);
        this.currentUtterance = utterance;

        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        // Choose a professional natural voice if available
        const voices = this.speechSynthesis.getVoices();
        const preferredVoice = voices.find(v => 
            v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Guy') || v.name.includes('Aria'))
        ) || voices.find(v => v.lang.startsWith('en'));

        if (preferredVoice) {
            utterance.voice = preferredVoice;
        }

        utterance.onstart = () => {
            if (this.onTtsStart) this.onTtsStart();
        };

        utterance.onend = () => {
            this.currentUtterance = null;
            if (this.onTtsEnd) this.onTtsEnd();
            if (onComplete) onComplete();
        };

        utterance.onerror = (e) => {
            console.warn("TTS error:", e);
            this.currentUtterance = null;
            if (this.onTtsEnd) this.onTtsEnd();
            if (onComplete) onComplete();
        };

        this.speechSynthesis.speak(utterance);
    }

    stopSpeaking() {
        if (this.speechSynthesis) {
            this.speechSynthesis.cancel();
        }
        this.currentUtterance = null;
        if (this.onTtsEnd) this.onTtsEnd();
    }

    toggleMuteTts() {
        this.isTtsMuted = !this.isTtsMuted;
        if (this.isTtsMuted) {
            this.stopSpeaking();
        }
        return this.isTtsMuted;
    }
}

// Attach to global window
window.InterviewSpeechModule = InterviewSpeechModule;
