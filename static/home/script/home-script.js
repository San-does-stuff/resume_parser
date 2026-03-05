document.addEventListener("DOMContentLoaded", function () {

    console.log("DOM Loaded. JS now runs correctly.");

    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const fileName = document.getElementById('fileName');
    const submitBtn = document.getElementById('submitBtn');
    const pdfIframe = document.getElementById('pdfIframe');

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
    }

    submitBtn.addEventListener('click', function() {
        submitBtn.textContent = 'Submitting...';
        submitBtn.disabled = true;

        var formData = new FormData();
        formData.append('resume', fileInput.files[0]);
        // formData.append('csrfmiddlewaretoken', '{{ csrf_token }}');
        formData.append('csrfmiddlewaretoken', document.getElementById('csrfToken').value);

        fetch('/upload-resume/', {
            method: 'POST',
            body: formData
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            submitBtn.textContent = 'Done ✓';
        })
        .catch(function(error) {
            submitBtn.textContent = 'Error — try again';
            submitBtn.disabled = false;
        });

    }); 

}); 