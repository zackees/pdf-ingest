#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx",
#     "uvicorn",
#     "fastapi",
#     "pydantic",
#     "langdetect"
# ]
# ///

"""
MCP Server for PDF Ingest Tool

This server exposes the PDF ingest functionality through REST API endpoints,
allowing remote processing of PDF, DJVU, EPUB, and FB2 files with language detection.
"""

import json
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import uvicorn

# Import the pdf_ingest functionality
try:
    from src.pdf_ingest.scan_and_convert import (
        scan_and_convert,
        TRANSLATABLE_EXTENSIONS,
        _scan_for_untreated_files
    )
    from src.pdf_ingest.language_detection import (
        language_detect,
        detect_language_from_file
    )
    from src.pdf_ingest.types import TranslationItem, Result
except ImportError as e:
    print(f"Warning: Could not import pdf_ingest modules: {e}")
    print("Make sure to run this from the project root directory")
    # Define fallback constants for development
    TRANSLATABLE_EXTENSIONS = [".pdf", ".djvu", ".epub", ".fb2"]


# Pydantic models for API
class ProcessRequest(BaseModel):
    input_dir: str
    output_dir: str
    depth: int = 0


class ScanRequest(BaseModel):
    input_dir: str
    output_dir: str
    depth: int = 0


class LanguageDetectRequest(BaseModel):
    text: Optional[str] = None
    file_path: Optional[str] = None


class ProcessResponse(BaseModel):
    success: bool
    message: str
    input_files: List[str]
    output_files: List[str]
    untranslatable: List[str]
    errors: List[str]
    missing_json_files: List[str]


class ScanResponse(BaseModel):
    success: bool
    message: str
    files_to_process: List[Dict[str, Any]]


class LanguageDetectResponse(BaseModel):
    success: bool
    language_code: str
    is_reliable: bool
    error: Optional[str] = None


class StatusResponse(BaseModel):
    status: str
    supported_formats: List[str]
    version: str


# Initialize FastAPI app
app = FastAPI(
    title="PDF Ingest MCP Server",
    description="Model Context Protocol server for PDF document processing and language detection",
    version="1.0.0"
)


@app.get("/", response_model=StatusResponse)
async def root():
    """Root endpoint providing server status and capabilities."""
    return StatusResponse(
        status="running",
        supported_formats=list(TRANSLATABLE_EXTENSIONS),
        version="1.0.0"
    )


@app.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats."""
    return {
        "supported_formats": list(TRANSLATABLE_EXTENSIONS),
        "description": "File formats that can be processed by the PDF ingest tool"
    }


@app.post("/scan", response_model=ScanResponse)
async def scan_directory(request: ScanRequest):
    """
    Scan a directory for files that need processing.
    
    Returns list of files that would be processed without actually processing them.
    """
    try:
        input_dir = Path(request.input_dir)
        output_dir = Path(request.output_dir)
        
        if not input_dir.exists():
            raise HTTPException(status_code=400, detail=f"Input directory does not exist: {input_dir}")
        
        if not input_dir.is_dir():
            raise HTTPException(status_code=400, detail=f"Input path is not a directory: {input_dir}")
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Scan for files to process
        files_to_process = _scan_for_untreated_files(
            input_dir=input_dir,
            output_dir=output_dir,
            depth=request.depth
        )
        
        # Convert TranslationItem objects to dictionaries
        files_data = []
        for item in files_to_process:
            files_data.append({
                "input_file": str(item.input_file),
                "output_file": str(item.output_file),
                "json_file": str(item.json_file),
                "json_exists": item.json_exists,
                "language": item.language,
                "should_translate": item.should_translate
            })
        
        return ScanResponse(
            success=True,
            message=f"Found {len(files_to_process)} files to process",
            files_to_process=files_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning directory: {str(e)}")


@app.post("/process", response_model=ProcessResponse)
async def process_documents(request: ProcessRequest):
    """
    Process documents in the specified input directory.
    
    Converts PDF, DJVU, EPUB, and FB2 files to text with language detection.
    """
    try:
        input_dir = Path(request.input_dir)
        output_dir = Path(request.output_dir)
        
        if not input_dir.exists():
            raise HTTPException(status_code=400, detail=f"Input directory does not exist: {input_dir}")
        
        if not input_dir.is_dir():
            raise HTTPException(status_code=400, detail=f"Input path is not a directory: {input_dir}")
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Process the documents
        result = scan_and_convert(
            input_dir=input_dir,
            output_dir=output_dir,
            depth=request.depth
        )
        
        return ProcessResponse(
            success=True,
            message=f"Processed {len(result.output_files)} files successfully",
            input_files=[str(f) for f in result.input_files],
            output_files=[str(f) for f in result.output_files],
            untranslatable=[str(f) for f in result.untranstlatable],
            errors=[str(e) for e in result.errors],
            missing_json_files=[str(f) for f in result.missing_json_files]
        )
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing documents: {str(e)}")


@app.post("/detect-language", response_model=LanguageDetectResponse)
async def detect_language(request: LanguageDetectRequest):
    """
    Detect the language of provided text or file.
    
    Either provide text directly or specify a file path to analyze.
    """
    try:
        if request.text and request.file_path:
            raise HTTPException(status_code=400, detail="Provide either text or file_path, not both")
        
        if not request.text and not request.file_path:
            raise HTTPException(status_code=400, detail="Must provide either text or file_path")
        
        if request.text:
            # Detect language from provided text
            language_code, is_reliable = language_detect(request.text)
        else:
            # Detect language from file
            file_path = Path(request.file_path)
            if not file_path.exists():
                raise HTTPException(status_code=400, detail=f"File does not exist: {file_path}")
            
            language_code, is_reliable = detect_language_from_file(file_path)
        
        return LanguageDetectResponse(
            success=True,
            language_code=language_code,
            is_reliable=is_reliable
        )
        
    except Exception as e:
        return LanguageDetectResponse(
            success=False,
            language_code="unknown",
            is_reliable=False,
            error=str(e)
        )


@app.post("/upload-and-process")
async def upload_and_process(file: UploadFile = File(...)):
    """
    Upload a file and process it immediately.
    
    Returns the processed text content and language detection results.
    """
    try:
        # Check if file type is supported
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        file_suffix = Path(file.filename).suffix.lower()
        if file_suffix not in TRANSLATABLE_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_suffix}. Supported types: {list(TRANSLATABLE_EXTENSIONS)}"
            )
        
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=file_suffix, delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_output_dir:
            output_dir = Path(temp_output_dir)
            
            # Create TranslationItem for processing
            output_file = output_dir / f"{temp_file_path.stem}.txt"
            json_file = output_dir / f"{temp_file_path.stem}.json"
            
            # Create empty JSON file
            with open(json_file, "w") as f:
                json.dump({"language": ""}, f)
            
            item = TranslationItem(
                input_file=temp_file_path,
                output_file=output_file,
                json_file=json_file,
                json_exists=False
            )
            
            # Process the file using the appropriate parser
            from src.pdf_ingest.scan_and_convert import TRANSLATION_FUNCTIONS
            process_function = TRANSLATION_FUNCTIONS.get(file_suffix)
            if not process_function:
                raise HTTPException(status_code=500, detail=f"No processor found for {file_suffix}")
            
            err, success = process_function(item)
            
            if not success:
                error_msg = str(err) if err else "Processing failed"
                raise HTTPException(status_code=500, detail=f"File processing failed: {error_msg}")
            
            # Read the processed text
            if output_file.exists():
                with open(output_file, "r", encoding="utf-8") as f:
                    processed_text = f.read()
            else:
                processed_text = ""
            
            # Read the JSON metadata
            metadata = {}
            if json_file.exists():
                with open(json_file, "r") as f:
                    metadata = json.load(f)
            
            # Clean up temporary input file
            temp_file_path.unlink()
            
            return {
                "success": True,
                "filename": file.filename,
                "file_type": file_suffix,
                "processed_text": processed_text,
                "metadata": metadata,
                "text_length": len(processed_text)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing uploaded file: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "pdf-ingest-mcp-server"}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PDF Ingest MCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    print(f"Starting PDF Ingest MCP Server on {args.host}:{args.port}")
    print(f"Supported formats: {list(TRANSLATABLE_EXTENSIONS)}")
    
    uvicorn.run(
        "mcp_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )