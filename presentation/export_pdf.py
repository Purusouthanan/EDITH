import os
import time
import subprocess
import pymupdf

WORKSPACE = r"c:\Users\PURUSOUTHANAN\OneDrive\Desktop\EDITH"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

html_path = os.path.join(WORKSPACE, "presentation.html")
pdf_path = os.path.join(WORKSPACE, "EDITH_Hackathon_Pitch_Deck.pdf")
temp_pdf_path = os.path.join(WORKSPACE, "EDITH_Hackathon_Pitch_Deck_new.pdf")
assets_dir = os.path.join(WORKSPACE, "EDITH_Presentation_Assets")
os.makedirs(assets_dir, exist_ok=True)

# Format file URL
file_url = "file:///" + html_path.replace("\\", "/")

if os.path.exists(temp_pdf_path):
    try:
        os.remove(temp_pdf_path)
    except Exception:
        pass

cmd = [
    CHROME_PATH,
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={temp_pdf_path}",
    file_url
]

print("Executing Chrome headless...")
res = subprocess.run(cmd, capture_output=True, text=True)
print("Return code:", res.returncode)

if os.path.exists(temp_pdf_path):
    print("Temporary PDF created, replacing final PDF...")
    time.sleep(1) # Wait for Chrome to fully release handle
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception as e:
            print("Could not remove old pdf immediately:", e)
            time.sleep(2)
            try:
                os.remove(pdf_path)
            except Exception as e2:
                print("Second remove attempt:", e2)

    try:
        os.replace(temp_pdf_path, pdf_path)
    except Exception as e:
        print("Replace failed, copying instead:", e)
        import shutil
        shutil.copy2(temp_pdf_path, pdf_path)
    
    size_kb = round(os.path.getsize(pdf_path) / 1024, 1)
    print(f"Success! PDF generated: {pdf_path} ({size_kb} KB)")
    
    doc = pymupdf.open(pdf_path)
    print(f"Total pages: {len(doc)}")
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        img_name = f"slide_{i+1:02d}.png"
        img_path = os.path.join(assets_dir, img_name)
        pix.save(img_path)
        print(f"Saved: {img_name}")
    doc.close()
else:
    print("Error: temp PDF was not created!")
    if res.stderr:
        print("Stderr:", res.stderr)
