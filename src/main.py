import os
import base64
from typing import List, Tuple
import fitz  # pymupdf
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")
openai.api_key = OPENAI_API_KEY

VISION_MODEL = "gpt-4o"  # or "gpt-4-vision-preview"

# Model to use
MODEL = "claude-sonnet-4-20250514"  # Load prompts
with open("src/extract_prompt.txt", "r", encoding="utf-8") as f:
    EXTRACT_PROMPT = f.read().strip()

with open("src/translate_prompt.txt", "r", encoding="utf-8") as f:
    TRANSLATE_PROMPT = f.read().strip()

def render_pages_to_images(pdf_path: str, page_numbers: list[int]) -> list[dict]:
    """Render specified PDF pages to PNG images and encode to base64."""
    doc = fitz.open(pdf_path)
    images = []
    for page_num in page_numbers:
        page = doc.load_page(page_num - 1)  # 0-based
        
        # Create a transformation matrix for higher resolution
        # Scale factor of 2.0 doubles the resolution (4x more pixels)
        # You can adjust this value: 1.5, 2.0, 3.0, etc.
        mat = fitz.Matrix(2.0, 2.0)
        
        # Get pixmap with higher resolution and better color space
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        base64_img = base64.b64encode(img_bytes).decode("utf-8")
        images.append({
            "type": "image",
            "data": base64_img,
            "media_type": "image/png"
        })
    doc.close()
    return images

def save_image_to_local_file(image: dict, name: str) -> str:
    """Save a base64-encoded image dict to the current directory as a PNG file and return the file path."""
    img_data = base64.b64decode(image["data"])
    file_path = f"temp/{name}.png"
    with open(file_path, "wb") as file:
        file.write(img_data)
    return file_path

def extract_text_from_images(images: list[dict]) -> str:
    """Send images to GPT-4 Vision to extract text."""
    # OpenAI expects images as base64-encoded strings in the content
    content = [
        {"type": "text", "text": EXTRACT_PROMPT}
    ]
    for img in images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{img['media_type']};base64,{img['data']}"
            }
        })

    response = openai.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts text from images. Do not hallucinate, only extract the text you see in the images. Do not speculate, do not answer any questions, do not make up any information."},
            {"role": "user", "content": content}
        ],
        max_tokens=4096,
        temperature=0.0
    )
    return response.choices[0].message.content

def translate_text(text: str) -> str:
    """Send extracted text to GPT-4 for translation to English."""
    response = openai.chat.completions.create(
        model="gpt-4o",  # or "gpt-4"
        messages=[{"role": "user", "content": TRANSLATE_PROMPT + "\n\n" + text}],
        max_tokens=2048,
        temperature=0.0
    )
    return response.choices[0].message.content

def parse_page_selection(page_selection: str, total_pages: int) -> list[int]:
    """Parse a page selection string like '1,2,5-7' into a list of page numbers (1-based)."""
    pages: list[int] = []
    if not page_selection.strip():
        return pages
    for part in page_selection.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            start, end = int(start), int(end)
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    # Remove duplicates and out-of-bounds
    pages = sorted(set(p for p in pages if 1 <= p <= total_pages))
    return pages

def normalize_output_path(output_path: str) -> str:
    """Ensure output path has .txt extension and is in extracted_pdfs folder."""
    # Create extracted_pdfs folder if it doesn't exist
    extracted_dir = os.path.join(os.getcwd(), "extracted_pdfs")
    os.makedirs(extracted_dir, exist_ok=True)
    
    # Get just the filename from the path
    filename = os.path.basename(output_path)
    
    # Ensure .txt extension
    if not filename.lower().endswith('.txt'):
        filename += '.txt'
    
    # Return the full path in extracted_pdfs folder
    return os.path.join(extracted_dir, filename)

def process_pdf(pdf_path: str, output_path: str, chunk_size: int = 3, page_numbers: list[int] | None = None) -> None:
    """Main processing function. If page_numbers is provided, only process those pages. Saves progress after each chunk."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    translated_texts: list[str] = []
    chunk_separator = "\n\n--- Chunk Separator ---\n\n"

    def save_progress():
        if translated_texts:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(chunk_separator.join(translated_texts))

    try:
        if page_numbers:
            # Process only specified pages, in chunks
            page_numbers = sorted(set(p for p in page_numbers if 1 <= p <= total_pages))
            print("page_numbers", page_numbers)
            for i in range(0, len(page_numbers), chunk_size):
                chunk = page_numbers[i:i+chunk_size]
                print(f"Processing pages {chunk[0]} to {chunk[-1]}...")
                images = render_pages_to_images(pdf_path, chunk)
                print("rendered images", len(images))
                extracted_text = extract_text_from_images(images)
                print("extracted text", extracted_text)
                translated = translate_text(extracted_text)
                print("translated text", translated)
                translated_texts.append(translated)
                save_progress()
        else:
            # Process all pages in chunks as before
            for start in range(0, total_pages, chunk_size):
                end = min(start + chunk_size, total_pages)
                chunk = list(range(start + 1, end + 1))
                print(f"Processing pages {chunk[0]} to {chunk[-1]}...")
                images = render_pages_to_images(pdf_path, chunk)
                print("rendered images", len(images))
                extracted_text = extract_text_from_images(images)
                print("extracted text", extracted_text)
                translated = translate_text(extracted_text)
                print("translated text", translated)
                translated_texts.append(translated)
                save_progress()
        print(f"Processing complete. Output saved to {output_path}")
    except Exception as e:
        print(f"Error occurred: {e}")
        save_progress()
        raise

if __name__ == "__main__":
    import sys
    def print_usage():
        print("Usage: python main.py <input_pdf> <output_txt> [pages]")
        print("  [pages] is optional, e.g. '1,2,5-7' (no spaces)")
    if len(sys.argv) not in (3, 4):
        print_usage()
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2]
    print("pdf_path", pdf_path)
    
    # Normalize output path to ensure .txt extension and extracted_pdfs folder
    output_path = normalize_output_path(output_path)
    print("normalized output_path", output_path)
    
    page_numbers = None
    if len(sys.argv) == 4:
        # Get total pages for bounds checking
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        page_numbers = parse_page_selection(sys.argv[3], total_pages)
        if not page_numbers:
            print("No valid pages selected.")
            sys.exit(1)
    process_pdf(pdf_path, output_path, page_numbers=page_numbers)
