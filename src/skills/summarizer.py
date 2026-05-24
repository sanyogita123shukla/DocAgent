from typing import Any, Type
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from src.skills.base import AbstractSkill, SkillInput

class SummarizationInput(BaseModel):
    document_content: str = Field(description="The parsed text content of the document to summarize")
    document_type: str = Field(description="The type or MIME type of the document (e.g. pdf, excel)")

class SummarizationSkill(AbstractSkill):
    name: str = "summarizer"
    description: str = "Generates a detailed summary and extracts key topics from document content."
    args_schema: Type[BaseModel] = SummarizationInput

    def __init__(self, llm=None):
        super().__init__()
        # Use provided LLM or fallback to default
        if llm:
            self._llm = llm
        else:
            self._llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")

    def _execute(self, document_content: str, document_type: str, **kwargs: Any) -> dict[str, Any]:
        """
        Calls an LLM to generate a detailed summary based on the document content.
        """
        # Limit content to roughly fit context window if it's exceedingly large,
        # but Gemini 2.0 Flash handles 1M tokens, so we're generally fine.
        
        prompt = f"""
        You are an expert document analyst. Please read the following {document_type} content
        and provide a highly detailed summary.
        
        Also extract the key topics and outline them.

        --- DOCUMENT CONTENT ---
        {document_content[:500000]} # Safe truncating just in case
        ------------------------
        
        Return your answer structured as a detailed report containing:
        1. Executive Summary
        2. Key Topics/Themes
        3. Important Details
        """
        
        # Simple invoke
        response = self._llm.invoke(prompt)
        
        return {
            "summary": response.content
        }
