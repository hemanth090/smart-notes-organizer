from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import google.generativeai as genai
from PIL import Image
import pytesseract
import cv2
import numpy as np
import logging
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"]
    }
})

# Configure app
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'your_secret_key_here'

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def process_image(image):
    try:
        # Convert PIL Image to OpenCV format
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Resize if image is too large
        max_dimension = 2000
        height, width = img_cv.shape[:2]
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            img_cv = cv2.resize(img_cv, None, fx=scale, fy=scale)
        
        # Image preprocessing
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Extract text using Tesseract
        extracted_text = pytesseract.image_to_string(denoised)
        return extracted_text.strip()
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise

def enhance_notes(text):
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Enhance and organize these notes into a well-structured format:
        {text}
        
        Please:
        1. Fix any spelling or grammar errors
        2. Organize into clear sections
        3. Add proper formatting (headers, lists, etc.)
        4. Expand abbreviations
        5. Add markdown formatting
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error enhancing notes: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capabilities')
def capabilities():
    return render_template('capabilities.html')

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/process_image', methods=['POST', 'OPTIONS'])
def process_image_route():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        logger.debug("Received image processing request")
        logger.debug(f"Request headers: {request.headers}")
        
        if 'image' not in request.files:
            logger.error("No image file in request")
            return jsonify({'error': 'No image file provided'}), 400
            
        file = request.files['image']
        if file.filename == '':
            logger.error("Empty filename")
            return jsonify({'error': 'No selected file'}), 400
            
        if file:
            # Process the image
            image = Image.open(file)
            extracted_text = process_image(image)
            enhanced_notes = enhance_notes(extracted_text)
            
            return jsonify({
                'success': True,
                'extracted_text': extracted_text,
                'enhanced_notes': enhanced_notes
            })
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
