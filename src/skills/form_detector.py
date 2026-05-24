import re
from typing import Any, Type
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from src.skills.base import AbstractSkill

class FormDetectorInput(BaseModel):
    document_content: str = Field(description="The raw text content of the document to analyze")

class ExtractedForm(BaseModel):
    is_form: bool
    questions: list[str]

QUESTION_PATTERNS = [
    r'\d+[\.\)]\s+.+\?',                    # "1. What is...?"
    r'(?:Q|Question)\s*\d*[:\.\)]\s*.+',     # "Q1: ..."
    r'^[A-Z][\.\)]\s+.+\?',                 # "A. What..."
    r'_{3,}',                                # "___________" (fill-in blanks)
    r'\[\s*\]',                              # "[ ]" checkboxes
    r'(?:Yes|No)\s*/\s*(?:Yes|No)',          # "Yes / No"
    r'(?:Please|Kindly)\s+(?:describe|explain|list|provide)',
]

class FormDetectorSkill(AbstractSkill):
    name: str = "form_detector"
    description: str = "Detects if a document is a form/questionnaire and extracts questions sequentially."
    args_schema: Type[BaseModel] = FormDetectorInput

    def __init__(self, llm=None):
        super().__init__()
        # Use provided LLM or default
        if llm:
            self._llm = llm
        else:
            self._llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")
            
    def _execute(self, document_content: str, **kwargs: Any) -> dict[str, Any]:
        """
        Two-pass detection:
        1. Heuristic regex
        2. LLM fallback if it's ambiguous
        """
        lines = document_content.split("\n")
        matched_questions = []
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            for pattern in QUESTION_PATTERNS:
                if re.search(pattern, line_str, flags=re.IGNORECASE):
                    matched_questions.append(line_str)
                    break # Skip other patterns if one matches
                    
        match_count = len(matched_questions)
        
        if match_count >= 3:
            # High confidence form
            return {
                "is_form": True,
                "confidence": "high",
                "questions": matched_questions
            }
        elif match_count == 0:
            # Not a form
            return {
                "is_form": False,
                "confidence": "high",
                "questions": []
            }
        else:
            # Ambiguous (1-2 matches). Use LLM to confirm.
            prompt = f"""
            Analyze the following document snippet. Is it a form or a questionnaire?
            If so, extract the questions or fields that need to be filled.
            
            Return output that strictly matches the concept of whether it's a form, and if so, what questions are present.
            
            Document Snippet:
            {document_content[:15000]} # Look at the first 15k chars
            """
            
            structured_llm = self._llm.with_structured_output(ExtractedForm)
            result = structured_llm.invoke(prompt)
            
            # Pydantic structured output mapping
            return {
                "is_form": result.is_form,
                "confidence": "llm_fallback",
                "questions": result.questions if result.is_form else []
            }
