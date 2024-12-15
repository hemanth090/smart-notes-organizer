from flask import Flask, request, jsonify, render_template, send_from_directory, flash, redirect, url_for
import os
import google.generativeai as genai
from PIL import Image
import pytesseract
import cv2
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
    static_url_path='',
    static_folder='static',
    template_folder='templates'
)
app.secret_key = 'your_secret_key_here'  # Add a secret key for flash messages

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

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
        
        # Image preprocessing pipeline
        # 1. Convert to grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # 2. Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # 3. Denoise
        denoised = cv2.fastNlMeansDenoising(binary)
        
        # 4. Increase contrast
        contrast = cv2.convertScaleAbs(denoised, alpha=1.5, beta=0)
        
        # 5. Apply dilation to connect text components
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        dilated = cv2.dilate(contrast, kernel, iterations=1)
        
        # OCR Configuration
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?()[]{}:;\'\"- "'
        
        # Try OCR on different processed images
        text_results = []
        for img in [gray, binary, denoised, contrast, dilated]:
            try:
                text = pytesseract.image_to_string(img, config=custom_config)
                if text.strip():
                    text_results.append(text.strip())
            except:
                continue
        
        # Get the longest text result
        if text_results:
            text = max(text_results, key=len)
            # Clean up the text
            text = ' '.join(text.split())
            if len(text) < 10:  # If text is too short, likely noise
                raise ValueError("Insufficient text found in image")
            return text
        else:
            raise ValueError("No text found in image")
            
    except Exception as e:
        raise ValueError(f"Error processing image: {str(e)}")

def enhance_notes(text):
    if not text:
        raise ValueError("No text to enhance")

    try:
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config
        )

        chat_session = model.start_chat(history=[])

        prompt = f"""
        Transform this text into comprehensive, well-structured study notes. Follow these guidelines:

        # Main Topic
        - Start with a clear, concise title
        - Provide a brief overview (2-3 sentences)
        - List key takeaways (3-5 points)

        ## Core Concepts
        - Break down main ideas
        - Define important terms
        - Explain relationships between concepts
        - Use analogies when helpful

        ## Detailed Analysis
        - Deep dive into each concept
        - Provide examples and use cases
        - Include formulas or technical details
        - Highlight edge cases and limitations

        ## Practical Applications
        - Real-world examples
        - Implementation guidelines
        - Best practices
        - Common pitfalls to avoid

        ## Code Examples (if applicable)
        ```
        Include relevant code snippets
        Show practical implementations
        Explain key parts
        ```

        ## Visual Representations
        - Use ASCII diagrams if needed
        - Create tables for comparisons
        - List pros and cons
        - Show hierarchical relationships

        ## Summary
        - Recap key points
        - Connect concepts
        - Highlight critical insights
        - Future implications

        ## References
        - Related topics
        - Further reading
        - External resources
        - Research papers

        Formatting Rules:
        1. Use clean headings (# for main, ## for sub)
        2. Keep paragraphs short and focused
        3. Use bullet points for lists
        4. Include code blocks with language
        5. Create tables with | for data
        6. Use > for important notes
        7. Add --- for sections
        8. Number steps when sequential

        Here's the text to transform:
        {text}

        Remember:
        - Focus on clarity and understanding
        - Maintain logical flow
        - Include practical insights
        - Link related concepts
        - Add examples where helpful
        - Keep formatting minimal but effective
        """

        response = chat_session.send_message(prompt)
        if not response.text:
            raise ValueError("Failed to generate enhanced notes")
        
        return response.text.strip()

    except Exception as e:
        raise Exception(f"Error enhancing notes with Gemini AI: {str(e)}")

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

@app.route('/process_image', methods=['POST'])
def analyze_image():
    logger.debug("Received image upload request")
    logger.debug(f"Files in request: {request.files}")
    
    if 'image' not in request.files:
        logger.error("No image file in request")
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        try:
            logger.debug(f"Processing image: {file.filename}")
            # Open and process the image
            image = Image.open(file.stream)
            
            # Extract text from image
            extracted_text = process_image(image)
            if not extracted_text:
                logger.error("No text extracted from image")
                return jsonify({'error': 'No text could be extracted from the image'}), 400
            
            # Enhance the extracted text
            enhanced_notes = enhance_notes(extracted_text)
            logger.debug("Successfully processed image and enhanced notes")
            
            return jsonify({
                'enhanced_notes': enhanced_notes
            })
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    # Enable debug mode and set host/port
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
