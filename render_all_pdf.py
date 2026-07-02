import os
import pypdfium2 as pdfium

def render_pages():
    os.makedirs("diagrams/pdf_pages", exist_ok=True)
    doc = pdfium.PdfDocument("nuclear_manual.pdf")
    for idx, page in enumerate(doc):
        # Render at 3x scale for high resolution
        bitmap = page.render(scale=3)
        pil_img = bitmap.to_pil()
        filename = f"diagrams/pdf_pages/page_{idx + 1}.png"
        pil_img.save(filename)
        print(f"Rendered {filename}")

if __name__ == "__main__":
    render_pages()
