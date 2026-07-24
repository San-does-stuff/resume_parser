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
    const updatePredictionBtn = document.getElementById('updatePredictionBtn');
    const initialStateElement = document.getElementById('initialResumeState');

    // One row of elements per predicted job (rank 1, 2, and 3).
    const predictionRows = [
        {
            valueEl: document.getElementById('predictedJobValue1'),
            badgeEl: document.getElementById('confidenceBadge1'),
        },
        {
            valueEl: document.getElementById('predictedJobValue2'),
            badgeEl: document.getElementById('confidenceBadge2'),
        },
        {
            valueEl: document.getElementById('predictedJobValue3'),
            badgeEl: document.getElementById('confidenceBadge3'),
        },
    ];

    // Keeps track of which resume we're currently working with, and which
    // of its skills are currently toggled "on". Both get set after a
    // successful upload (or when the page loads with a previous resume
    // already in the session).
    let currentResumeId = null;
    let selectedSkills = new Set();

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
            const topPredictions = getTopPredictionsFromResponse(data);
            const resumeUrl = data.url || data.resume_url || '';

            currentResumeId = data.resume_id || null;

            updateExtractedPanel(extractedData);
            updateTopPredictionsPanel(topPredictions);
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

    updatePredictionBtn.addEventListener('click', function() {
        if (!currentResumeId) {
            return;
        }

        const skillsToSend = Array.from(selectedSkills);
        if (skillsToSend.length === 0) {
            updatePredictionBtn.textContent = 'Select at least 1 skill';
            setTimeout(function() {
                updatePredictionBtn.textContent = 'Update Prediction';
            }, 1500);
            return;
        }

        updatePredictionBtn.textContent = 'Updating...';
        updatePredictionBtn.disabled = true;

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        fetch('/upload-resume/update-prediction/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                resume_id: currentResumeId,
                selected_skills: skillsToSend,
            }),
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
                    const serverMessage = data.error || ('Update failed with status ' + response.status);
                    throw new Error(serverMessage);
                }
                return data;
            });
        })
        .then(function(data) {
            if (data.error) {
                throw new Error(data.error);
            }

            const topPredictions = getTopPredictionsFromResponse(data);
            updateTopPredictionsPanel(topPredictions);

            updatePredictionBtn.textContent = 'Updated ✓';
            updatePredictionBtn.disabled = false;
        })
        .catch(function(error) {
            updatePredictionBtn.textContent = error.message || 'Error — try again';
            updatePredictionBtn.disabled = false;
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

        renderSkillChips(skills);
        renderChipList(experienceChips, experienceLabels, 'Not detected');
        renderChipList(educationChips, educationLabels, 'Not detected');
    }

    // Renders the skills as clickable chips. Nothing is selected by
    // default -- clicking a chip HIGHLIGHTS it, adding it to the set of
    // skills that will be sent the next time "Update Prediction" is
    // clicked. Only highlighted skills get used.
    function renderSkillChips(skills) {
        skillsChips.innerHTML = '';
        selectedSkills = new Set();
        updatePredictionBtn.disabled = true;

        if (!skills.length) {
            const chip = document.createElement('span');
            chip.className = 'chip';
            chip.textContent = 'Not detected';
            skillsChips.appendChild(chip);
            return;
        }

        skills.forEach(function(skill) {
            const chip = document.createElement('span');
            chip.className = 'chip skill-chip';
            chip.textContent = skill;

            chip.addEventListener('click', function() {
                if (selectedSkills.has(skill)) {
                    selectedSkills.delete(skill);
                    chip.classList.remove('chip-highlighted');
                } else {
                    selectedSkills.add(skill);
                    chip.classList.add('chip-highlighted');
                }
                updatePredictionBtn.disabled = !currentResumeId || selectedSkills.size === 0;
            });

            skillsChips.appendChild(chip);
        });

        updatePredictionBtn.textContent = 'Update Prediction';
    }

    // Pull a list of predictions out of the server response. Backend
    // responses include "top_predictions" (a list of up to 3). Older
    // responses (or the initial page-load state) might only have a single
    // "prediction" object, so we wrap that in a list as a fallback.
    function getTopPredictionsFromResponse(data) {
        if (Array.isArray(data.top_predictions) && data.top_predictions.length > 0) {
            return data.top_predictions;
        }
        if (data.prediction) {
            return [data.prediction];
        }
        return [];
    }

    function updateTopPredictionsPanel(topPredictions) {
        for (let i = 0; i < predictionRows.length; i++) {
            const row = predictionRows[i];
            const prediction = topPredictions[i];

            if (!prediction) {
                row.valueEl.textContent = '—';
                row.badgeEl.textContent = '—';
                continue;
            }

            const jobCategory = prediction.job_category || 'Not Trained';
            // Prefer display_confidence (temperature-scaled so the top
            // few candidates are spread out and comparable to each
            // other) since raw confidence can make #2 and #3 round down
            // to 0% when #1 is an overwhelming match.
            const hasDisplay = typeof prediction.display_confidence === 'number';
            const confidence = Number(hasDisplay ? prediction.display_confidence : (prediction.confidence || 0));
            const boundedConfidence = Math.min(Math.max(confidence, 0), 1);
            const confidencePercent = Math.round(boundedConfidence * 100);

            row.valueEl.textContent = jobCategory;
            row.badgeEl.textContent = confidencePercent + '% match';
        }
    }

    function hydrateFromInitialState() {
        if (!initialStateElement) return;
        try {
            const state = JSON.parse(initialStateElement.textContent || '{}');

            currentResumeId = state.resume_id || null;

            if (hasExtractedContent(state.extracted_data)) {
                updateExtractedPanel(state.extracted_data);
            }

            const topPredictions = Array.isArray(state.top_predictions) && state.top_predictions.length > 0
                ? state.top_predictions
                : (hasPredictionContent(state.prediction) ? [state.prediction] : []);

            if (topPredictions.length > 0) {
                updateTopPredictionsPanel(topPredictions);
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

    function hasPredictionContent(prediction) {
        if (!prediction || typeof prediction !== 'object') return false;
        const category = String(prediction.job_category || '').trim();
        const confidence = Number(prediction.confidence);
        return Boolean(category) || Number.isFinite(confidence) && confidence > 0;
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