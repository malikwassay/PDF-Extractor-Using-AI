from flask import Flask, request, render_template, jsonify, flash, redirect, url_for
import google.generativeai as genai
import io
import httpx
import os
import time
import mimetypes
import tempfile
import json
import re
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import platform

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8MB max file size

# Configure the API key from environment variable
# Make sure to set your API key as an environment variable: GEMINI_API_KEY
API_KEY = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=API_KEY)

# Supported file types and their MIME types
SUPPORTED_FORMATS = {
    '.pdf': 'application/pdf',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.doc': 'application/msword'
}


def convert_to_camel_case(text):
    """Convert a string to camelCase format"""
    # Split by spaces and convert to lowercase
    words = text.split()
    if not words:
        return text
    
    # First word is lowercase, subsequent words are title case
    camel_case = words[0].lower()
    for word in words[1:]:
        camel_case += word.capitalize()
    
    return camel_case


def convert_keys_to_camel_case(obj):
    """Recursively convert all keys in a dictionary/list to camelCase"""
    if isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            # Convert key to camelCase
            new_key = convert_to_camel_case(key)
            # Recursively process the value
            new_dict[new_key] = convert_keys_to_camel_case(value)
        return new_dict
    elif isinstance(obj, list):
        # Process each item in the list
        return [convert_keys_to_camel_case(item) for item in obj]
    else:
        # Return the value as-is if it's not a dict or list
        return obj


def clean_ai_response(response_text):
    """Clean AI response by removing markdown formatting and parsing JSON if possible"""
    try:
        # Remove markdown code block formatting
        cleaned = re.sub(r'```json\s*', '', response_text)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        
        # Remove extra whitespace and newlines
        cleaned = cleaned.strip()
        
        # Try to parse as JSON to validate and reformat
        try:
            parsed_json = json.loads(cleaned)
            # Convert keys to camelCase
            camel_case_json = convert_keys_to_camel_case(parsed_json)
            return camel_case_json, json.dumps(camel_case_json, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            # If not valid JSON, just return cleaned text
            return None, cleaned
            
    except Exception:
        # If cleaning fails, return original
        return None, response_text

def get_file_mime_type(file_path):
    """Determine the MIME type of a file based on its extension"""
    file_extension = Path(file_path).suffix.lower()
    
    if file_extension in SUPPORTED_FORMATS:
        return SUPPORTED_FORMATS[file_extension]
    else:
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'

def validate_file_format(filename):
    """Validate if the file format is supported"""
    file_extension = Path(filename).suffix.lower()
    return file_extension in SUPPORTED_FORMATS

def convert_with_python_docx(docx_path, pdf_path):
    """Fallback method using python-docx and reportlab"""
    try:
        from docx import Document
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        
        # Read the DOCX file
        doc = Document(docx_path)
        
        # Create PDF
        pdf_doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Extract text from DOCX and add to PDF
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                # Clean text for reportlab (escape special characters)
                clean_text = paragraph.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(clean_text, styles['Normal']))
                story.append(Spacer(1, 0.2*inch))
        
        if not story:  # If no content found, add a placeholder
            story.append(Paragraph("Document content could not be extracted.", styles['Normal']))
        
        pdf_doc.build(story)
        
    except ImportError:
        raise Exception("Please install required packages: pip install python-docx reportlab")
    except Exception as e:
        raise Exception(f"python-docx conversion failed: {str(e)}")

def convert_docx_to_pdf(docx_path):
    """Convert DOCX file to PDF and return the PDF path"""
    try:
        # Create a temporary PDF file path
        pdf_path = docx_path.replace('.docx', '.pdf').replace('.doc', '.pdf')
        
        # Check if running on Windows (docx2pdf works best on Windows)
        if platform.system() == 'Windows':
            try:
                # Try to initialize COM before using docx2pdf
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                    com_initialized = True
                except ImportError:
                    print("pythoncom not available, trying without COM initialization...")
                    com_initialized = False
                
                # Use docx2pdf for Windows
                from docx2pdf import convert
                convert(docx_path, pdf_path)
                
                # Uninitialize COM if we initialized it
                if com_initialized:
                    pythoncom.CoUninitialize()
                
            except Exception as e:
                print(f"docx2pdf failed: {e}")
                # If docx2pdf fails, try LibreOffice method
                try:
                    import subprocess
                    # Try different LibreOffice executable names for Windows
                    libreoffice_commands = ['soffice', 'libreoffice', 'C:\\Program Files\\LibreOffice\\program\\soffice.exe']
                    
                    conversion_successful = False
                    for cmd in libreoffice_commands:
                        try:
                            result = subprocess.run([
                                cmd, '--headless', '--convert-to', 'pdf', 
                                '--outdir', os.path.dirname(pdf_path), docx_path
                            ], capture_output=True, text=True, timeout=60)
                            
                            if result.returncode == 0:
                                conversion_successful = True
                                break
                        except (subprocess.TimeoutExpired, FileNotFoundError):
                            continue
                    
                    if not conversion_successful:
                        raise Exception("LibreOffice conversion failed or not found")
                        
                except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                    # Fall back to python-docx + reportlab method
                    print("LibreOffice not available, using python-docx + reportlab...")
                    convert_with_python_docx(docx_path, pdf_path)
        else:
            # For Linux/Mac, try using LibreOffice command line first
            try:
                import subprocess
                result = subprocess.run([
                    'libreoffice', '--headless', '--convert-to', 'pdf', 
                    '--outdir', os.path.dirname(pdf_path), docx_path
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    raise Exception(f"LibreOffice conversion failed: {result.stderr}")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # If LibreOffice is not available, use python-docx + reportlab
                print("LibreOffice not available, using python-docx + reportlab...")
                convert_with_python_docx(docx_path, pdf_path)
        
        if not os.path.exists(pdf_path):
            raise Exception("PDF conversion failed - output file not created")
            
        return pdf_path
        
    except Exception as e:
        raise Exception(f"Error converting DOCX to PDF: {str(e)}")

def get_prompt_for_file_type(file_path):
    """Get appropriate prompt based on file type"""
    file_extension = Path(file_path).suffix.lower()
    
    if file_extension in ['.pdf', '.docx', '.doc']:
        return """
        You are an intelligent information extractor. Carefully extract all relevant details from the given document and return ONLY a clean JSON object. Do not include any markdown formatting, code blocks, or explanatory text.

        ⚠️ Important:
        - Return ONLY valid JSON without any ```json``` code blocks or extra formatting
        - ONLY include fields that are explicitly mentioned or can be confidently extracted from the document
        - Do NOT include any field in the JSON if the information is missing, unavailable, or unclear

        Extract the following and return as a JSON object:

        1. **Personal Information**:
        - First Name 
        - Last Name
        - Gender
        - Nationality
        - Current Country of Residence
        - Date of Birth
        - Passport Number
        - Passport Expiry Date
        - Email Address (consider only personal Email - Do not consider lecturer or institute email as personal email)
        - Phone Number

        2. **Address Details** (Do not include the Test Center as Address):
        - Country (Even using the city you can)
        - Province / State
        - City (Even if Board is given there you will find the city)
        - Postal / Zip Code
        - Home Address

        3. **Emergency Contact**:
        - Name
        - Email Address
        - Relation with Applicant
        - Phone Number
        - Country 
        - Province / State
        - City
        - Postal / Zip Code
        - Home Address

        4. **Academic History** (May include multiple records):
        - Obtain Degree (if applicablek)
        - Roll Number
        - Total number
        - Obtain number
        - Country of Education
        - Level of Education (e.g., Secondary (SSC / O Levels / Level 2 Diploma), HSSC / A Levels / Level 3 Diploma, Diploma Qualification (HNC / Level 4, HND / Level 5), Undergraduate, Postgraduate)
        - Diploma Qualification (if applicable)
        - Grading Scheme (e.g., CGPA, Grade, Percentage)
        - Grade Average
        - Institute Name 
        - Program Start Date
        - Program End Date
        - Program Duration

        5. **English Proficiency Test**:
        - Exam Type (e.g., IELTS, LanguageCert, PTE, Duolingo, TOEFL)
        - Date of Exam
        - Overall Score
        - Sectional Scores (Listening, Reading, Writing, Speaking)
        - Valid Until
        - Issue Date

        Return ONLY the JSON object with extracted data. No explanations, no code blocks, just clean JSON.
        """
    elif file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif']:
        return """
        You are an intelligent image analyzer and OCR specialist. Analyze the given image and extract all relevant text and information. Return ONLY a clean JSON object without any markdown formatting or code blocks.

        ⚠️ Important:
        - Return ONLY valid JSON without any ```json``` code blocks or extra formatting
        - ONLY include fields that are clearly visible and readable in the image
        - Do NOT include any field in the JSON if the information is missing, unclear, or not visible


        Extract any of the following if visible and return as a JSON object:

        1. **Document Type**: (e.g., ID Card, Passport, Driver's License, Certificate, Form, etc.)

        2. **Personal Information**:
        - First Name 
        - Last Name
        - Gender
        - Nationality
        - Current Country of Residence
        - Date of Birth
        - Passport Number
        - Passport Expiry Date
        - Email Address (consider only personal Email - Do not consider lecturer or institute email as personal email)
        - Phone Number

        3. **Address Details** (Do not include the Test Center as Address, Do not include educational address):
        - Country (Even using the city you can)
        - Province / State
        - City (Even if Board is given there you will find the city)
        - Postal / Zip Code
        - Home Address

        4. **Emergency Contact**:
        - Name
        - Email Address
        - Relation with Applicant
        - Phone Number
        - Country 
        - Province / State
        - City
        - Postal / Zip Code
        - Home Address

        5. **Academic History** (May include multiple records):
        - Obtain Degree (if applicablek)
        - Roll Number
        - Total number
        - Obtain number
        - Country of Education
        - Level of Education (e.g., Secondary (SSC / O Levels / Level 2 Diploma), HSSC / A Levels / Level 3 Diploma, Diploma Qualification (HNC / Level 4, HND / Level 5), Undergraduate, Postgraduate)
        - Diploma Qualification (if applicable)
        - Grading Scheme (e.g., CGPA, Grade, Percentage)
        - Grade Average
        - Institute Name 
        - Program Start Date
        - Program End Date
        - Program Duration

        6. **English Proficiency Test**:
        - Exam Type (e.g., IELTS, LanguageCert, PTE, Duolingo, TOEFL)
        - Date of Exam
        - Overall Score
        - Sectional Scores (Listening, Reading, Writing, Speaking)
        - Valid Until
        - Issue Date


        7. **Additional Information**:
        - Any other relevant text or data visible in the image
        - Dates, numbers, or codes
        - Signatures or stamps (describe if present)

        Return ONLY the JSON object with extracted data. No explanations, no code blocks, just clean JSON.
        """
    else:
        return """
        Analyze this file and extract all relevant information. Return the results as a clean JSON object without any markdown formatting or code blocks. If it's a document, extract key details. If it's an image, describe what you see and extract any text or data visible.
        
        Return ONLY valid JSON without any ```json``` code blocks or extra formatting.
        """

def process_file_with_gemini(file_path, prompt_text, filename):
    """Process a file with Google's Gemini AI model"""
    try:
        original_file_path = file_path
        pdf_converted = False
        
        # Check if it's a DOCX file and convert to PDF
        file_extension = Path(file_path).suffix.lower()
        if file_extension in ['.docx', '.doc']:
            try:
                print(f"Converting {file_extension} to PDF...")
                pdf_path = convert_docx_to_pdf(file_path)
                file_path = pdf_path  # Use the converted PDF path
                pdf_converted = True
                print("Conversion successful!")
            except Exception as e:
                print(f"Warning: Could not convert {file_extension} to PDF: {str(e)}")
                print("Proceeding with original file...")
        
        # Get MIME type (use PDF mime type if converted)
        if pdf_converted:
            mime_type = 'application/pdf'
        else:
            mime_type = get_file_mime_type(file_path)
        
        # Upload the file to Google AI
        uploaded_file = genai.upload_file(
            path=file_path,
            mime_type=mime_type,
            display_name=filename
        )
        
        # Wait for the file to be processed
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)
        
        if uploaded_file.state.name == "FAILED":
            raise ValueError(f"File processing failed: {uploaded_file.state}")
        
        # Initialize the model
        # model = genai.GenerativeModel('gemini-1.5-flash')
        model = genai.GenerativeModel('gemini-2.0-flash')
        # model = genai.GenerativeModel('gemini-2.5-pro')

        
        # Generate content with the uploaded file
        response = model.generate_content([uploaded_file, prompt_text])
        
        # Clean up - delete the uploaded file
        genai.delete_file(uploaded_file.name)
        
        # Clean up converted PDF if it was created
        if pdf_converted and file_path != original_file_path:
            try:
                os.unlink(file_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary PDF file: {str(e)}")
        
        return response.text
        
    except Exception as e:
        # Clean up files in case of error
        if 'pdf_converted' in locals() and pdf_converted and 'file_path' in locals() and file_path != original_file_path:
            try:
                os.unlink(file_path)
            except:
                pass
        return f"Error processing file: {str(e)}"

def process_url_with_gemini(file_url, prompt_text):
    """Process a file from URL with Google's Gemini AI model"""
    try:
        # Download the file
        response = httpx.get(file_url, follow_redirects=True)
        response.raise_for_status()
        
        # Determine file extension from URL or content type
        file_extension = Path(file_url).suffix.lower()
        if not file_extension:
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type:
                file_extension = '.pdf'
            elif 'png' in content_type:
                file_extension = '.png'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                file_extension = '.jpg'
            elif 'wordprocessingml' in content_type:
                file_extension = '.docx'
            elif 'msword' in content_type:
                file_extension = '.doc'
            else:
                file_extension = '.bin'
        
        # Validate file format
        if file_extension not in SUPPORTED_FORMATS:
            supported_formats = ', '.join(SUPPORTED_FORMATS.keys())
            return f"Error: Unsupported file format '{file_extension}'. Supported formats: {supported_formats}"
        
        # Save the file content to a temporary file
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        
        original_temp_path = temp_file_path
        pdf_converted = False
        
        # Check if it's a DOCX file and convert to PDF
        if file_extension in ['.docx', '.doc']:
            try:
                print(f"Converting {file_extension} to PDF...")
                pdf_path = convert_docx_to_pdf(temp_file_path)
                temp_file_path = pdf_path  # Use the converted PDF path
                pdf_converted = True
                print("Conversion successful!")
            except Exception as e:
                print(f"Warning: Could not convert {file_extension} to PDF: {str(e)}")
                print("Proceeding with original file...")
        
        # Get MIME type (use PDF mime type if converted)
        if pdf_converted:
            mime_type = 'application/pdf'
        else:
            mime_type = SUPPORTED_FORMATS[file_extension]
        
        # Upload the file to Google AI
        uploaded_file = genai.upload_file(
            path=temp_file_path,
            mime_type=mime_type,
            display_name=f'Downloaded_File{file_extension}'
        )
        
        # Wait for the file to be processed
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)
        
        if uploaded_file.state.name == "FAILED":
            raise ValueError(f"File processing failed: {uploaded_file.state}")
        
        # Initialize the model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Generate content with the uploaded file
        ai_response = model.generate_content([uploaded_file, prompt_text])
        
        # Clean up - delete the uploaded file and temporary files
        genai.delete_file(uploaded_file.name)
        os.unlink(original_temp_path)
        if pdf_converted and temp_file_path != original_temp_path:
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary PDF file: {str(e)}")
        
        return ai_response.text
        
    except httpx.RequestError as e:
        return f"Error downloading file: {str(e)}"
    except Exception as e:
        return f"Error processing file: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html', supported_formats=list(SUPPORTED_FORMATS.keys()))


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """API endpoint for file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        custom_prompt = request.form.get('custom_prompt', '').strip()
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not validate_file_format(file.filename):
            return jsonify({
                'error': f'Unsupported file format. Supported formats: {", ".join(SUPPORTED_FORMATS.keys())}'
            }), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)
        
        try:
            # Get appropriate prompt
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = get_prompt_for_file_type(temp_path)
            
            # Process file with Gemini
            raw_result = process_file_with_gemini(temp_path, prompt, filename)
            
            # Clean the AI response
            parsed_json, cleaned_result = clean_ai_response(raw_result)
            
            print("Raw result:", raw_result)
            print("Cleaned result:", cleaned_result)
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            # Return structured response
            if parsed_json:
                return jsonify({
                    'result': parsed_json,  # Return as proper JSON object with camelCase keys
                })
            else:
                # If not JSON, return as text
                return jsonify({
                    'result': cleaned_result,
                })
            
        except Exception as e:
            # Clean up temporary file in case of error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process_url', methods=['POST'])
def api_process_url():
    """API endpoint for URL processing"""
    try:
        data = request.get_json()
        file_url = data.get('file_url', '').strip()
        custom_prompt = data.get('custom_prompt', '').strip()
        
        if not file_url:
            return jsonify({'error': 'Please provide a file URL'}), 400
        
        # Download file from URL to temporary location
        try:
            import urllib.request
            from urllib.parse import urlparse
            
            # Parse URL to get filename
            parsed_url = urlparse(file_url)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                # If no filename in URL, try to get from content-disposition or use default
                filename = 'downloaded_file'
            
            # Validate file format before downloading
            if not validate_file_format(filename):
                return jsonify({
                    'error': f'Unsupported file format. Supported formats: {", ".join(SUPPORTED_FORMATS.keys())}'
                }), 400
            
            # Create secure filename and temp path
            filename = secure_filename(filename)
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            
            # Download file
            urllib.request.urlretrieve(file_url, temp_path)
            
            # Get appropriate prompt (same logic as api_upload)
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = get_prompt_for_file_type(temp_path)
            
            # Process file with Gemini
            raw_result = process_file_with_gemini(temp_path, prompt, filename)
            
            # Clean the AI response
            parsed_json, cleaned_result = clean_ai_response(raw_result)
            
            print("Raw result:", raw_result)
            print("Cleaned result:", cleaned_result)
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            # Return structured response
            if parsed_json:
                return jsonify({
                    'result': parsed_json,  # Return as proper JSON object with camelCase keys
                })
            else:
                # If not JSON, return as text
                return jsonify({
                    'result': cleaned_result,
                })
                
        except Exception as e:
            # Clean up temporary file in case of error
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'supported_formats': list(SUPPORTED_FORMATS.keys()),
        'max_file_size': '16MB'
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)