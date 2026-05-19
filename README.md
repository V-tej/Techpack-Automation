# Techpack Artwork Automation System

> 🤖 Automated techpack PDF processing for garment production

## Quick Start

```bash
# 1. Clone and setup
cd techpack-automation
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt

# 2. Configure
copy .env.example .env
# Edit .env with your API keys

# 3. Place service account JSON
# Save your Google service account key to: credentials/service_account.json

# 4. Run
python main.py analyze "path/to/techpack.pdf"           # Preview
python main.py process "path/to/techpack.pdf" -b NIKE -s SS25-001   # Process
python main.py process "path/to/techpack.pdf" -b NIKE -s SS25-001 --drive --sheets  # Full pipeline
```

## Project Structure

```
techpack-automation/
├── main.py                    # CLI entry point
├── requirements.txt           # Python dependencies
├── .env.example               # Environment config template
├── .gitignore
│
├── src/                       # Source code
│   ├── __init__.py
│   ├── config.py              # Configuration & constants
│   ├── pdf_processor.py       # Phase 1: PDF parsing & splitting
│   ├── drive_manager.py       # Phase 2: Google Drive integration
│   ├── ai_detector.py         # Phase 3: AI/OCR detection
│   ├── naming_engine.py       # Phase 4: Naming & cataloging
│   └── pipeline.py            # Main orchestration pipeline
│
├── tests/                     # Unit tests
│   └── test_processor.py
│
├── config/                    # Config files (future)
├── credentials/               # Google service account (gitignored)
├── samples/                   # Sample techpack PDFs for testing
├── output/                    # Processed output files
└── logs/                      # Application logs
```

## Commands

| Command | Description |
|---------|-------------|
| `python main.py analyze <pdf>` | Preview artwork detection without processing |
| `python main.py process <pdf> -b BRAND -s STYLE` | Full local processing |
| `python main.py process <pdf> --drive` | Process + upload to Google Drive |
| `python main.py process <pdf> --ocr --ai` | Enable OCR & AI detection |
| `python main.py process <pdf> --sheets` | Process + update Google Sheets |

## Phases

1. **PDF Processing** → Parse, detect keywords, split pages
2. **Google Drive** → Auto-create folders, upload files
3. **AI/OCR** → Google Vision + GPT-4 Vision for scanned PDFs
4. **Naming** → BRAND_STYLE_TYPE_VERSION convention + Sheets DB
5. **Testing** → Multi-format validation + error handling
