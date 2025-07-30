# PDF Ingest

[![Lint](https://github.com/zackees/pdf-ingest/actions/workflows/lint.yml/badge.svg)](https://github.com/zackees/pdf-ingest/actions/workflows/lint.yml)
[![Build Docker Image](https://github.com/zackees/pdf-ingest/actions/workflows/build_docker_image.yml/badge.svg)](https://github.com/zackees/pdf-ingest/actions/workflows/build_docker_image.yml)

# Language(X) -> English translations

[fairseq](https://github.com/facebookresearch/fairseq)

https://github.com/facebookresearch/fairseq/blob/main/examples/translation/README.md



# Use

```
pdf-ingest X:\yourfiles
```

## Language Detection and Processing Status

The tool automatically detects the language of processed documents and tracks processing status through JSON metadata files.

### JSON Metadata States

Each processed file has a corresponding `.json` metadata file that tracks processing status:

#### **Unprocessed Files**
```json
{"language": ""}
```
- File was found during scanning but hasn't been processed yet
- Processing is still pending

#### **Successfully Processed Files**
```json
{
  "language": "en",
  "language_detection_reliable": true,
  "should_translate": true
}
```
- File was successfully converted to text
- Language was detected (e.g., "en" for English)
- `language_detection_reliable` indicates successful completion
- `should_translate` indicates if file should be processed further

#### **Output Files**
Successfully processed files generate:
- **Text file**: `document-EN.txt` (with language code suffix)
- **JSON metadata**: `document.json` (with processing status)

### Processing Workflow

1. **Scanning**: Tool finds PDF/DJVU/EPUB/FB2 files and creates empty JSON metadata
2. **Text Extraction**: Converts document to text using appropriate parser
3. **Language Detection**: Analyzes text to determine language
4. **File Naming**: Adds language code to output filename (e.g., `-EN.txt`)
5. **Metadata Update**: Updates JSON with language info and completion status

### Troubleshooting

If you see many files with empty `"language": ""` fields:
- Files were found but processing failed or was interrupted
- Check for missing dependencies (pdftotext, tesseract, etc.)
- Check for file access permissions
- Review error logs for specific parsing failures


# Misc

  * How to use GPU in paddleocr
  * https://github.com/PaddlePaddle/PaddleOCR/issues/10429


# Extensions TODO:
  [ ] fb2
  [ ] epub


# Instructions from Mike Adams

MA: I was wondering though if the filename could have a pre-extension based on language like *-EN.txt
MA: Or *-RUS.txt, etc.
MA: Like, if it's easy for your program to realize what language it is

ME: that's trivial
ME: but how is your AI going to make sense out of different languages?

MA: We are just gonna archive non-English for now, and only process English

