"""
Techpack Artwork Automation System
===================================
A Python-based tool that automates garment techpack processing:
- Parses techpack PDFs and extracts structured metadata
- Detects & classifies artwork types (prints, labels, badges, embroidery, heat transfers, packaging)
- Extracts Pantone colors, dimensions, placements, and techniques
- Splits into organized folders with standardized naming
- Uploads to Google Drive with shareable links
- Maintains 5-sheet artwork database in Google Sheets
- Tracks approvals, vendors, and versions
- Provides webhook endpoints for Make/Zapier automation
"""

__version__ = "2.0.0"
__author__ = "Varuntej"
