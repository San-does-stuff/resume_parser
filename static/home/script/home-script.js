document.addEventListener("DOMContentLoaded", function () {

    console.log("DOM Loaded. JS now runs correctly.");

    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const fileName = document.getElementById('fileName');
    const submitBtn = document.getElementById('submitBtn');
    const pdfIframe = document.getElementById('pdfIframe');
    const pdfOpenLink = document.getElementById('pdfOpenLink');
    const skillsChips = document.getElementById('skillsChips');
    const experienceChips = document.getElementById('experienceChips');
    const educationChips = document.getElementById('educationChips');
    const predictedJobValue = document.getElementById('predictedJobValue');
    const confidenceBadge = document.getElementById('confidenceBadge');
    const initialStateElement = document.getElementById('initialResumeState');

    hydrateFromInitialState();

    fileInput.addEventListener('change', function(e) {
        var file = e.target.files[0];
        if (file) processFile(file);
    });

    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', function() {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.classList.remove('dragover');

        var file = e.dataTransfer.files[0];

        if (file && file.type === 'application/pdf') {
            fileInput.files = e.dataTransfer.files;
            processFile(file);
        }
    });

    function processFile(file) {
        fileName.textContent = file.name;
        submitBtn.disabled = false;
        var url = URL.createObjectURL(file);
        pdfIframe.src = url;
        if (pdfOpenLink) {
            pdfOpenLink.href = url;
        }
    }

    submitBtn.addEventListener('click', function() {
        submitBtn.textContent = 'Submitting...';
        submitBtn.disabled = true;

        var formData = new FormData();
        formData.append('resume', fileInput.files[0]);
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        formData.append('csrfmiddlewaretoken', csrfToken);

        fetch('/upload-resume/', {
            method: 'POST',
            body: formData
        })
        .then(function(response) {
            return response.text().then(function(bodyText) {
                let data = {};
                try {
                    data = bodyText ? JSON.parse(bodyText) : {};
                } catch (parseError) {
                    data = {};
                }

                if (!response.ok) {
                    const serverMessage = data.error || ('Upload failed with status ' + response.status);
                    throw new Error(serverMessage);
                }
                return data;
            });
        })
        .then(function(data) {
            if (data.error) {
                throw new Error(data.error);
            }

            const extractedData = data.extracted_data || data.extractedData || {};
            const predictionData = data.prediction || {};
            const resumeUrl = data.url || data.resume_url || '';

            updateExtractedPanel(extractedData);
            updatePredictionPanel(predictionData);
            if (resumeUrl) {
                pdfIframe.src = resumeUrl;
                if (pdfOpenLink) {
                    pdfOpenLink.href = resumeUrl;
                }
                fileName.textContent = extractFilename(resumeUrl);
            }
            submitBtn.textContent = 'Done ✓';
            submitBtn.disabled = false;
        })
        .catch(function(error) {
            submitBtn.textContent = error.message || 'Error — try again';
            submitBtn.disabled = false;
        });

    }); 

    function updateExtractedPanel(extractedData) {
        const experience = extractedData.experience || [];
        const education = extractedData.education || [];
        const skills = extractedData.skills || [];

        const experienceLabels = experience
            .map(function(item) { return item.job_title; })
            .filter(Boolean);

        const educationLabels = education
            .map(function(item) { return item.degree; })
            .filter(Boolean);

        renderChipList(skillsChips, skills, 'Not detected');
        renderChipList(experienceChips, experienceLabels, 'Not detected');
        renderChipList(educationChips, educationLabels, 'Not detected');
    }

    function updatePredictionPanel(prediction) {
        const jobCategory = prediction.job_category || 'Not Trained';
        const modelAccuracy = Number(prediction.model_accuracy || 0);
        const confidence = Number(prediction.confidence || 0);
        const boundedConfidence = Math.min(Math.max(confidence, 0), 0.99);
        const accuracyPercent = Math.round(Math.min(Math.max(modelAccuracy, 0), 0.99) * 100);
        const confidencePercent = Math.round(boundedConfidence * 100);

        predictedJobValue.textContent = jobCategory;
        if (accuracyPercent > 0) {
            confidenceBadge.textContent = confidencePercent + '% confidence · ' + accuracyPercent + '% model acc';
        } else {
            confidenceBadge.textContent = confidencePercent + '% confidence';
        }
    }

    function hydrateFromInitialState() {
        if (!initialStateElement) return;
        try {
            const state = JSON.parse(initialStateElement.textContent || '{}');
            if (hasExtractedContent(state.extracted_data)) {
                updateExtractedPanel(state.extracted_data);
            }
            if (state.prediction) {
                updatePredictionPanel(state.prediction);
            }
            if (state.resume_url) {
                pdfIframe.src = state.resume_url;
                if (pdfOpenLink) {
                    pdfOpenLink.href = state.resume_url;
                }
                fileName.textContent = extractFilename(state.resume_url);
            }
        } catch (error) {
            console.error('Failed to hydrate initial resume state', error);
        }
    }

    function hasExtractedContent(extractedData) {
        if (!extractedData || typeof extractedData !== 'object') return false;
        const skills = extractedData.skills || [];
        const experience = extractedData.experience || [];
        const education = extractedData.education || [];
        return skills.length > 0 || experience.length > 0 || education.length > 0;
    }

    function extractFilename(pathValue) {
        if (!pathValue) return 'No file selected';
        const lastSegment = pathValue.split('/').pop();
        return lastSegment || 'No file selected';
    }

    function renderChipList(container, items, emptyLabel) {
        container.innerHTML = '';

        if (!items.length) {
            const chip = document.createElement('span');
            chip.className = 'chip';
            chip.textContent = emptyLabel;
            container.appendChild(chip);
            return;
        }

        items.forEach(function(item) {
            const chip = document.createElement('span');
            chip.className = 'chip';
            chip.textContent = item;
            container.appendChild(chip);
        });
    }

}); 