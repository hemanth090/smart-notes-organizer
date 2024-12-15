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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
    static_url_path='',
    static_folder='static',
    template_folder='templates'
)

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
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-secret-key')

# Configure Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables!")
else:
    genai.configure(api_key=GEMINI_API_KEY)

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
        custom_config = r'--oem 3 --psm 6'
        extracted_text = pytesseract.image_to_string(denoised, config=custom_config)
        return extracted_text.strip()
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise

def enhance_notes(text):
    try:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")
            
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Enhance and organize these notes into a well-structured format:
        {text}
        
        Please:
        1. Fix any spelling or grammar errors
        2. Organize into clear sections with markdown headers
        3. Add proper formatting (lists, code blocks, etc.)
        4. Expand abbreviations
        5. Add emphasis for important points
        
        Format the output in clean markdown.
        """
        
        response = model.generate_content(prompt)
        if not response.text:
            raise ValueError("No response from Gemini API")
        return response.text
    except Exception as e:
        logger.error(f"Error enhancing notes: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_image', methods=['POST', 'OPTIONS'])
def process_image_route():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        logger.info("Received image processing request")
        logger.debug(f"Request headers: {request.headers}")
        
        if 'image' not in request.files:
            logger.error("No image file in request")
            return jsonify({'error': 'No image file provided'}), 400
            
        file = request.files['image']
        if file.filename == '':
            logger.error("Empty filename")
            return jsonify({'error': 'No selected file'}), 400
            
        if file:
            # Validate file type
            if not file.content_type.startswith('image/'):
                return jsonify({'error': 'Invalid file type. Please upload an image.'}), 400
                
            # Process the image
            image = Image.open(file)
            extracted_text = process_image(image)
            
            if not extracted_text:
                return jsonify({'error': 'No text could be extracted from the image'}), 400
                
            enhanced_notes = enhance_notes(extracted_text)
            
            return jsonify({
                'success': True,
                'extracted_text': extracted_text,
                'enhanced_notes': enhanced_notes
            })
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
