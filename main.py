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
with open("extract_prompt.txt", "r", encoding="utf-8") as f:
    EXTRACT_PROMPT = f.read().strip()

with open("translate_prompt.txt", "r", encoding="utf-8") as f:
    TRANSLATE_PROMPT = f.read().strip()

def render_pages_to_images(pdf_path: str, page_numbers: List[int]) -> List[dict]:
    """Render specified PDF pages to PNG images and encode to base64."""
    doc = fitz.open(pdf_path)
    images = []
    for page_num in page_numbers:
        page = doc.load_page(page_num - 1)  # 0-based
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        base64_img = base64.b64encode(img_bytes).decode("utf-8")
        images.append({
            "type": "image",
            "data": base64_img,
            "media_type": "image/png"
        })
    doc.close()
    return images

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

def process_pdf(pdf_path: str, output_path: str, chunk_size: int = 3) -> None:
    """Main processing function."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    translated_texts = []

    for start in range(0, total_pages, chunk_size):
        end = min(start + chunk_size, total_pages)
        page_numbers = list(range(start + 1, end + 1))
        print(f"Processing pages {page_numbers[0]} to {page_numbers[-1]}...")

        images = render_pages_to_images(pdf_path, page_numbers)
        print("rendered images")
        extracted_text = extract_text_from_images(images)
        print("extracted text", extracted_text)
        translated = translate_text(extracted_text)
        print("translated text", translated)
        translated_texts.append(translated)
        break

    # Save to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n--- Chunk Separator ---\n\n".join(translated_texts))

    print(f"Processing complete. Output saved to {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python main.py <input_pdf> <output_txt>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2]
    process_pdf(pdf_path, output_path)
