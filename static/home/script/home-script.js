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
  // TODO: hook up Django form submission here
  // e.g. fetch('/parse-resume/', { method: 'POST', body: formData })
});