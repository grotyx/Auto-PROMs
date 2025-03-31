#!/bin/bash

# 필요한 디렉토리 생성
mkdir -p templates static/css logs input_pdfs output_csv temp_images

# HTML 파일 생성
cat > templates/index.html << 'EOL'
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>임상 설문지 PDF 처리기</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>임상 설문지 PDF 처리기</h1>
            <p class="subtitle">PDF 임상 설문지를 업로드하면 CSV 파일로 자동 변환합니다</p>
        </header>

        <main>
            <section class="upload-section">
                <div class="upload-container" id="dropArea">
                    <form id="uploadForm">
                        <div class="file-input-container">
                            <input type="file" id="fileInput" name="file" accept=".pdf" required>
                            <label for="fileInput">
                                <div class="upload-icon">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                    </svg>
                                </div>
                                <div>
                                    <span class="primary-text">PDF 파일을 선택하거나 여기에 끌어다 놓으세요</span>
                                    <span class="secondary-text">최대 파일 크기: 100MB</span>
                                </div>
                            </label>
                        </div>
                        <button type="submit" id="submitBtn" disabled>
                            파일 처리하기
                        </button>
                    </form>
                </div>
            </section>

            <section class="progress-section hidden" id="progressSection">
                <h2>파일 처리 중...</h2>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <div class="progress-text" id="progressText">0%</div>
                </div>
                <p class="status-message" id="statusMessage">PDF 파일을 처리하고 있습니다...</p>
            </section>

            <section class="result-section hidden" id="resultSection">
                <div class="result-card success hidden" id="successCard">
                    <div class="result-icon success-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h2>처리 완료!</h2>
                    <p>설문 데이터가 성공적으로 CSV 파일로 변환되었습니다.</p>
                    <a href="#" id="downloadLink" class="download-button">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        CSV 파일 다운로드
                    </a>
                </div>

                <div class="result-card error hidden" id="errorCard">
                    <div class="result-icon error-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                    </div>
                    <h2>처리 오류</h2>
                    <p id="errorMessage">PDF 파일 처리 중 오류가 발생했습니다.</p>
                    <button id="tryAgainBtn" class="try-again-button">
                        다시 시도
                    </button>
                </div>
            </section>
        </main>

        <footer>
            <p>© 2025 임상 설문지 처리 시스템</p>
        </footer>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const uploadForm = document.getElementById('uploadForm');
            const fileInput = document.getElementById('fileInput');
            const submitBtn = document.getElementById('submitBtn');
            const dropArea = document.getElementById('dropArea');
            const progressSection = document.getElementById('progressSection');
            const resultSection = document.getElementById('resultSection');
            const successCard = document.getElementById('successCard');
            const errorCard = document.getElementById('errorCard');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            const statusMessage = document.getElementById('statusMessage');
            const downloadLink = document.getElementById('downloadLink');
            const errorMessage = document.getElementById('errorMessage');
            const tryAgainBtn = document.getElementById('tryAgainBtn');

            // 파일 선택 시 버튼 활성화
            fileInput.addEventListener('change', function() {
                if (fileInput.files.length > 0) {
                    const fileName = fileInput.files[0].name;
                    if (fileName.toLowerCase().endsWith('.pdf')) {
                        submitBtn.removeAttribute('disabled');
                        dropArea.classList.add('has-file');
                        dropArea.querySelector('.primary-text').textContent = fileName;
                    } else {
                        alert('PDF 파일만 업로드 가능합니다.');
                        fileInput.value = '';
                        submitBtn.setAttribute('disabled', true);
                    }
                } else {
                    submitBtn.setAttribute('disabled', true);
                    dropArea.classList.remove('has-file');
                    dropArea.querySelector('.primary-text').textContent = 'PDF 파일을 선택하거나 여기에 끌어다 놓으세요';
                }
            });

            // 드래그 앤 드롭 기능
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, preventDefaults, false);
            });

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            ['dragenter', 'dragover'].forEach(eventName => {
                dropArea.addEventListener(eventName, highlight, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, unhighlight, false);
            });

            function highlight() {
                dropArea.classList.add('highlight');
            }

            function unhighlight() {
                dropArea.classList.remove('highlight');
            }

            dropArea.addEventListener('drop', handleDrop, false);

            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;

                if (files.length > 0) {
                    const file = files[0];
                    if (file.name.toLowerCase().endsWith('.pdf')) {
                        fileInput.files = files;
                        submitBtn.removeAttribute('disabled');
                        dropArea.classList.add('has-file');
                        dropArea.querySelector('.primary-text').textContent = file.name;
                    } else {
                        alert('PDF 파일만 업로드 가능합니다.');
                    }
                }
            }

            // 폼 제출 처리
            uploadForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                if (!fileInput.files.length) {
                    return;
                }

                const formData = new FormData();
                formData.append('file', fileInput.files[0]);

                // UI 업데이트
                dropArea.classList.add('hidden');
                progressSection.classList.remove('hidden');
                resultSection.classList.add('hidden');
                successCard.classList.add('hidden');
                errorCard.classList.add('hidden');

                try {
                    // 파일 업로드
                    const response = await fetch('/upload/', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        throw new Error(`서버 오류: ${response.status}`);
                    }

                    const data = await response.json();
                    
                    if (data && data.job_id) {
                        // 상태 폴링 시작
                        pollJobStatus(data.job_id);
                    } else {
                        throw new Error('서버에서 작업 ID를 반환하지 않았습니다.');
                    }
                } catch (error) {
                    showError(error.message);
                }
            });

            // 작업 상태 폴링
            async function pollJobStatus(jobId) {
                const pollInterval = setInterval(async () => {
                    try {
                        const response = await fetch(`/status/${jobId}`);
                        
                        if (!response.ok) {
                            clearInterval(pollInterval);
                            throw new Error(`상태 확인 오류: ${response.status}`);
                        }

                        const data = await response.json();
                        
                        // 진행률 업데이트
                        updateProgress(data.progress, data.status);
                        
                        // 상태에 따른 처리
                        if (data.status === 'completed') {
                            clearInterval(pollInterval);
                            showSuccess(data.download_url);
                        } else if (data.status === 'error') {
                            clearInterval(pollInterval);
                            showError(data.error || '알 수 없는 오류가 발생했습니다.');
                        }
                    } catch (error) {
                        clearInterval(pollInterval);
                        showError(error.message);
                    }
                }, 2000); // 2초마다 폴링
            }

            // 진행률 업데이트
            function updateProgress(progress, status) {
                progressFill.style.width = `${progress}%`;
                progressText.textContent = `${progress}%`;
                
                // 상태 메시지 업데이트
                if (status === 'processing') {
                    statusMessage.textContent = 'PDF 파일을 처리하고 있습니다...';
                } else if (status === 'analyzing') {
                    statusMessage.textContent = '설문 데이터를 분석하고 있습니다...';
                } else if (status === 'generating_csv') {
                    statusMessage.textContent = 'CSV 파일을 생성하고 있습니다...';
                }
            }

            // 성공 화면 표시
            function showSuccess(downloadUrl) {
                progressSection.classList.add('hidden');
                resultSection.classList.remove('hidden');
                successCard.classList.remove('hidden');
                downloadLink.href = downloadUrl;
            }

            // 오류 화면 표시
            function showError(message) {
                progressSection.classList.add('hidden');
                resultSection.classList.remove('hidden');
                errorCard.classList.remove('hidden');
                errorMessage.textContent = message;
            }

            // 다시 시도 버튼
            tryAgainBtn.addEventListener('click', function() {
                resetForm();
            });

            // 폼 초기화
            function resetForm() {
                fileInput.value = '';
                submitBtn.setAttribute('disabled', true);
                dropArea.classList.remove('has-file');
                dropArea.querySelector('.primary-text').textContent = 'PDF 파일을 선택하거나 여기에 끌어다 놓으세요';
                
                resultSection.classList.add('hidden');
                dropArea.classList.remove('hidden');
            }
        });
    </script>
</body>
</html>
EOL

# CSS 파일 생성
cat > static/css/styles.css << 'EOL'
/* 기본 설정 */
:root {
    --primary-color: #4c6ef5;
    --primary-dark: #3b5bdb;
    --success-color: #37b24d;
    --error-color: #e03131;
    --text-color: #343a40;
    --light-text: #868e96;
    --border-color: #dee2e6;
    --light-bg: #f8f9fa;
    --white: #ffffff;
    --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    --transition: all 0.3s ease;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--light-bg);
}

.container {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem 1rem;
}

/* 헤더 스타일 */
header {
    text-align: center;
    margin-bottom: 2rem;
}

h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    color: var(--primary-color);
}

.subtitle {
    font-size: 1.1rem;
    color: var(--light-text);
}

/* 메인 섹션 */
main {
    margin-bottom: 3rem;
}

section {
    margin-bottom: 2rem;
}

.hidden {
    display: none;
}

/* 파일 업로드 영역 */
.upload-container {
    border: 2px dashed var(--border-color);
    border-radius: 10px;
    padding: 2rem;
    text-align: center;
    transition: var(--transition);
    background-color: var(--white);
}

.upload-container.highlight {
    border-color: var(--primary-color);
    background-color: rgba(76, 110, 245, 0.05);
}

.upload-container.has-file {
    border-color: var(--primary-color);
    background-color: rgba(76, 110, 245, 0.05);
}

.file-input-container {
    margin-bottom: 1.5rem;
}

.file-input-container input[type="file"] {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
}

.file-input-container label {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    padding: 1rem;
}

.upload-icon {
    width: 60px;
    height: 60px;
    margin-bottom: 1rem;
    color: var(--primary-color);
}

.upload-icon svg {
    width: 100%;
    height: 100%;
}

.primary-text {
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
    color: var(--text-color);
}

.secondary-text {
    font-size: 0.9rem;
    color: var(--light-text);
}

button {
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: 5px;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    cursor: pointer;
    transition: var(--transition);
}

button:hover:not([disabled]) {
    background-color: var(--primary-dark);
}

button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* 진행 상태 표시 */
.progress-section {
    text-align: center;
    padding: 2rem;
    background-color: var(--white);
    border-radius: 10px;
    box-shadow: var(--shadow);
}

.progress-container {
    margin: 1.5rem 0;
}

.progress-bar {
    height: 10px;
    background-color: var(--border-color);
    border-radius: 5px;
    overflow: hidden;
    margin-bottom: 0.5rem;
}

.progress-fill {
    height: 100%;
    background-color: var(--primary-color);
    width: 0%;
    transition: width 0.3s ease;
}

.progress-text {
    text-align: right;
    font-size: 0.9rem;
    color: var(--light-text);
}

.status-message {
    color: var(--text-color);
}

/* 결과 영역 */
.result-section {
    display: flex;
    justify-content: center;
}

.result-card {
    text-align: center;
    padding: 2rem;
    background-color: var(--white);
    border-radius: 10px;
    box-shadow: var(--shadow);
    width: 100%;
    max-width: 500px;
}

.result-icon {
    width: 60px;
    height: 60px;
    margin: 0 auto 1.5rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}

.success-icon {
    background-color: rgba(55, 178, 77, 0.1);
    color: var(--success-color);
}

.error-icon {
    background-color: rgba(224, 49, 49, 0.1);
    color: var(--error-color);
}

.result-icon svg {
    width: 30px;
    height: 30px;
}

.result-card h2 {
    margin-bottom: 1rem;
}

.result-card p {
    margin-bottom: 1.5rem;
    color: var(--light-text);
}

.download-button {
    display: inline-flex;
    align-items: center;
    background-color: var(--success-color);
    color: white;
    text-decoration: none;
    padding: 0.75rem 1.5rem;
    border-radius: 5px;
    transition: var(--transition);
}

.download-button:hover {
    background-color: #2f9e44;
}

.download-button svg {
    width: 20px;
    height: 20px;
    margin-right: 0.5rem;
}

.try-again-button {
    background-color: var(--light-text);
}

.try-again-button:hover {
    background-color: #495057;
}

/* 푸터 */
footer {
    text-align: center;
    color: var(--light-text);
    font-size: 0.9rem;
    margin-top: 2rem;
}
EOL

# 패키지 설치
pip install -r requirements.txt

# 애플리케이션 실행
uvicorn app:app --host 0.0.0.0 --port 8000 --reload