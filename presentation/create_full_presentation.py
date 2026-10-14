# -*- coding: utf-8 -*-
"""
EDITH Hackathon Pitch Deck Generator
Creates:
1. presentation.html (Widescreen 1920x1080 with high-density design system)
2. EDITH_Hackathon_Pitch_Deck.pdf (Vector PDF via Chrome Headless)
3. EDITH_Hackathon_Pitch_Deck.pptx (Editable PPTX via python-pptx)
4. EDITH_Presentation_Assets/slide_01.png ... slide_16.png (High-res rendered slides via PyMuPDF)
"""

import os
import subprocess
import pymupdf
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

WORKSPACE = r"c:\Users\PURUSOUTHANAN\OneDrive\Desktop\EDITH"
ASSETS_DIR = os.path.join(WORKSPACE, "EDITH_Presentation_Assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

HTML_PATH = os.path.join(WORKSPACE, "presentation.html")
PDF_PATH = os.path.join(WORKSPACE, "EDITH_Hackathon_Pitch_Deck.pdf")
PPTX_PATH = os.path.join(WORKSPACE, "EDITH_Hackathon_Pitch_Deck.pptx")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

print(f"Browser path: {CHROME_PATH}")
