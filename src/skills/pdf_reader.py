import fitz
import pdfplumber
from typing import Any, Type
from pydantic import BaseModel, Field
from src.skills.base import AbstractSkill, SkillInput

class PDFReaderInput(SkillInput):
    extract_tables: bool = Field(default=False, description="Set True to extract tables")

class PDFReaderSkill(AbstractSkill):
    name: str = "pdf_reader"
    description: str = "Extracts text and optionally tables from a PDF file."
    args_schema: Type[BaseModel] = PDFReaderInput

    def _execute(self, file_path: str, extract_tables: bool = False, **kwargs: Any) -> dict[str, Any]:
        """
        Extracts content from a PDF.
        Uses PyMuPDF for fast text extraction. Option to use pdfplumber for table extraction.
        """
        # PyMuPDF fast path
        # Use fitz.Document for robust type hinting in PyMuPDF
        doc = fitz.open(file_path)
        pages = [{"page": i+1, "text": page.get_text()} for i, page in enumerate(doc)]
        
        tables = []
        if extract_tables:
            # pdfplumber precision path for tables
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    for table in page.extract_tables():
                        tables.append({"page": i+1, "data": table})
        
        return {"pages": pages, "tables": tables, "total_pages": len(pages)}
