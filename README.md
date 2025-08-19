# Document AI Extractor

A powerful Flask-based API service that uses Google's Gemini AI to extract structured information from various document formats including PDFs, images, and Microsoft Word documents. The service provides intelligent OCR, document parsing, and structured data extraction capabilities.

## Features

### Core Functionality
- **Multi-Format Support**: Process PDFs, images (PNG, JPG, GIF, WebP, etc.), and Word documents (DOCX, DOC)
- **AI-Powered Extraction**: Google Gemini AI for intelligent document analysis and information extraction
- **Document Conversion**: Automatic DOCX/DOC to PDF conversion for better processing
- **OCR Capabilities**: Extract text and data from scanned documents and images
- **Structured Output**: Returns data in clean JSON format with camelCase key conversion
- **URL Processing**: Download and process documents directly from URLs

### Advanced Capabilities
- **Smart Field Detection**: Automatically identifies and extracts relevant information based on document type
- **Academic Document Processing**: Specialized extraction for educational transcripts and certificates
- **Identity Document Parsing**: Extract data from passports, ID cards, and other official documents
- **English Proficiency Test Results**: Parse IELTS, TOEFL, PTE, and other test score reports
- **Address and Contact Information**: Intelligent extraction of personal and emergency contact details
- **Flexible Prompting**: Support for custom extraction prompts for specialized use cases

## Prerequisites

### Required Services
- **Google AI API**: Gemini AI API access for document processing
- **Python 3.8+**: Runtime environment
- **LibreOffice** (optional): For enhanced DOCX to PDF conversion

### API Keys Required
- Google AI (Gemini) API key

### System Dependencies (Optional)
- **LibreOffice**: For document conversion (Linux/Mac)
- **Microsoft Office**: For document conversion (Windows)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/malikwassay/PDF-Extractor-Using-AI
cd document-ai-extractor
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
```bash
pip install flask google-generativeai httpx python-docx reportlab docx2pdf
```

### 3. Environment Setup

Set your Google AI API key as an environment variable:

**Linux/Mac:**
```bash
export GEMINI_API_KEY="your-google-ai-api-key-here"
```

**Windows:**
```cmd
set GEMINI_API_KEY=your-google-ai-api-key-here
```

### 4. Optional Dependencies

For enhanced document conversion capabilities:

**LibreOffice (Linux/Mac):**
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice

# macOS
brew install libreoffice
```

**Additional Python packages for fallback conversion:**
```bash
pip install python-docx reportlab pythoncom  # pythoncom for Windows only
```

## Dependencies

```txt
flask>=2.3.0
google-generativeai>=0.3.0
httpx>=0.24.0
python-docx>=0.8.11
reportlab>=4.0.0
docx2pdf>=0.1.8  # Windows only
werkzeug>=2.3.0
```

## Usage

### Starting the Server
```bash
python app.py
```

The server will start on `http://0.0.0.0:5000` by default.

### API Endpoints

**Health Check:**
```bash
GET /health
```

**File Upload Processing:**
```bash
POST /api/upload
Content-Type: multipart/form-data

# Form fields:
# - file: The document file to process
# - custom_prompt: (optional) Custom extraction prompt
```

**URL Processing:**
```bash
POST /api/process_url
Content-Type: application/json

{
  "file_url": "https://example.com/document.pdf",
  "custom_prompt": "Extract specific information..."  // optional
}
```

## Supported File Formats

### Document Formats
- **PDF**: `.pdf` - Direct processing with Gemini AI
- **Word Documents**: `.docx`, `.doc` - Automatic conversion to PDF for processing
- **Images**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`, `.tiff`, `.tif` - OCR processing

### File Size Limits
- Maximum file size: 8MB
- Configurable via `MAX_CONTENT_LENGTH` setting

## API Reference

### POST /api/upload

Upload and process a document file.

**Request:**
```bash
curl -X POST \
  http://localhost:5000/api/upload \
  -F "file=@document.pdf" \
  -F "custom_prompt=Extract personal information"
```

**Response:**
```json
{
  "result": {
    "firstName": "John",
    "lastName": "Doe",
    "emailAddress": "john.doe@email.com",
    "phoneNumber": "+1234567890",
    "academicHistory": [
      {
        "levelOfEducation": "Undergraduate",
        "instituteName": "University Name",
        "gradeAverage": "3.8 GPA"
      }
    ]
  }
}
```

### POST /api/process_url

Process a document from a URL.

**Request:**
```bash
curl -X POST \
  http://localhost:5000/api/process_url \
  -H "Content-Type: application/json" \
  -d '{
    "file_url": "https://example.com/transcript.pdf",
    "custom_prompt": "Extract academic information"
  }'
```

**Response:**
```json
{
  "result": {
    "personalInformation": {
      "firstName": "Jane",
      "lastName": "Smith"
    },
    "academicHistory": [
      {
        "obtainDegree": "Bachelor of Science",
        "instituteName": "Tech University",
        "programStartDate": "2018-09",
        "programEndDate": "2022-05"
      }
    ]
  }
}
```

### GET /health

Check service health and configuration.

**Response:**
```json
{
  "status": "healthy",
  "supported_formats": [".pdf", ".png", ".jpg", ".docx", ".doc"],
  "max_file_size": "16MB"
}
```

## Extraction Categories

### Personal Information
- First Name, Last Name
- Gender, Nationality
- Date of Birth
- Passport Number and Expiry Date
- Email Address, Phone Number
- Current Country of Residence

### Address Details
- Country, Province/State, City
- Postal/Zip Code
- Home Address

### Emergency Contact
- Contact Name, Email, Phone
- Relation to Applicant
- Contact Address Details

### Academic History
- Degree Information
- Roll Number, Total/Obtained Marks
- Country and Level of Education
- Grading Scheme and Grade Average
- Institute Name and Program Dates
- Program Duration

### English Proficiency Tests
- Exam Type (IELTS, TOEFL, PTE, etc.)
- Date of Exam, Overall Score
- Sectional Scores (Listening, Reading, Writing, Speaking)
- Validity Period, Issue Date

### Additional Information
- Document Type Detection
- Signatures and Stamps
- Relevant Dates and Codes
- Other Extracted Text

## Technical Architecture

### Core Components

**Flask Application:**
```python
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8MB limit
```

**Google AI Integration:**
```python
import google.generativeai as genai
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')
```

**File Processing Pipeline:**
1. File validation and format checking
2. Document conversion (DOCX → PDF if needed)
3. File upload to Google AI
4. AI processing with specialized prompts
5. Response cleaning and JSON formatting
6. camelCase key conversion
7. Cleanup of temporary files

### Document Conversion

**DOCX to PDF Conversion:**
```python
def convert_docx_to_pdf(docx_path):
    # Platform-specific conversion logic
    # Windows: docx2pdf or LibreOffice
    # Linux/Mac: LibreOffice or python-docx + reportlab
```

**Conversion Methods:**
1. **docx2pdf** (Windows preferred)
2. **LibreOffice CLI** (Cross-platform)
3. **python-docx + reportlab** (Fallback)

### Prompt Engineering

**Document-Specific Prompts:**
- PDF/DOCX: Comprehensive information extraction
- Images: OCR with document type detection
- Custom: User-defined extraction requirements

**Smart Field Detection:**
- Automatic identification of document types
- Context-aware information extraction
- Structured output formatting

## Configuration

### Environment Variables

**Required:**
```bash
GEMINI_API_KEY=your-google-ai-api-key
```

**Optional:**
```bash
FLASK_ENV=development
FLASK_DEBUG=True
MAX_CONTENT_LENGTH=8388608  # 8MB in bytes
```

### Application Settings

**File Size Limits:**
```python
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8MB
```

**Supported Formats:**
```python
SUPPORTED_FORMATS = {
    '.pdf': 'application/pdf',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    # ... additional formats
}
```

### Model Configuration

**Gemini Model Selection:**
```python
# Available models (configure based on needs)
model = genai.GenerativeModel('gemini-2.0-flash')      # Latest, fastest
model = genai.GenerativeModel('gemini-1.5-flash')     # Stable, fast
model = genai.GenerativeModel('gemini-1.5-pro')       # High accuracy
```

## Error Handling

### File Processing Errors
- Invalid file format detection
- File size limit enforcement
- Document conversion failure handling
- Temporary file cleanup

### API Error Responses
```json
{
  "error": "Unsupported file format. Supported formats: .pdf, .png, .jpg, .docx, .doc"
}
```

### Conversion Fallbacks
- Multiple conversion methods for DOCX files
- Graceful degradation when tools unavailable
- Error reporting for failed conversions

## Security Considerations

### File Handling
- Secure filename generation with `werkzeug.utils.secure_filename`
- Temporary file cleanup after processing
- File size validation to prevent abuse
- Format validation before processing

### API Security
- Input validation for all endpoints
- Error message sanitization
- Temporary file isolation
- No persistent file storage

### Data Privacy
- Files processed temporarily and deleted immediately
- No data retention on server
- Google AI file cleanup after processing
- Secure API key management

## Performance Optimization

### Processing Efficiency
- Asynchronous file processing where possible
- Efficient temporary file management
- Smart document conversion choices
- Optimized prompt engineering

### Resource Management
- Memory-efficient file handling
- Automatic cleanup of temporary files
- Connection pooling for external APIs
- Request timeout management

### Caching Strategies
- No persistent caching (privacy-focused)
- Efficient in-memory processing
- Optimized API calls to Google AI

## Deployment

### Local Development
```bash
# Set environment variables
export GEMINI_API_KEY="your-api-key"

# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py
```

### Production Deployment

**Docker Deployment:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install LibreOffice for document conversion
RUN apt-get update && apt-get install -y libreoffice

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

**Environment Configuration:**
```bash
# Production environment variables
export GEMINI_API_KEY="production-api-key"
export FLASK_ENV="production"
export MAX_CONTENT_LENGTH="16777216"  # 16MB
```

**WSGI Server:**
```bash
# Install production server
pip install gunicorn

# Run with gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
```

### Cloud Deployment

**Key Considerations:**
- Ensure LibreOffice availability in container
- Configure proper memory limits for large documents
- Set up proper logging and monitoring
- Configure reverse proxy for production traffic

## Integration Examples

### Python Client Example
```python
import requests

# File upload
files = {'file': open('document.pdf', 'rb')}
response = requests.post('http://localhost:5000/api/upload', files=files)
data = response.json()

# URL processing
payload = {
    'file_url': 'https://example.com/document.pdf',
    'custom_prompt': 'Extract contact information'
}
response = requests.post('http://localhost:5000/api/process_url', json=payload)
data = response.json()
```

### JavaScript/Node.js Example
```javascript
// File upload
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:5000/api/upload', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));

// URL processing
fetch('http://localhost:5000/api/process_url', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    file_url: 'https://example.com/document.pdf'
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

### cURL Examples
```bash
# File upload
curl -X POST \
  http://localhost:5000/api/upload \
  -F "file=@transcript.pdf" \
  -F "custom_prompt=Extract academic information"

# URL processing
curl -X POST \
  http://localhost:5000/api/process_url \
  -H "Content-Type: application/json" \
  -d '{"file_url": "https://example.com/passport.jpg"}'

# Health check
curl http://localhost:5000/health
```

## Troubleshooting

### Common Issues

**Google AI API Errors:**
- Verify API key configuration in environment variables
- Check API quotas and rate limits
- Ensure proper internet connectivity
- Validate supported file formats

**Document Conversion Problems:**
- Install LibreOffice for better DOCX conversion
- Check file permissions for temporary directory
- Verify sufficient disk space for conversion
- Monitor conversion timeout issues

**File Processing Errors:**
- Validate file format support
- Check file size limits (8MB default)
- Ensure proper file encoding
- Monitor memory usage for large files

**OCR Accuracy Issues:**
- Use high-quality, clear images
- Ensure proper image resolution
- Consider document orientation
- Validate text visibility and contrast

### Debugging Steps

1. **Environment Validation:**
   ```bash
   # Check API key
   echo $GEMINI_API_KEY
   
   # Verify Python packages
   pip list | grep -E "(flask|google-generativeai|httpx)"
   
   # Test LibreOffice availability
   libreoffice --version
   ```

2. **API Testing:**
   ```bash
   # Test health endpoint
   curl http://localhost:5000/health
   
   # Test with sample file
   curl -X POST -F "file=@sample.pdf" http://localhost:5000/api/upload
   ```

3. **Log Analysis:**
   ```python
   # Enable debug logging in app.py
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## Performance Tuning

### File Processing Optimization
- Use appropriate Gemini model for speed vs. accuracy trade-offs
- Implement request queuing for high-volume scenarios
- Optimize prompt engineering for faster responses
- Consider image preprocessing for better OCR results

### Resource Management
- Monitor memory usage for large document processing
- Implement proper timeout handling
- Use efficient file streaming for large uploads
- Configure appropriate worker processes for production

## Future Enhancements

### Planned Features
- **Batch Processing**: Multiple file processing in single request
- **Webhook Support**: Asynchronous processing with callbacks
- **Template Extraction**: Predefined extraction templates for common document types
- **Multi-language Support**: Enhanced OCR for non-English documents
- **Database Integration**: Optional result storage and retrieval

### Technical Improvements
- **Caching Layer**: Redis integration for improved performance
- **Queue System**: Celery integration for background processing
- **Authentication**: API key-based access control
- **Rate Limiting**: Request throttling and quota management
- **Advanced OCR**: Integration with specialized OCR engines


---

**Note**: This application requires an active Google AI (Gemini) API key and processes documents temporarily in memory. Ensure all API credentials are properly configured and consider data privacy implications for production use.
