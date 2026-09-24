from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json"}


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix in TEXT_EXTENSIONS:
        text = data.decode("utf-8", errors="replace")
    elif suffix == ".pdf":
        reader = PdfReader(BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        document = Document(BytesIO(data))
        text = "\n".join(p.text for p in document.paragraphs)
    else:
        raise ValueError("仅支持 txt、md、csv、json、pdf、docx 文件")

    text = text.strip()
    if not text:
        raise ValueError("文件中没有可提取的文本")
    return text
