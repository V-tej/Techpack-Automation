"""
Configuration Module
====================
Loads settings from .env and config files.
Provides centralized access to all configuration values.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# ============================================
# PATHS
# ============================================
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
CREDENTIALS_DIR = BASE_DIR / "credentials"
OUTPUT_DIR = Path(os.getenv("DEFAULT_OUTPUT_DIR", BASE_DIR / "output"))
LOGS_DIR = BASE_DIR / "logs"
SAMPLES_DIR = BASE_DIR / "samples"

# ============================================
# GOOGLE CLOUD
# ============================================
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    str(CREDENTIALS_DIR / "service_account.json")
)
GOOGLE_DRIVE_ROOT_FOLDER_ID = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")

# Google API Scopes
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/cloud-vision",
]

# ============================================
# OPENAI
# ============================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ============================================
# PROCESSING SETTINGS
# ============================================
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================
# ARTWORK CATEGORIES
# ============================================
ARTWORK_CATEGORIES = {
    "print": {
        "keywords": [
            "screen print", "dtf", "sublimation", "digital print",
            "discharge print", "pigment print", "heat transfer print",
            "plastisol", "water-based print", "foil print", "flock print",
            "puff print", "hd print", "print artwork", "print col",
            "all over print", "placement print", "~aop",
        ],
        "code_prefix": "ART",
        "folder_name": "Prints"
    },
    "embroidery": {
        "keywords": [
            "embroidery", "embroidered", "3d puff", "flat embroidery",
            "chain stitch", "satin stitch", "cross stitch", "applique",
            "puffed embroidery", "tuft embroidery",
            "embroidery in cotton", "embroidery in poly",
        ],
        "code_prefix": "EMB",
        "folder_name": "Embroidery"
    },
    "woven_label": {
        "keywords": [
            "woven label", "main label", "size label", "care label",
            "brand label", "neck label", "woven tag", "damask label",
            "satin label", "taffeta label", "washcare label",
            "wash care label", "branding label", "flag label",
            "loop label", "content label", "printed neck tape",
            "tracibility label", "party tag", "wash care",
        ],
        "code_prefix": "WL",
        "folder_name": "Woven_Labels"
    },
    "heat_transfer": {
        "keywords": [
            "heat transfer", "silicone transfer", "reflective transfer",
            "vinyl transfer", "~htv", "heat seal",
            "heat transfer label", "silicon label",
            "ht tape", "ht proportional",
        ],
        "code_prefix": "HT",
        "folder_name": "Heat_Transfers"
    },
    "patch_badge": {
        "keywords": [
            "rubber patch", "tpu patch", "leather patch",
            "pvc patch", "metal badge", "woven patch", "chenille patch",
            "silicone badge", "silicon branding", "silicon badge",
            "moon patch", "branding badge",
        ],
        "code_prefix": "SB",
        "folder_name": "Patches_Badges"
    },
    "packaging": {
        "keywords": [
            "hangtag", "hang tag", "polybag", "sticker", "barcode",
            "packaging artwork", "price tag", "tissue paper",
            "poly cover", "packing tape", "carton box",
            "inserter", "crocodile clip", "~bopp",
        ],
        "code_prefix": "PKG",
        "folder_name": "Packaging"
    },
    "bill_of_materials": {
        "keywords": [
            "bill of materials", "~bom",
        ],
        "code_prefix": "BOM",
        "folder_name": "BOM"
    },
    "design_sheet": {
        "keywords": [
            "design sheet", "working sketch", "style description",
        ],
        "code_prefix": "DS",
        "folder_name": "Design_Sheets"
    },
    "spec_sheet": {
        "keywords": [
            "spec sheet", "spec detail", "reference sheet",
            "measurement sheet",
        ],
        "code_prefix": "SP",
        "folder_name": "Spec_Sheets"
    },
}

# ============================================
# NAMING CONVENTION
# ============================================
# Format: BRAND_STYLE_ARTWORKTYPE_VERSION
# Example: NIKE_SS25-001_PRINT_V1
NAMING_SEPARATOR = "_"
DEFAULT_VERSION = "V1"

# ============================================
# LOGGING SETUP
# ============================================
logger.add(
    LOGS_DIR / "techpack_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level=LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {module}:{function}:{line} | {message}"
)


def ensure_directories():
    """Create all required directories if they don't exist."""
    for directory in [OUTPUT_DIR, LOGS_DIR, SAMPLES_DIR, CREDENTIALS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# Create directories on import
ensure_directories()
