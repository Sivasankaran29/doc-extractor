"""
Industrial PDF text extractor — extracts text page-by-page using PyMuPDF.
Handles text-heavy docs (SOPs, reports) as well as diagram-heavy pages
(electrical diagrams, spare part sheets) by also extracting any embedded
text annotations and block metadata.
"""
import fitz  # PyMuPDF
from typing import List, Dict


def extract_pages(pdf_bytes: bytes) -> List[Dict]:
    """
    Extract structured text from each page of an industrial PDF.

    Returns:
        [
          {
            "page_number": 1,
            "text": "...",
            "char_count": 123,
            "has_images": True,
            "block_count": 5,
          },
          ...
        ]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()

        # Count image blocks — useful signal for diagram/schematic pages
        image_list = page.get_images(full=False)
        blocks = page.get_text("blocks")

        pages.append(
            {
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text),
                "has_images": len(image_list) > 0,
                "block_count": len(blocks),
            }
        )

    doc.close()
    return pages
