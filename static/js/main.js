// Handle paste event for clipboard images
document.addEventListener('paste', function(e) {
    const items = e.clipboardData.items;

    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
            const blob = items[i].getAsFile();
            uploadImage(blob);
            break;
        }
    }
});

// Handle file input
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');

uploadArea.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        uploadImage(e.target.files[0]);
    }
});

// Upload image function
function uploadImage(file) {
    const formData = new FormData();
    formData.append('image', file);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('shareUrl').value = data.share_url;
            document.getElementById('result').classList.remove('hidden');
        } else {
            alert('Upload failed: ' + data.error);
        }
    })
    .catch(error => {
        alert('Upload failed: ' + error);
    });
}

// Copy link to clipboard
function copyLink() {
    const shareUrl = document.getElementById('shareUrl');
    shareUrl.select();
    document.execCommand('copy');
    alert('Link copied to clipboard!');
}
