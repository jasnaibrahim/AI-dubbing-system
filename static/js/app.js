// AI Dubbing Service - Frontend JavaScript

class DubbingApp {
    constructor() {
        this.currentJobId = null;
        this.pollInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadVoices();
    }

    bindEvents() {
        // Form submission
        document.getElementById('dubbingForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startDubbing();
        });

        // Preview button
        document.getElementById('previewBtn').addEventListener('click', () => {
            this.previewTranslation();
        });

        // Language change
        document.getElementById('targetLanguage').addEventListener('change', () => {
            this.loadVoices();
        });
    }

    async loadVoices() {
        try {
            const language = document.getElementById('targetLanguage').value;
            const response = await fetch(`/api/voices${language ? `?language=${language}` : ''}`);
            const data = await response.json();

            const voiceSelect = document.getElementById('voiceSelect');
            voiceSelect.innerHTML = '<option value="">Use default voice for language</option>';

            data.voices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.voice_id;

                // Use enhanced display name if available, otherwise fallback to basic info
                const displayName = voice.display_name ||
                    `${voice.name} (${voice.gender || voice.category || 'General'})`;

                option.textContent = displayName;
                voiceSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load voices:', error);
        }
    }

    async previewTranslation() {
        const youtubeUrl = document.getElementById('youtubeUrl').value;
        const targetLanguage = document.getElementById('targetLanguage').value;

        if (!youtubeUrl || !targetLanguage) {
            this.showAlert('Please enter a YouTube URL and select a target language.', 'warning');
            return;
        }

        const previewBtn = document.getElementById('previewBtn');
        const originalText = previewBtn.innerHTML;
        previewBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating Preview...';
        previewBtn.disabled = true;

        try {
            const response = await fetch('/api/preview-translation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    youtube_url: youtubeUrl,
                    target_language: targetLanguage
                })
            });

            if (!response.ok) {
                throw new Error('Failed to generate preview');
            }

            const data = await response.json();
            this.displayPreview(data);

        } catch (error) {
            console.error('Preview failed:', error);
            this.showAlert('Failed to generate preview. Please check the YouTube URL and try again.', 'danger');
        } finally {
            previewBtn.innerHTML = originalText;
            previewBtn.disabled = false;
        }
    }

    displayPreview(data) {
        const previewCard = document.getElementById('previewCard');
        const previewContent = document.getElementById('previewContent');

        let html = `
            <div class="mb-3">
                <h6><i class="fas fa-info-circle me-2"></i>Translation Summary</h6>
                <p><strong>Source Language:</strong> ${this.getLanguageName(data.source_language)}</p>
                <p><strong>Target Language:</strong> ${this.getLanguageName(data.target_language)}</p>
                <p><strong>Segments:</strong> ${data.translated_transcript.length}</p>
            </div>
            <div class="preview-segments">
                <h6><i class="fas fa-file-alt me-2"></i>Sample Translations</h6>
        `;

        // Show first 3 segments as preview
        const sampleSegments = data.translated_transcript.slice(0, 3);
        sampleSegments.forEach((segment, index) => {
            html += `
                <div class="preview-segment">
                    <div class="original">Original: ${segment.original_text || 'N/A'}</div>
                    <div class="translated">Translated: ${segment.text}</div>
                </div>
            `;
        });

        if (data.translated_transcript.length > 3) {
            html += `<p class="text-muted">... and ${data.translated_transcript.length - 3} more segments</p>`;
        }

        html += '</div>';
        previewContent.innerHTML = html;
        previewCard.style.display = 'block';
        previewCard.classList.add('fade-in');
    }

    async startDubbing() {
        const youtubeUrl = document.getElementById('youtubeUrl').value;
        const targetLanguage = document.getElementById('targetLanguage').value;
        const voiceId = document.getElementById('voiceSelect').value;
        const cloneVoice = document.getElementById('cloneVoice').checked;

        if (!youtubeUrl || !targetLanguage) {
            this.showAlert('Please enter a YouTube URL and select a target language.', 'warning');
            return;
        }

        const dubBtn = document.getElementById('dubBtn');
        const originalText = dubBtn.innerHTML;
        dubBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting...';
        dubBtn.disabled = true;

        try {
            const response = await fetch('/api/dub-video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    youtube_url: youtubeUrl,
                    target_language: targetLanguage,
                    voice_id: voiceId || null,
                    clone_original_voice: cloneVoice
                })
            });

            if (!response.ok) {
                throw new Error('Failed to start dubbing process');
            }

            const data = await response.json();
            this.currentJobId = data.job_id;
            this.showProgressCard();
            this.startPolling();

        } catch (error) {
            console.error('Dubbing failed:', error);
            this.showAlert('Failed to start dubbing process. Please try again.', 'danger');
            dubBtn.innerHTML = originalText;
            dubBtn.disabled = false;
        }
    }

    showProgressCard() {
        const progressCard = document.getElementById('progressCard');
        progressCard.style.display = 'block';
        progressCard.classList.add('fade-in');
        
        // Hide result card if visible
        document.getElementById('resultCard').style.display = 'none';
    }

    startPolling() {
        this.pollInterval = setInterval(() => {
            this.checkJobStatus();
        }, 1000); // Poll every 1 second for better responsiveness
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    async checkJobStatus() {
        if (!this.currentJobId) return;

        try {
            const response = await fetch(`/api/job-status/${this.currentJobId}`);

            // Handle 404 - job not found (server restarted)
            if (response.status === 404) {
                this.stopPolling();
                this.hideProgress();
                this.showAlert('⚠️ Job not found. The server may have restarted. Please start a new dubbing job.', 'warning');
                this.currentJobId = null; // Clear the job ID
                return;
            }

            const data = await response.json();

            this.updateProgress(data);

            if (data.status === 'completed') {
                this.handleJobComplete(data);
            } else if (data.status === 'failed') {
                this.handleJobFailed(data);
            }

        } catch (error) {
            console.error('Failed to check job status:', error);
            this.stopPolling();
            this.hideProgress();
            this.showAlert('Error checking job status. Please try again.', 'danger');
        }
    }

    updateProgress(data) {
        const progressBar = document.getElementById('progressBar');
        const progressMessage = document.getElementById('progressMessage');

        progressBar.style.width = `${data.progress}%`;
        progressMessage.textContent = data.message;

        if (data.status === 'processing') {
            progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
        }
    }

    handleJobComplete(data) {
        clearInterval(this.pollInterval);
        
        const progressBar = document.getElementById('progressBar');
        progressBar.className = 'progress-bar bg-success';
        progressBar.style.width = '100%';
        
        document.getElementById('progressMessage').textContent = 'Dubbing completed successfully!';
        
        this.showResult(data.result);
        this.resetForm();
    }

    handleJobFailed(data) {
        clearInterval(this.pollInterval);
        
        const progressBar = document.getElementById('progressBar');
        progressBar.className = 'progress-bar bg-danger';
        
        document.getElementById('progressMessage').textContent = data.message;
        this.showAlert('Dubbing process failed. Please try again.', 'danger');
        this.resetForm();
    }

    showResult(result) {
        const resultCard = document.getElementById('resultCard');
        const resultContent = document.getElementById('resultContent');

        // Check if this is a successful dubbing (real VideoDB stream)
        const isSuccessfulDubbing = result.video_url && result.video_url.includes('stream.videodb.io');

        // Check if this is demo mode
        const isDemoMode = !isSuccessfulDubbing && (result.demo_mode || result.note);

        let html = `
            <div class="text-center">
                <h5><i class="fas fa-${isSuccessfulDubbing ? 'microphone' : (isDemoMode ? 'magic' : 'check-circle')} text-${isSuccessfulDubbing ? 'success' : (isDemoMode ? 'warning' : 'success')} me-2"></i>
                ${isSuccessfulDubbing ? '🎉 AI Dubbing Completed Successfully!' : (isDemoMode ? 'AI Translation Demo Completed!' : 'Your dubbed video is ready!')}</h5>
                <p class="mb-3">Language: ${this.getLanguageName(result.target_language)}</p>
        `;

        if (isSuccessfulDubbing) {
            html += `
                <div class="alert alert-success mb-3">
                    <strong>🎤 AI Dubbing Complete!</strong> Your video has been successfully dubbed with AI-generated voice!<br>
                    <small>✨ Full pipeline: Video processing → Transcript → Translation → Voice synthesis → Final video</small>
                </div>
                <div class="alert alert-light mb-3">
                    <h6>🎯 What Was Accomplished:</h6>
                    <ul class="text-start mb-0">
                        <li>✅ Video uploaded and processed</li>
                        <li>✅ Transcript extracted from audio</li>
                        <li>✅ AI translation completed with GPT-4o-mini</li>
                        <li>✅ AI voice synthesis with ElevenLabs</li>
                        <li>✅ Final dubbed video created</li>
                    </ul>
                </div>
            `;
        } else if (isDemoMode) {
            html += `
                <div class="alert alert-info mb-3">
                    <strong>🎭 Demo Mode:</strong> Translation completed successfully!<br>
                    <small>${result.note || 'Voice generation requires valid ElevenLabs API key.'}</small>
                </div>
                <div class="alert alert-light mb-3">
                    <h6>🎯 What Was Accomplished:</h6>
                    <ul class="text-start mb-0">
                        <li>✅ Video uploaded and processed</li>
                        <li>✅ Transcript extracted from audio</li>
                        <li>✅ AI translation completed with GPT-4o-mini</li>
                        <li>⚠️ Voice synthesis requires valid ElevenLabs API key</li>
                    </ul>
                </div>
            `;
        }

        html += `
                <div class="result-video mb-3">
                    <video id="videoPlayer" controls width="100%" height="400" style="max-width: 600px;" preload="metadata">
                        <source src="${result.video_url}" type="application/x-mpegURL">
                        <source src="${result.video_url}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div class="mt-2">
                        <small class="text-muted">
                            ${isSuccessfulDubbing ? '🎤 Your AI-dubbed video' : '🎬 Your video'}:
                            <a href="${result.video_url}" target="_blank" class="text-primary">Open in new tab</a>
                            ${isSuccessfulDubbing ? ' | <span class="text-success">✅ AI Voice Synthesis Complete</span>' : ''}
                        </small>
                    </div>
                </div>

                <div class="d-grid gap-2">
                    <a href="${result.video_url}" class="btn btn-primary btn-lg" target="_blank">
                        <i class="fas fa-${isSuccessfulDubbing ? 'microphone' : (isDemoMode ? 'play' : 'external-link-alt')} me-2"></i>
                        ${isSuccessfulDubbing ? '🎤 Play AI-Dubbed Video' : (isDemoMode ? 'View Original Video' : 'Open Video in New Tab')}
                    </a>
                    <button class="btn btn-outline-secondary" onclick="app.copyToClipboard(\`${result.video_url}\`)">
                        <i class="fas fa-copy me-2"></i>
                        Copy Video URL
                    </button>
                    ${isSuccessfulDubbing ? `
                    <button class="btn btn-outline-info" onclick="app.showVideoInfo('${result.video_url}')">
                        <i class="fas fa-info-circle me-2"></i>
                        Video Info & Alternatives
                    </button>
                    ` : ''}
                </div>
            </div>
        `;

        resultContent.innerHTML = html;
        resultCard.style.display = 'block';
        resultCard.classList.add('fade-in');

        // Initialize HLS.js for better video streaming support
        this.initializeVideoPlayer(result.video_url);
    }

    initializeVideoPlayer(videoUrl) {
        const video = document.getElementById('videoPlayer');
        if (!video) return;

        // Check if HLS.js is supported and the URL is an HLS stream
        if (typeof Hls !== 'undefined' && Hls.isSupported() && videoUrl.includes('.m3u8')) {
            const hls = new Hls({
                enableWorker: true,
                lowLatencyMode: true,
                backBufferLength: 90
            });

            hls.loadSource(videoUrl);
            hls.attachMedia(video);

            hls.on(Hls.Events.MANIFEST_PARSED, function() {
                console.log('✅ HLS video loaded successfully');
            });

            hls.on(Hls.Events.ERROR, function(event, data) {
                console.warn('⚠️ HLS error:', data);
                // Fallback to native video player
                if (video.canPlayType('application/vnd.apple.mpegurl')) {
                    video.src = videoUrl;
                }
            });
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            // Native HLS support (Safari)
            video.src = videoUrl;
        }
    }

    resetForm() {
        const dubBtn = document.getElementById('dubBtn');
        dubBtn.innerHTML = '<i class="fas fa-play me-2"></i>Generate Dubbing';
        dubBtn.disabled = false;
        this.currentJobId = null;
    }

    showVideoInfo(videoUrl) {
        const modal = `
            <div class="modal fade" id="videoInfoModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">🎬 Video Playback Options</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <h6>📺 Why .m3u8 Format?</h6>
                            <p><strong>HLS (HTTP Live Streaming)</strong> is the industry standard for adaptive video streaming:</p>
                            <ul>
                                <li>📱 <strong>Adaptive Quality</strong>: Adjusts to your connection speed</li>
                                <li>⚡ <strong>Fast Loading</strong>: Starts playing while processing</li>
                                <li>🌐 <strong>Web Optimized</strong>: Used by Netflix, YouTube, etc.</li>
                                <li>🎯 <strong>AI Processing</strong>: Perfect for dubbed videos</li>
                            </ul>

                            <h6>🚀 Playback Options:</h6>
                            <div class="d-grid gap-2">
                                <a href="${videoUrl}" class="btn btn-primary" target="_blank">
                                    <i class="fas fa-external-link-alt me-2"></i>Open in New Tab
                                </a>
                                <button class="btn btn-outline-secondary" onclick="app.copyToClipboard('${videoUrl}')">
                                    <i class="fas fa-copy me-2"></i>Copy URL for VLC/Media Player
                                </button>
                            </div>

                            <div class="alert alert-info mt-3">
                                <small><strong>💡 Tip:</strong> If the video doesn't play in browser, copy the URL and open it in VLC Media Player or any modern video player that supports HLS streams.</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('videoInfoModal');
        if (existingModal) existingModal.remove();

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modal);

        // Show modal
        const modalElement = new bootstrap.Modal(document.getElementById('videoInfoModal'));
        modalElement.show();
    }

    copyToClipboard(text) {
        // Check if the text is valid
        if (!text || text.trim() === '') {
            this.showAlert('No URL to copy!', 'warning');
            return;
        }

        // Try modern clipboard API first
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(() => {
                this.showAlert('✅ Video URL copied to clipboard!', 'success');
                console.log('Copied to clipboard:', text);
            }).catch((err) => {
                console.error('Clipboard API failed:', err);
                this.fallbackCopyToClipboard(text);
            });
        } else {
            // Fallback for older browsers or non-secure contexts
            this.fallbackCopyToClipboard(text);
        }
    }

    fallbackCopyToClipboard(text) {
        try {
            // Create a temporary textarea element
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();

            // Try to copy using execCommand
            const successful = document.execCommand('copy');
            document.body.removeChild(textArea);

            if (successful) {
                this.showAlert('✅ Video URL copied to clipboard!', 'success');
                console.log('Fallback copy successful:', text);
            } else {
                this.showAlert('❌ Failed to copy URL. Please copy manually.', 'warning');
                console.error('Fallback copy failed');
                // Show the URL in a prompt as last resort
                prompt('Copy this URL manually:', text);
            }
        } catch (err) {
            console.error('Fallback copy error:', err);
            this.showAlert('❌ Copy failed. Please copy manually.', 'warning');
            // Show the URL in a prompt as last resort
            prompt('Copy this URL manually:', text);
        }
    }

    async showLogs() {
        try {
            const response = await fetch('/api/logs');
            const data = await response.json();

            // Create a modal to show logs
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-file-alt me-2"></i>
                                Application Logs (Last ${data.showing_last} lines)
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <pre style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 15px; border-radius: 5px; font-size: 12px;">${data.logs.join('')}</pre>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" onclick="app.showLogs()">Refresh</button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();

            // Remove modal from DOM when hidden
            modal.addEventListener('hidden.bs.modal', () => {
                document.body.removeChild(modal);
            });

        } catch (error) {
            console.error('Failed to fetch logs:', error);
            this.showAlert('Failed to load logs', 'danger');
        }
    }

    getLanguageName(code) {
        const languages = {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
            'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
            'ko': 'Korean', 'zh': 'Chinese', 'hi': 'Hindi', 'ar': 'Arabic'
        };
        return languages[code] || code;
    }



    showAlert(message, type) {
        // Create alert element
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Insert at top of container
        const container = document.querySelector('.container');
        container.insertBefore(alert, container.firstChild);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new DubbingApp();
});
