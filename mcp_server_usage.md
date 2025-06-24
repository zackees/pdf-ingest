# PDF Ingest MCP Server Usage Guide

The `mcp_server.py` is a FastAPI-based Model Context Protocol server that exposes the PDF ingest tool functionality through REST API endpoints.

## Starting the Server

### Using uv (Recommended)
```bash
./mcp_server.py
# Or with custom options:
./mcp_server.py --host 127.0.0.1 --port 8080 --reload
```

### Using Python directly
```bash
python3 mcp_server.py
```

## Available Endpoints

### 1. Root Endpoint - GET `/`
Returns server status and supported file formats.

**Example:**
```bash
curl http://localhost:8000/
```

### 2. Get Supported Formats - GET `/supported-formats`
Returns list of supported file formats.

**Example:**
```bash
curl http://localhost:8000/supported-formats
```

### 3. Scan Directory - POST `/scan`
Scans a directory for files that need processing without actually processing them.

**Request Body:**
```json
{
    "input_dir": "/path/to/input",
    "output_dir": "/path/to/output",
    "depth": 0
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "./test_data",
    "output_dir": "./output",
    "depth": 0
  }'
```

### 4. Process Documents - POST `/process`
Processes all documents in the specified directory.

**Request Body:**
```json
{
    "input_dir": "/path/to/input",
    "output_dir": "/path/to/output", 
    "depth": 0
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "./test_data",
    "output_dir": "./output",
    "depth": 0
  }'
```

### 5. Detect Language - POST `/detect-language`
Detects the language of provided text or file.

**Request Body (Text):**
```json
{
    "text": "Hello, this is a sample text in English."
}
```

**Request Body (File):**
```json
{
    "file_path": "/path/to/text/file.txt"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/detect-language \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Bonjour, ceci est un texte en français."
  }'
```

### 6. Upload and Process - POST `/upload-and-process`
Uploads a file and processes it immediately.

**Example:**
```bash
curl -X POST http://localhost:8000/upload-and-process \
  -F "file=@/path/to/document.pdf"
```

### 7. Health Check - GET `/health`
Simple health check endpoint.

**Example:**
```bash
curl http://localhost:8000/health
```

## Supported File Formats

- **PDF** (`.pdf`) - Portable Document Format
- **DJVU** (`.djvu`) - DjVu document format
- **EPUB** (`.epub`) - Electronic Publication format
- **FB2** (`.fb2`) - FictionBook format

## Interactive API Documentation

Once the server is running, you can access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Dependencies

The script automatically manages its dependencies using uv. The following packages are automatically installed:
- `httpx` - HTTP client library
- `uvicorn` - ASGI server
- `fastapi` - Web framework
- `pydantic` - Data validation
- `langdetect` - Language detection

## Requirements

- Python 3.11+
- Access to external tools: `pdftotext`, `ocrmypdf`, `tesseract-ocr`, `djvulibre-bin`, `calibre`
- The `pdf_ingest` package should be available in the Python path

## Error Handling

The server includes comprehensive error handling:
- Validates input directories exist
- Handles file processing errors gracefully
- Returns appropriate HTTP status codes
- Provides detailed error messages

## Development

To run in development mode with auto-reload:
```bash
./mcp_server.py --reload
```

## Security Notes

- The server binds to `0.0.0.0:8000` by default
- File uploads are temporarily stored and cleaned up automatically
- Input validation is performed on all endpoints
- Consider running behind a reverse proxy in production