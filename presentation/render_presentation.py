# -*- coding: utf-8 -*-
"""
Full Presentation HTML Generator for EDITH
Generates presentation.html
"""

import os
import subprocess
import pymupdf

WORKSPACE = r"c:\Users\PURUSOUTHANAN\OneDrive\Desktop\EDITH"
HTML_PATH = os.path.join(WORKSPACE, "presentation.html")
PDF_PATH = os.path.join(WORKSPACE, "EDITH_Hackathon_Pitch_Deck.pdf")
ASSETS_DIR = os.path.join(WORKSPACE, "EDITH_Presentation_Assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>EDITH — Hackathon Pitch Deck</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

@page {
    size: 1920px 1080px;
    margin: 0;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    background-color: #050B14;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #F4F8FF;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}

.slide {
    width: 1920px;
    height: 1080px;
    max-width: 1920px;
    max-height: 1080px;
    position: relative;
    overflow: hidden;
    background: #091020;
    padding: 44px 64px 34px 64px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    page-break-after: always;
    break-after: page;
}

.slide::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: 
        radial-gradient(circle at 85% 15%, rgba(43, 220, 224, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 15% 85%, rgba(76, 145, 255, 0.06) 0%, transparent 45%),
        linear-gradient(to right, rgba(255, 255, 255, 0.015) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(255, 255, 255, 0.015) 1px, transparent 1px);
    background-size: 100% 100%, 100% 100%, 64px 64px, 64px 64px;
    pointer-events: none;
    z-index: 0;
}

.slide-content-wrap {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    height: 100%;
    justify-content: space-between;
}

/* Header */
.slide-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 20px;
    border-bottom: 1px solid rgba(76, 145, 255, 0.2);
    padding-bottom: 12px;
}

.slide-header-left {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.section-eyebrow {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #2BDCE0;
    display: flex;
    align-items: center;
    gap: 8px;
}

.section-eyebrow::before {
    content: '';
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #2BDCE0;
    border-radius: 50%;
    box-shadow: 0 0 8px #2BDCE0;
}

.slide-title {
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #FFFFFF;
    line-height: 1.15;
}

.slide-subtitle {
    font-size: 15px;
    font-weight: 400;
    color: #A3B4CC;
    line-height: 1.35;
}

.slide-badge {
    background: rgba(17, 29, 51, 0.85);
    border: 1px solid rgba(76, 145, 255, 0.35);
    padding: 6px 14px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 600;
    color: #4C91FF;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Body */
.slide-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 16px;
    min-height: 0;
}

/* Footer */
.slide-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 10px;
    font-size: 12px;
    color: #72849E;
    font-family: 'JetBrains Mono', monospace;
}

.slide-footer-left {
    display: flex;
    align-items: center;
    gap: 12px;
}

.slide-footer-center {
    font-weight: 500;
    color: #A3B4CC;
}

.slide-footer-right {
    color: #2BDCE0;
    font-weight: 600;
}

/* Cards & Layout */
.card {
    background: linear-gradient(135deg, rgba(17, 29, 51, 0.88) 0%, rgba(21, 34, 56, 0.72) 100%);
    border: 1px solid rgba(76, 145, 255, 0.18);
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.card-highlight {
    background: linear-gradient(135deg, rgba(23, 42, 74, 0.92) 0%, rgba(17, 29, 51, 0.85) 100%);
    border: 1px solid rgba(43, 220, 224, 0.4);
    box-shadow: 0 8px 30px rgba(43, 220, 224, 0.12);
}

.pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 9px;
    border-radius: 14px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.pill-cyan { background: rgba(43, 220, 224, 0.15); color: #2BDCE0; border: 1px solid rgba(43, 220, 224, 0.3); }
.pill-blue { background: rgba(76, 145, 255, 0.15); color: #4C91FF; border: 1px solid rgba(76, 145, 255, 0.3); }
.pill-green { background: rgba(82, 220, 164, 0.15); color: #52DCA4; border: 1px solid rgba(82, 220, 164, 0.3); }
.pill-orange { background: rgba(255, 164, 76, 0.15); color: #FFA44C; border: 1px solid rgba(255, 164, 76, 0.3); }
.pill-red { background: rgba(255, 104, 120, 0.15); color: #FF6878; border: 1px solid rgba(255, 104, 120, 0.3); }

/* Table */
.edith-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    text-align: left;
}

.edith-table th {
    background: rgba(17, 29, 51, 0.95);
    color: #2BDCE0;
    font-weight: 700;
    padding: 9px 13px;
    border-bottom: 2px solid rgba(76, 145, 255, 0.35);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.5px;
}

.edith-table td {
    padding: 9px 13px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    color: #D3DFEE;
    line-height: 1.35;
}

.edith-table tr:nth-child(even) td {
    background: rgba(17, 29, 51, 0.35);
}

/* Grids */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }
.grid-4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 18px; }
.grid-5 { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.grid-6 { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }

</style>
</head>
<body>
"""

print("Generating slides content...")
