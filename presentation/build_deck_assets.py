import os
import sys
import subprocess
import pymupdf
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

print("Configuring directories...")
WORKSPACE = r"c:\Users\PURUSOUTHANAN\OneDrive\Desktop\EDITH"
ASSETS_DIR = os.path.join(WORKSPACE, "EDITH_Presentation_Assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

print(f"Using browser at: {CHROME_PATH}")
