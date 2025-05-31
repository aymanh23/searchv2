# searchv2/tools/trusted_medical_search_tool.py
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from searchv2.tools.serper_tool import SerperSearchTool
from crewai_tools import WebsiteSearchTool

class TrustedMedicalSearchInput(BaseModel):
    query: str = Field(..., description="The symptom or condition to search for.")

class TrustedMedicalSearchTool(BaseTool):
    name: str = "Trusted Medical Search Tool"
    description: str = "Performs semantic RAG-based search on trusted medical websites."
    args_schema: Type[BaseModel] = TrustedMedicalSearchInput

    def _run(self, query: str) -> str:
        serper_data = SerperSearchTool()._run(query)
        links = serper_data["links"]

        articles = []
        for link in links:
            try:
                print(f"[TrustedSearchTool] Fetching: {link}")
                tool = WebsiteSearchTool(
                    website=link,
                    config=dict(
                        llm=dict(
                            provider="google",
                            config=dict(
                                model="gemini/gemini-2.0-flash",
                            ),
                        ),
                        embedder=dict(
                            provider="google",
                            config=dict(
                                model="models/embedding-001",
                                task_type="retrieval_document",
                            ),
                        ),
                    )
                )
                content = tool._run(query)
                if content and len(content.strip()) > 500:
                    articles.append(content)
            except Exception as e:
                print(f"[TrustedSearchTool] Failed {link}: {e}")

        return "\n\n".join(articles[:2]) if articles else "No relevant content could be extracted."
