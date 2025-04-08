from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel
from fastapi import HTTPException
import inspect
import json
from functools import wraps
import logging
import asyncio
import re

logger = logging.getLogger(__name__)

class FunctionDeclaration(BaseModel):
    """Schema for function declarations that Gemini can understand"""
    name: str
    description: str
    parameters: Dict[str, Any]
    roles: Optional[List[str]] = None  # List of roles that can access this function

class FunctionRouter:
    """
    Function router service that manages available functions and their declarations
    for Gemini to use in compositional function calling.
    """
    def __init__(self):
        self._functions: Dict[str, Dict] = {}
        self._function_declarations: List[Dict] = []

    def register_function(self, name: str, description: str, handler, parameters: Dict[str, Any], roles: Optional[List[str]] = None):
        """
        Register a new function with its declaration and handler
        
        Args:
            name: Function name
            description: Function description
            handler: The actual function to be called
            parameters: OpenAPI compatible parameter schema
            roles: Optional list of roles that can access this function (None means all roles)
        """
        try:
            if not name or not isinstance(name, str):
                logger.error(f"Invalid function name: {name}")
                return
            
            if not handler or not callable(handler):
                logger.error(f"Invalid handler for function {name}")
                return
            
            logger.info(f"Registering function: {name}, roles: {roles}")
            
            # Ensure parameters is a dictionary
            if not parameters:
                parameters = {"type": "object", "properties": {}}
            
            # Ensure roles is a list or None
            if roles and not isinstance(roles, list):
                roles = [str(roles)]
            
            self._functions[name] = {
                "handler": handler,
                "declaration": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                    "roles": roles
                }
            }
            self._function_declarations.append(self._functions[name]["declaration"])
            logger.debug(f"Function {name} registered successfully")
        except Exception as e:
            logger.error(f"Error registering function {name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def get_function_declarations(self, role: Optional[str] = None) -> List[Dict]:
        """
        Get registered function declarations for Gemini, optionally filtered by role
        
        Args:
            role: Optional role to filter functions by
            
        Returns:
            List of function declarations accessible to the given role
        """
        try:
            # If no role specified or role is "admin", return all functions
            if role is None or role.lower() == "admin":
                logger.debug(f"Returning all {len(self._function_declarations)} functions for admin/unspecified role")
                return self._function_declarations
            
            # Filter functions based on role
            filtered_functions = [
                func for func in self._function_declarations
                if "roles" not in func or func.get("roles") is None or role.lower() in [r.lower() for r in func.get("roles", [])]
            ]
            
            logger.debug(f"Filtered functions by role '{role}': {len(filtered_functions)} of {len(self._function_declarations)}")
            return filtered_functions
        except Exception as e:
            logger.error(f"Error in get_function_declarations: {str(e)}")
            # Return empty list in case of error to avoid breaking the application
            return []

    def get_canonical_function_name(self, name: str) -> Optional[str]:
        """
        Get the canonical function name, handling different case conventions
        
        For example, if 'getCourses' and 'get_courses' are both registered,
        this method will return the registered name for either input.
        
        Args:
            name: The function name to check
            
        Returns:
            The canonical function name if it exists, or None
        """
        # Check direct match first
        if name in self._functions:
            return name
            
        # Try to match camelCase to snake_case and vice versa
        snake_case = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        if snake_case in self._functions:
            logger.info(f"Matched function {name} to canonical name {snake_case}")
            return snake_case
            
        # Convert snake_case to camelCase
        camel_case_parts = name.split('_')
        camel_case = camel_case_parts[0] + ''.join(x.title() for x in camel_case_parts[1:])
        if camel_case in self._functions:
            logger.info(f"Matched function {name} to canonical name {camel_case}")
            return camel_case
            
        # No match found
        return None

    async def execute_function(self, name: str, args: Dict[str, Any], user_role: str = None) -> Any:
        """
        Execute a registered function with the given arguments
        
        Args:
            name: Name of the function to execute
            args: Arguments to pass to the function
            user_role: Role of the user executing the function, used for authorization
            
        Returns:
            Result of the function execution
        
        Raises:
            ValueError: If the function is not registered or user is not authorized
        """
        # Get canonical function name (handling different case conventions)
        canonical_name = self.get_canonical_function_name(name)
        if not canonical_name:
            logger.error(f"Function {name} not registered (no canonical match)")
            raise ValueError(f"Function '{name}' not registered")
        
        function_info = self._functions[canonical_name]
        
        # Check if function requires authorization
        if function_info.get("roles") and user_role:
            # If roles are specified, check if user has the required role
            allowed_roles = function_info.get("roles")
            if user_role not in allowed_roles:
                logger.warning(f"User with role {user_role} not authorized to execute function {canonical_name}")
                raise ValueError(f"Not authorized to execute function '{canonical_name}'")
        
        # Get the function handler
        handler = function_info.get("handler")
        if not handler or not callable(handler):
            logger.error(f"Function {canonical_name} has no valid handler")
            raise ValueError(f"Function '{canonical_name}' has no valid handler")
        
        # Execute the function with the provided arguments
        try:
            # Check if the handler is async
            if inspect.iscoroutinefunction(handler):
                result = await handler(**args)
            else:
                # Run synchronous functions in a thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: handler(**args))
            
            # If we got a Pydantic model back, convert it to a dictionary
            if hasattr(result, "dict") and callable(result.dict):
                result = result.dict()
            elif hasattr(result, "model_dump") and callable(result.model_dump):
                result = result.model_dump()
                
            logger.info(f"Successfully executed function {canonical_name}")
            return result
        except Exception as e:
            logger.error(f"Error executing function {canonical_name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def function_declaration(self, name: str, description: str, parameters: Dict[str, Any], roles: Optional[List[str]] = None):
        """
        Decorator to register API endpoint functions
        
        Example:
            @function_router.function_declaration(
                name="get_courses",
                description="Get available courses",
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Course category"
                        }
                    }
                },
                roles=["student", "faculty", "admin"]
            )
            async def get_courses(category: str):
                # Function implementation
                pass
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            
            self.register_function(name, description, wrapper, parameters, roles)
            return wrapper
        return decorator

    async def web_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform a web search for the given query.
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            
        Returns:
            List of search results with title, snippet, and url
        """
        try:
            # This is a mock implementation - in production, you would integrate with a real search API
            # such as Google Custom Search, Bing Search, or similar
            logger.info(f"Performing web search for: {query}")
            
            # Mock results - in a real implementation, this would call an external API
            mock_results = [
                {
                    "title": "Understanding Function Calling in LLMs",
                    "snippet": "Function calling allows LLMs to interact with external tools while still using their reasoning capabilities.",
                    "url": "https://example.com/function-calling-llm"
                },
                {
                    "title": "Gemini API Documentation",
                    "snippet": "Gemini can use both its knowledge and function calling to provide comprehensive responses.",
                    "url": "https://ai.google.dev/docs/gemini_api"
                },
                {
                    "title": "Best Practices for AI Assistants",
                    "snippet": "Effective AI assistants combine model knowledge with external tools for the best user experience.",
                    "url": "https://example.com/ai-assistant-best-practices"
                }
            ]
            
            # Return limited number of results
            return mock_results[:num_results]
        except Exception as e:
            logger.error(f"Error in web_search: {str(e)}")
            return [{"title": "Error", "snippet": f"Failed to perform web search: {str(e)}", "url": ""}]

# Create global function router instance
function_router = FunctionRouter() 

# Register API functions
from app.services.api_functions import (
    getUserProfile, getCourses, getAssignments, search_faqs,
    web_search, generate_learning_roadmap, get_course_with_grades
)

# Setup the router with all available functions
def setup_function_router():
    """Register all API functions with the router"""
    
    # User functions
    function_router.register_function(
        name="getUserProfile",
        description="Get a user's profile information",
        handler=getUserProfile,
        parameters={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User ID to get profile for"
                }
            },
            "required": ["user_id"]
        }
    )
    
    # Course functions
    function_router.register_function(
        name="getCourses",
        description="Get courses for a user with optional status filter",
        handler=getCourses,
        parameters={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User ID to get courses for"
                },
                "status": {
                    "type": "string",
                    "description": "Optional status filter (active, completed, etc.)"
                }
            },
            "required": ["user_id"]
        }
    )
    
    function_router.register_function(
        name="get_course_with_grades",
        description="Get a course with all student grades",
        handler=get_course_with_grades,
        parameters={
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "string",
                    "description": "Course ID to get grades for"
                }
            },
            "required": ["course_id"]
        }
    )
    
    # Assignment functions
    function_router.register_function(
        name="getAssignments",
        description="Get assignments for a course with optional user filter",
        handler=getAssignments,
        parameters={
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "string",
                    "description": "Course ID to get assignments for"
                },
                "user_id": {
                    "type": "string",
                    "description": "Optional user ID for filtering submissions"
                }
            },
            "required": ["course_id"]
        }
    )
    
    # FAQ functions
    function_router.register_function(
        name="search_faqs",
        description="Search FAQs based on query text and optional category",
        handler=search_faqs,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text"
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter"
                }
            },
            "required": ["query"]
        }
    )
    
    # Web search functions
    function_router.register_function(
        name="web_search",
        description="Search the web for information using the provided query",
        handler=web_search,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    )
    
    # Learning roadmap functions
    function_router.register_function(
        name="generate_learning_roadmap",
        description="Generate a learning roadmap for a given topic and difficulty level",
        handler=generate_learning_roadmap,
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic to create a roadmap for"
                },
                "difficulty": {
                    "type": "string",
                    "description": "Difficulty level (beginner, intermediate, advanced)",
                    "default": "beginner"
                }
            },
            "required": ["topic"]
        }
    )
    
    logger.info("Function router initialized with API functions")

# Initialize functions when module is imported
setup_function_router() 