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
# GEMINI (Google AI Studio)
# ============================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

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
            "puff print", "hd print", "print artwork", "solid 2 mm hd print",
            "artwork detail",
        ],
        "code_prefix": "ART",
        "folder_name": "Prints",
        "color_hex": "#3B82F6",
        "color_name": "Blue",
    },
    "embroidery": {
        "keywords": [
            "embroidery", "embroidered", "3d puff", "flat embroidery",
            "chain stitch", "satin stitch", "cross stitch", "applique",
            "puffed embroidery", "tuft embroidery", "cotton poly thread",
            "emb patch", "embroidery artwork",
        ],
        "code_prefix": "EMB",
        "folder_name": "Embroidery",
        "color_hex": "#10B981",
        "color_name": "Green",
    },
    "woven_label": {
        "keywords": [
            "woven label", "main label", "size label", "care label",
            "brand label", "neck label", "woven tag", "damask label",
            "satin label", "taffeta label", "woven loop label",
            "washcare label", "flag label", "branding label",
            "party tag",
        ],
        "code_prefix": "WL",
        "folder_name": "Woven_Labels",
        "color_hex": "#F59E0B",
        "color_name": "Orange",
    },
    "heat_transfer": {
        "keywords": [
            "heat transfer", "silicone transfer", "reflective transfer",
            "vinyl transfer", "htv", "heat seal",
            "heat transfer label", "heat transfer at inner",
            "ht tape", "silicon print",
        ],
        "code_prefix": "HT",
        "folder_name": "Heat_Transfers",
        "color_hex": "#8B5CF6",
        "color_name": "Purple",
    },
    "patch_badge": {
        "keywords": [
            "patch", "badge", "rubber patch", "tpu patch", "leather patch",
            "pvc patch", "metal badge", "woven patch", "chenille patch",
            "silicone badge", "silicon badge", "rubber badge",
            "branding badge", "moon patch",
        ],
        "code_prefix": "SB",
        "folder_name": "Patches_Badges",
        "color_hex": "#EF4444",
        "color_name": "Red",
    },
    "packaging": {
        "keywords": [
            "hangtag", "hang tag", "polybag", "sticker", "barcode",
            "packaging", "price tag", "care tag", "tissue paper",
            "packaging artwork", "carton box", "packing tape",
            "inserter", "crocodile clip", "poly cover",
        ],
        "code_prefix": "PKG",
        "folder_name": "Packaging",
        "color_hex": "#6366F1",
        "color_name": "Indigo",
    },
}

# ============================================
# CATEGORY COLOR CODING
# ============================================
CATEGORY_COLORS = {
    cat: {"hex": info["color_hex"], "name": info["color_name"]}
    for cat, info in ARTWORK_CATEGORIES.items()
}

# ============================================
# TEXT EXTRACTION PATTERNS
# ============================================
# Regex patterns for extracting metadata from techpack text

PANTONE_PATTERN = r'(\d{2}-\d{4})\s*TCX\s*\n?\s*([A-Z][A-Z\s]*?)(?:\n|$)'
DIMENSION_PATTERNS = [
    r'(\d+(?:\.\d+)?)\s*(?:CM|cm)\s*(?:X|x)\s*(\d+(?:\.\d+)?)\s*(?:CM|cm)',
    r'(\d+(?:\.\d+)?)\s*(?:CM|cm)\s*(?:WIDTH|width|HT|ht)',
    r'WIDTH\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:CM|cm)',
    r'HEIGHT\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:CM|cm)',
    r'(\d+(?:\.\d+)?)\s*(?:INCHES|inches)\s*(?:WIDTH|width)',
    r'(\d+(?:\.\d+)?)\s*(?:CM|cm)\s*(?:LENGTH|length)',
]

PLACEMENT_KEYWORDS = [
    "left chest", "right chest", "center back", "center front",
    "left sleeve", "right sleeve", "inner neck", "inner yoke",
    "outer cb", "at hem", "side seam", "back neck",
    "front panel", "back panel", "below collar", "sleeve cuff",
    "at shoulder", "waistband", "pocket", "placket",
]

TECHNIQUE_KEYWORDS = [
    "screen print", "flock print", "hd print", "puff print",
    "foil print", "sublimation", "digital print", "dtf",
    "discharge print", "plastisol", "pigment print",
    "flat embroidery", "puffed embroidery", "tuft embroidery",
    "3d puff embroidery", "satin stitch", "chain stitch",
    "heat transfer", "silicon print", "silicon badge",
    "rubber badge", "woven label", "damask", "satin label",
]

HEADER_PATTERNS = {
    "style_no": [
        r'STYLE\s*(?:NO|NUMBER|#)?\s*[:\-]?\s*([A-Z0-9\-]+)',
        r'STYLE\s*:\s*([A-Z0-9\-]+)',
    ],
    "buyer": [
        r'BUYER\s*[:\-]?\s*([A-Za-z\s]+?)(?:\n|$)',
    ],
    "season": [
        r'SEASON\s*[:\-]?\s*([A-Za-z0-9\s\-\/]+?)(?:\n|$)',
        r'(AUTUMN\s+WINTER\s+\d{4}[\-\d]*)',
        r'(SPRING\s+(?:SUMMER\s+)?\d{2,4})',
        r'(FALL\s+WINTER\s+\d{4})',
        r'(SS\d{2}|FW\d{2}|AW\d{2})',
    ],
    "garment_type": [
        r'STYLE\s+DESCRIPTION\s*\n\s*\n?\s*(.+?)(?:\n|$)',
        r'PRODUCT\s+TYPE.*?\n.*?([A-Z][A-Z\s\/]+(?:TEE|POLO|HOODIE|JACKET|SHORTS|PANTS|SHIRT))',
    ],
    "designer": [
        r'DESIGNER\s*[:\-]?\s*([A-Za-z\/\s]+?)(?:\n|$)',
    ],
    "collection": [
        r'COLLECTION\s*[:\-]?\s*([A-Za-z\s]+?)(?:\n|$)',
    ],
    "fabric": [
        r'(\d+%\s*(?:COTTON|POLYESTER|SPANDEX|ELASTANE|NYLON|VISCOSE)[\w\s%\/,]+)',
    ],
}

# ============================================
# VERSION STATES
# ============================================
VERSION_STATES = ["V1", "V2", "V3", "FINAL", "APPROVED"]
DEFAULT_VERSION = "V1"

# ============================================
# APPROVAL STATUSES
# ============================================
APPROVAL_STATUSES = ["Pending", "Approved", "Rejected", "Revision"]

# ============================================
# NAMING CONVENTION
# ============================================
# Format: BRAND_STYLE_ARTWORKTYPE_VERSION
# Example: NIKE_SS25-001_PRINT_V1
NAMING_SEPARATOR = "_"

# ============================================
# GOOGLE SHEETS STRUCTURE
# ============================================
SHEETS_CONFIG = {
    "artwork_master": {
        "name": "Artwork_Master",
        "headers": [
            "Artwork ID", "Style No", "Buyer", "Season", "Garment Type",
            "Artwork Type", "Artwork Name", "Placement", "Color",
            "Size", "File Name", "PNG Link", "AI Link", "PDF Link",
            "DST Link", "Vendor", "Status", "Version",
            "Techpack Page", "Notes",
        ],
    },
    "artwork_types": {
        "name": "Artwork_Types",
        "headers": ["Artwork Type"],
        "values": [
            "Print", "Embroidery", "Woven Label", "Silicone Badge",
            "Heat Transfer", "Patch", "Rubber Badge", "Packaging",
        ],
    },
    "vendors": {
        "name": "Vendors",
        "headers": ["Vendor Name", "Type", "Contact"],
    },
    "upload_log": {
        "name": "Upload_Log",
        "headers": ["Upload Date", "Style No", "Uploaded By", "Status"],
    },
    "approval_tracker": {
        "name": "Approval_Tracker",
        "headers": ["Style", "Artwork", "Buyer Approval", "Vendor Approval"],
    },
}

# ============================================
# IMAGE EXTRACTION SETTINGS
# ============================================
MIN_IMAGE_WIDTH = 50   # pixels — filter out tiny icons
MIN_IMAGE_HEIGHT = 50

# ============================================
# DRIVE FOLDER STRUCTURE
# ============================================
DRIVE_FOLDERS = [
    "Prints", "Embroidery", "Woven_Labels", "Heat_Transfers",
    "Patches_Badges", "Packaging", "Mockups", "Unclassified",
]

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
