// static/home/script/home-script.js

console.log('DOM Loaded. JS now runs correctly.');

var fileInput = document.getElementById('fileInput');
var submitBtn = document.getElementById('submitBtn');
var fileName  = document.getElementById('fileName');

// ── File selection ──────────────────────────────────────
fileInput.addEventListener('change', function () {
    if (fileInput.files.length > 0) {
        fileName.textContent = fileInput.files[0].name;
        submitBtn.disabled   = false;

        // ── Show uploaded PDF in the iframe immediately ──
        var objectUrl = URL.createObjectURL(fileInput.files[0]);
        document.getElementById('pdfIframe').src = objectUrl;
    }
});

// ── Drag and drop ───────────────────────────────────────
var dropZone = document.getElementById('dropZone');

dropZone.addEventListener('dragover', function (e) {
    e.preventDefault();
    dropZone.style.borderColor = '#4a7fd4';
});

dropZone.addEventListener('dragleave', function () {
    dropZone.style.borderColor = '';
});

dropZone.addEventListener('drop', function (e) {
    e.preventDefault();
    dropZone.style.borderColor = '';
    if (e.dataTransfer.files.length) {
        fileInput.files      = e.dataTransfer.files;
        fileName.textContent = e.dataTransfer.files[0].name;
        submitBtn.disabled   = false;

        // ── Show dropped PDF in the iframe immediately ──
        var objectUrl = URL.createObjectURL(e.dataTransfer.files[0]);
        document.getElementById('pdfIframe').src = objectUrl;
    }
});

// ── Submit ──────────────────────────────────────────────
submitBtn.addEventListener('click', function () {
    if (!fileInput.files.length) return;

    var formData = new FormData();
    formData.append('resume', fileInput.files[0]);

    // Get CSRF token from the hidden input
    var csrfInput = document.getElementById('csrfToken');
    var csrf = csrfInput
        ? csrfInput.value.replace(/[^a-zA-Z0-9]/g, '')
        : getCookieCSRF('csrftoken');

    console.log('Uploading file:', fileInput.files[0].name);
    console.log('CSRF token:', csrf ? 'found' : 'NOT FOUND');

    submitBtn.textContent = 'Parsing...';
    submitBtn.disabled    = true;

    fetch('/api/parse-cv/', {
        method:  'POST',
        headers: { 'X-CSRFToken': csrf },
        body:    formData
    })
    .then(function (r) {
        console.log('Response status:', r.status);
        return r.json();
    })
    .then(function (data) {
        console.log('Parsed result:', data);
        if (data.success) {
            displayResults(data);
        } else {
            alert('Parsing failed: ' + (data.message || data.error || 'Unknown error'));
        }
        submitBtn.textContent = 'Submit';
        submitBtn.disabled    = false;
    })
    .catch(function (err) {
        console.error('Fetch error:', err);
        alert('Server error. Check the browser console (F12).');
        submitBtn.textContent = 'Submit';
        submitBtn.disabled    = false;
    });
});

// ── Display parsed results on the page ─────────────────
function displayResults(data) {

    var allValues = document.querySelectorAll('.field-value');

    // Full Name
    if (allValues[0]) {
        allValues[0].textContent = data.name || 'Not found';
    }

    // Email
    if (allValues[1]) {
        allValues[1].textContent = data.email || 'Not found';
    }

    // Experience
    if (allValues[2]) {
        if (data.experience && data.experience.length) {
            var expText = data.experience.map(function (e) {
                var parts = [];
                if (e.job_title)  parts.push(e.job_title);
                if (e.company)    parts.push('at ' + e.company);
                if (e.start_date) parts.push('(' + e.start_date + ' - ' + (e.end_date || 'Present') + ')');
                return parts.join(' ');
            }).join(' | ');
            allValues[2].textContent = expText;
        } else {
            allValues[2].textContent = 'Not found';
        }
    }

    // Education
    if (allValues[3]) {
        if (data.education && data.education.length) {
            var eduText = data.education.map(function (e) {
                var parts = [];
                if (e.degree)          parts.push(e.degree);
                if (e.institution)     parts.push('— ' + e.institution);
                if (e.graduation_year) parts.push(', ' + e.graduation_year);
                return parts.join(' ');
            }).join(' | ');
            allValues[3].textContent = eduText;
        } else {
            allValues[3].textContent = 'Not found';
        }
    }

    // Skills chips
    var chipsContainer = document.querySelector('.skills-chips');
    if (chipsContainer) {
        if (data.skills && data.skills.length > 0) {
            chipsContainer.innerHTML = data.skills.map(function (s) {
                return '<span class="chip">' + s + '</span>';
            }).join('');
        } else {
            chipsContainer.innerHTML = '<span class="chip">No skills detected</span>';
        }
    }

    // Predicted Job Title
    var jtValue = document.querySelector('.jt-value');
    if (jtValue && data.predicted_title) {
        jtValue.textContent = data.predicted_title;
    }

    // Confidence badge
    var badge = document.querySelector('.confidence-badge');
    if (badge && data.confidence) {
        badge.textContent = data.confidence + '% match';
    }

    // Scroll to extracted panel
    var panel = document.querySelector('.extracted-panel');
    if (panel) {
        panel.scrollIntoView({ behavior: 'smooth' });
    }
}

// ── CSRF cookie fallback ────────────────────────────────
function getCookieCSRF(name) {
    var val   = '; ' + document.cookie;
    var parts = val.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}