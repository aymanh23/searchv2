# serper_tool.py

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import requests
import os


class SerperToolInput(BaseModel):
    """Input schema for SerperSearchTool."""
    query: str = Field(..., description="The search query string for medical information.")


class SerperSearchTool(BaseTool):
    name: str = "Serper Search Tool"
    description: str = (
        "Useful for searching the web for up-to-date and relevant medical information using Serper.dev Google search API. "
        "Returns top results with titles, snippets, and links for the provided query."
    )
    args_schema: Type[BaseModel] = SerperToolInput

    def _run(self, query: str) -> dict:
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            raise ValueError("SERPER_API_KEY is not set in the environment variables.")

        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "q": f"{query} site:mayoclinic.org OR site:heart.org OR site:cdc.gov OR site:medlineplus.gov OR site:nhs.uk"
        }

        response = requests.post("https://google.serper.dev/search", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        links = []
        metadata = []

        for item in data.get("organic", [])[:5]:
            links.append(item.get("link"))
            metadata.append({
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "link": item.get("link")
            })

        return {"links": links, "metadata": metadata} 