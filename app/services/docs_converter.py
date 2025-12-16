from docx import Document
from weasyprint import HTML
from io import BytesIO
import markdown

def markdown_to_word(md_content: str) -> BytesIO:
    doc = Document()
    for line in md_content.split("\n"):
        doc.add_paragraph(line)
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream



def markdown_to_pdf(md_content: str) -> BytesIO:
    html_content = markdown.markdown(md_content)
    pdf_stream = BytesIO()
    HTML(string=html_content).write_pdf(pdf_stream)
    pdf_stream.seek(0)
    return pdf_stream
