// Global variables
let dropzone, fileInput, results, enhancedNotes, loading;

// Initialize after DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize elements
    dropzone = document.getElementById('dropzone');
    fileInput = document.getElementById('fileInput');
    results = document.getElementById('results');
    enhancedNotes = document.getElementById('enhancedNotes');
    loading = document.getElementById('loading');

    // Configure marked.js
    marked.use({
        breaks: true,
        gfm: true
    });

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop zone when dragging over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropzone.addEventListener('drop', handleDrop, false);
    dropzone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFiles, false);

    // Copy functionality
    const copyButton = document.getElementById('copyButton');
    copyButton.addEventListener('click', copyNotes);
});

function preventDefaults (e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight(e) {
    dropzone.classList.add('drag-over');
}

function unhighlight(e) {
    dropzone.classList.remove('drag-over');
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles({ target: { files } });
}

function handleFiles(e) {
    const files = e.target.files;
    if (files.length) {
        const file = files[0];
        if (file.type.startsWith('image/')) {
            // Check file size (limit to 5MB)
            if (file.size > 5 * 1024 * 1024) {
                alert('Image size should be less than 5MB. Please choose a smaller image.');
                return;
            }
            uploadFile(file);
        } else {
            alert('Please upload an image file');
        }
    }
}

function uploadFile(file) {
    const formData = new FormData();
    formData.append('image', file);

    // Show loading indicator
    loading.classList.remove('hidden');
    dropzone.classList.add('hidden');
    results.classList.add('hidden');

    // Create AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    const apiUrl = window.location.origin + '/process_image';
    console.log('Sending request to:', apiUrl);

    fetch(apiUrl, {
        method: 'POST',
        body: formData,
        signal: controller.signal
    })
    .then(async response => {
        clearTimeout(timeoutId);
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Received data:', data);
        if (data.error) {
            throw new Error(data.error);
        }
        displayResults(data.enhanced_notes);
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error processing image: ' + error.message);
    })
    .finally(() => {
        loading.classList.add('hidden');
        dropzone.classList.remove('hidden');
        clearTimeout(timeoutId);
    });
}

function displayResults(markdown) {
    // Convert markdown to HTML using marked
    const htmlContent = marked.parse(markdown);
    
    // Display results
    enhancedNotes.innerHTML = htmlContent;
    results.classList.remove('hidden');
    dropzone.classList.add('hidden');
}

// Function to reset form - made global
window.resetForm = function() {
    // Clear the file input
    fileInput.value = '';
    
    // Hide results and show dropzone
    results.classList.add('hidden');
    dropzone.classList.remove('hidden');
    
    // Clear the enhanced notes
    enhancedNotes.innerHTML = '';
    
    // Remove any error messages or loading indicators
    loading.classList.add('hidden');
}

// Copy functionality - made global
window.copyNotes = function() {
    const notesContent = enhancedNotes.innerText;
    const copyButton = document.getElementById('copyButton');
    const originalText = copyButton.innerHTML;

    navigator.clipboard.writeText(notesContent)
        .then(() => {
            // Show success state
            copyButton.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                </svg>
                Copied!
            `;
            copyButton.classList.remove('bg-gray-600', 'hover:bg-gray-700');
            copyButton.classList.add('bg-green-600', 'hover:bg-green-700');

            // Reset button after 2 seconds
            setTimeout(() => {
                copyButton.innerHTML = originalText;
                copyButton.classList.remove('bg-green-600', 'hover:bg-green-700');
                copyButton.classList.add('bg-gray-600', 'hover:bg-gray-700');
            }, 2000);
        })
        .catch(err => {
            console.error('Failed to copy:', err);
            // Show error state
            copyButton.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
                Failed!
            `;
            copyButton.classList.remove('bg-gray-600', 'hover:bg-gray-700');
            copyButton.classList.add('bg-red-600', 'hover:bg-red-700');

            // Reset button after 2 seconds
            setTimeout(() => {
                copyButton.innerHTML = originalText;
                copyButton.classList.remove('bg-red-600', 'hover:bg-red-700');
                copyButton.classList.add('bg-gray-600', 'hover:bg-gray-700');
            }, 2000);
        });
}
