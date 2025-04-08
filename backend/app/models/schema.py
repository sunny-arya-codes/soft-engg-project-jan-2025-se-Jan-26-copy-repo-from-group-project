from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

class LLMResponse(BaseModel):
    """
    Schema for responses from the LLM service
    """
    content: str
    function_calls: Optional[List[Dict[str, Any]]] = None
    function_results: Optional[List[Dict[str, Any]]] = None
    raw_tool_calls: Optional[List[Dict[str, Any]]] = None 