import json
import logging
from typing import Dict, List, Any, Optional
from app.utils.logging import get_logger
from app.services.llm_service import call_llm

logger = get_logger(__name__)

async def process_query(query, user_id=None, max_functions=3, max_iterations=2):
    """
    Process a natural language query using the LLM to determine which functions to call.
    Handles function calling logic and execution.
    
    Args:
        query (str): The natural language query
        user_id (str, optional): The user ID for context
        max_functions (int): Maximum number of functions to call in a single query
        max_iterations (int): Maximum number of back-and-forth iterations with the LLM
        
    Returns:
        dict: Result containing LLM response and any function call results
    """
    logger.info(f"Processing query: {query}")
    
    # Direct function call detection for common queries
    # For example: getCourses or getCourses({})
    if query.strip().startswith("getCourses") or query.strip().startswith("getUserProfile"):
        logger.info(f"Detected direct function call in query: {query}")
        
        # Extract function name and arguments
        import re
        function_match = re.match(r'(\w+)(?:\(\s*(\{.*\})\s*\))?', query.strip())
        
        if function_match:
            function_name = function_match.group(1)
            args_str = function_match.group(2) if function_match.group(2) else "{}"
            
            try:
                args_dict = json.loads(args_str)
            except json.JSONDecodeError:
                args_dict = {}
                
            # Add user_id to arguments if needed
            if user_id and function_name in ["getUserProfile", "getCourses"]:
                if "user_id" not in args_dict:
                    args_dict["user_id"] = user_id
                    logger.info(f"Added user_id {user_id} to function arguments")
            
            # Execute the function
            try:
                result = await route_query_to_function(function_name, args_dict, user_id)
                
                # Return a simple response with the function call and result
                return {
                    "response": f"Here are the results for {function_name}:",
                    "function_calls": [{"name": function_name, "arguments": args_dict}],
                    "function_results": [{"name": function_name, "result": result}]
                }
            except Exception as e:
                logger.error(f"Error executing direct function call {function_name}: {e}")
                return {
                    "response": f"Error executing function {function_name}: {str(e)}",
                    "function_calls": [{"name": function_name, "arguments": args_dict}],
                    "function_results": [{"name": function_name, "error": str(e)}]
                }
    
    # Track all function calls for logging/debugging
    all_function_calls = []
    
    # Conversation history for the LLM
    messages = []
    
    if user_id:
        system_message = get_system_message_with_context(user_id)
    else:
        system_message = get_default_system_message()
    
    messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": query})
    
    iteration = 0
    while iteration < max_iterations:
        try:
            logger.info(f"LLM iteration {iteration+1}/{max_iterations}")
            
            # Call the LLM
            llm_response = await call_llm(messages)
            
            # Extract content and function calls from the LLM response
            # Handle AIMessage object correctly
            if hasattr(llm_response, 'content'):
                content = llm_response.content or ""
            else:
                content = ""

            # Extract function calls
            function_calls = extract_function_calls(llm_response)
            
            if not function_calls:
                # If no function calls, just return the content
                logger.info("No function calls detected in LLM response")
                return {
                    "response": content,
                    "function_calls": all_function_calls
                }
            
            # Limit the number of function calls
            function_calls = function_calls[:max_functions]
            
            # Add these function calls to our tracking
            all_function_calls.extend(function_calls)
            
            # Process each function call
            function_responses = []
            for func_call in function_calls:
                func_name = func_call.get("name")
                func_args = func_call.get("arguments", {})
                
                logger.info(f"Executing function: {func_name} with args: {func_args}")
                
                # Add user_id to function args if needed
                if user_id and func_name in ["getUserProfile", "getCourses"]:
                    if "user_id" not in func_args:
                        func_args["user_id"] = user_id
                        logger.info(f"Added user_id {user_id} to function arguments")
                
                try:
                    # This is where we execute the function call
                    result = await route_query_to_function(func_name, func_args, user_id)
                    
                    # Format the response for the LLM
                    function_response = {
                        "name": func_name,
                        "response": result
                    }
                    function_responses.append(function_response)
                    
                except Exception as e:
                    logger.error(f"Error executing function {func_name}: {e}")
                    function_response = {
                        "name": func_name,
                        "error": str(e)
                    }
                    function_responses.append(function_response)
            
            # Add LLM response to conversation history
            messages.append({"role": "assistant", "content": content, "function_calls": function_calls})
            
            # Add function results to conversation history
            if function_responses:
                function_results_message = format_function_results(function_responses)
                messages.append({"role": "function", "content": function_results_message})
            
            # If this was the last iteration, return current content
            if iteration == max_iterations - 1 or not function_responses:
                return {
                    "response": content,
                    "function_calls": all_function_calls,
                    "function_results": function_responses
                }
            
            # Otherwise, continue the conversation
            messages.append({
                "role": "user", 
                "content": "Please continue based on these function results."
            })
            
            iteration += 1
        
        except Exception as e:
            logger.error(f"Error in LLM processing: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "error": f"An error occurred while processing your request: {str(e)}",
                "function_calls": all_function_calls
            }
    
    # We should never reach here due to the return inside the loop,
    # but just in case
    return {
        "response": "I apologize, but I was unable to complete your request.",
        "function_calls": all_function_calls
    }

# -------------------- Query Router --------------------

async def route_query_to_function(function_name, function_args, user_id=None):
    """
    Route a query to the appropriate function based on the function name.
    
    Args:
        function_name (str): The name of the function to call
        function_args (dict): The arguments to pass to the function
        user_id (str, optional): The user ID for context
        
    Returns:
        Any: The result of the function call
    """
    logger.info(f"Routing query to function: {function_name}")
    
    # Add user_id to function args for functions that might need it
    if user_id and function_name in ["getUserProfile", "getCourses"]:
        if "user_id" not in function_args:
            function_args["user_id"] = user_id
    
    return await execute_function_call(function_name, function_args, user_id)

# -------------------- Function Execution --------------------

async def execute_function_call(function_name, function_args, user_id=None):
    """
    Execute a function call with the provided arguments.
    
    Args:
        function_name (str): The name of the function to call
        function_args (dict): The arguments to pass to the function
        user_id (str, optional): The user ID for context
        
    Returns:
        Any: The result of the function call
    """
    logger.info(f"Executing function call: {function_name} with args: {function_args}")
    
    # Import API functions dynamically
    from app.services.api_functions import (
        getUserProfile, getCourses, getAssignments, search_faqs,
        web_search, generate_learning_roadmap, get_course_with_grades
    )
    
    # Simple functions for testing
    def add_numbers(a, b):
        return a + b
    
    def multiply_numbers(a, b):
        return a * b
    
    # Mock implementations for testing when database connections fail
    # These will be used as fallbacks if the real functions fail with connection errors
    async def mock_getUserProfile(userId):
        return {
            "id": userId,
            "username": "test_user",
            "email": "test@example.edu",
            "role": "student",
            "name": "Test User",
            "is_mock_data": True
        }
    
    async def mock_getCourses(user_id):
        return [
            {
                "id": "830a19f9-6c8e-4df7-9b7f-c78e03966ad4",
                "name": "Introduction to Computer Science",
                "code": "CS101",
                "description": "An introductory course to computer science",
                "is_mock_data": True
            },
            {
                "id": "a51c8c7d-9e6b-4f5a-8e3d-4c7b9e1f6a8b",
                "name": "Data Structures and Algorithms",
                "code": "CS201",
                "description": "A course on data structures and algorithms",
                "is_mock_data": True
            }
        ]
    
    async def mock_getAssignments(courseId):
        return [
            {
                "id": "b7d2f2f9-8b5a-4f5a-9e3d-6c7b9e1f6a8b",
                "title": "Assignment 1",
                "description": "First assignment for the course",
                "due_date": "2023-12-15",
                "is_mock_data": True
            },
            {
                "id": "c8e3f3f0-9c6b-5f6a-0f4e-7d8c0f2g7b9c",
                "title": "Assignment 2",
                "description": "Second assignment for the course",
                "due_date": "2023-12-22",
                "is_mock_data": True
            }
        ]
    
    async def mock_search_faqs(query):
        return [
            {
                "id": "d9f4g4f1-0d7c-6g7b-1g5f-8e9d1f3h8c0d",
                "question": "How do I reset my password?",
                "answer": "You can reset your password by clicking on the 'Forgot Password' link on the login page.",
                "is_mock_data": True
            },
            {
                "id": "e0g5h5g2-1e8d-7h8c-2h6g-9f0e2g4i9d1e",
                "title": "How do I enroll in a course?",
                "answer": "You can enroll in a course by going to the course catalog and clicking on the 'Enroll' button for the course you want to take.",
                "is_mock_data": True
            }
        ]
    
    async def mock_generate_learning_roadmap(topic, difficulty="beginner"):
        return {
            "topic": topic,
            "difficulty": difficulty,
            "roadmap": [
                {
                    "title": "Fundamentals",
                    "description": "Learn the basic concepts of " + topic,
                    "resources": [
                        {"title": "Introduction to " + topic, "type": "Article", "url": "https://example.com/intro"}
                    ]
                },
                {
                    "title": "Intermediate Concepts",
                    "description": "Advance your knowledge of " + topic,
                    "resources": [
                        {"title": topic + " in Practice", "type": "Video", "url": "https://example.com/practice"}
                    ]
                },
                {
                    "title": "Advanced Topics",
                    "description": "Master " + topic + " completely",
                    "resources": [
                        {"title": "Advanced " + topic, "type": "Course", "url": "https://example.com/advanced"}
                    ]
                }
            ],
            "is_mock_data": True
        }
    
    # Map of function names to their implementations
    function_map = {
        "add_numbers": add_numbers,
        "multiply_numbers": multiply_numbers,
        "getUserProfile": getUserProfile,
        "getCourses": getCourses,
        "getAssignments": getAssignments,
        "search_faqs": search_faqs,
        "web_search": web_search,
        "generate_learning_roadmap": generate_learning_roadmap,
        "get_course_with_grades": get_course_with_grades
    }
    
    # Map of function names to their mock implementations
    mock_function_map = {
        "getUserProfile": mock_getUserProfile,
        "getCourses": mock_getCourses,
        "getAssignments": mock_getAssignments,
        "search_faqs": mock_search_faqs,
        "generate_learning_roadmap": mock_generate_learning_roadmap
    }
    
    # Check if the function exists
    if function_name not in function_map:
        error_msg = f"Function '{function_name}' is not recognized"
        logger.error(error_msg)
        return {"error": error_msg}
    
    # Get the function
    function = function_map[function_name]
    
    try:
        # Special cases for parameter handling
        if function_name == "getUserProfile":
            # Handle parameter name differences - API expects 'userId' but function router passes 'user_id'
            if "user_id" in function_args and "userId" not in function_args:
                function_args["userId"] = function_args.pop("user_id")
                logger.info(f"Renamed parameter 'user_id' to 'userId' for getUserProfile function")
            elif "userId" not in function_args and user_id:
                function_args["userId"] = user_id
                logger.info(f"Added userId={user_id} to function arguments")
                
        # Make sure required parameters are present
        elif function_name == "getCourses":
            if "user_id" not in function_args and user_id:
                function_args["user_id"] = user_id
                logger.info(f"Added user_id={user_id} to function arguments")
        
        # Handle parameter name differences for generate_learning_roadmap
        elif function_name == "generate_learning_roadmap":
            # If courseId is provided instead of topic, rename it
            if "courseId" in function_args and "topic" not in function_args:
                # Use course ID as the topic or extract course name if available
                function_args["topic"] = function_args.pop("courseId")
                logger.info(f"Renamed parameter 'courseId' to 'topic' for generate_learning_roadmap function")
            
            # If both course and difficulty are provided, ensure correct parameter names
            if "course" in function_args and "topic" not in function_args:
                function_args["topic"] = function_args.pop("course")
                logger.info(f"Renamed parameter 'course' to 'topic' for generate_learning_roadmap function")
            
            if "level" in function_args and "difficulty" not in function_args:
                function_args["difficulty"] = function_args.pop("level")
                logger.info(f"Renamed parameter 'level' to 'difficulty' for generate_learning_roadmap function")
        
        # Execute the function with the provided arguments
        try:
            result = await function(**function_args)
            return result
        except Exception as e:
            # Check if this is a database connection error
            error_str = str(e).lower()
            if any(err in error_str for err in ["connect call failed", "connection", "database", "timeout"]):
                logger.warning(f"Database connection error in {function_name}, falling back to mock implementation: {e}")
                # Use mock function as fallback if available
                if function_name in mock_function_map:
                    mock_function = mock_function_map[function_name]
                    result = await mock_function(**function_args)
                    return result
            # Re-raise if not a connection error or no mock available
            raise
    
    except Exception as e:
        logger.error(f"Error executing function {function_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": f"Error executing function '{function_name}': {str(e)}"}

# -------------------- Helper Functions --------------------

def extract_function_calls(llm_response):
    """
    Extract function calls from an LLM response.
    
    Args:
        llm_response (dict or AIMessage): The LLM response
        
    Returns:
        list: List of function calls
    """
    function_calls = []
    
    # Handle AIMessage object from langchain
    if hasattr(llm_response, 'additional_kwargs'):
        if 'function_calls' in llm_response.additional_kwargs:
            raw_calls = llm_response.additional_kwargs['function_calls']
            for call in raw_calls:
                if isinstance(call, dict) and 'name' in call:
                    arguments = call.get('arguments', {})
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except:
                            arguments = {}
                    function_calls.append({
                        'name': call['name'],
                        'arguments': arguments
                    })
        elif 'tool_calls' in llm_response.additional_kwargs:
            raw_calls = llm_response.additional_kwargs['tool_calls']
            for tool_call in raw_calls:
                if isinstance(tool_call, dict) and tool_call.get('type') == 'function':
                    function_info = tool_call.get('function', {})
                    try:
                        arguments = json.loads(function_info.get('arguments', '{}'))
                    except:
                        arguments = {}
                    
                    function_calls.append({
                        'name': function_info.get('name'),
                        'arguments': arguments
                    })
        return function_calls
    
    # Handle dictionary responses (OpenAI format)
    if isinstance(llm_response, dict):
        # Check if the response has the tool_calls field (OpenAI format)
        if "tool_calls" in llm_response and llm_response["tool_calls"]:
            for tool_call in llm_response["tool_calls"]:
                if tool_call.get("type") == "function":
                    function_info = tool_call.get("function", {})
                    try:
                        arguments = json.loads(function_info.get("arguments", "{}"))
                    except:
                        arguments = {}
                    
                    function_calls.append({
                        "name": function_info.get("name"),
                        "arguments": arguments
                    })
        
        # Check if the response has function_calls field (Claude format)
        if "function_calls" in llm_response and llm_response["function_calls"]:
            for func_call in llm_response["function_calls"]:
                try:
                    if isinstance(func_call, str):
                        # Try to parse if it's a string
                        parsed_call = json.loads(func_call)
                        name = parsed_call.get("name")
                        arguments = parsed_call.get("arguments", {})
                    else:
                        # Otherwise assume it's already structured
                        name = func_call.get("name")
                        arguments = func_call.get("arguments", {})
                    
                    function_calls.append({
                        "name": name,
                        "arguments": arguments
                    })
                except:
                    # Skip invalid function calls
                    continue
    
    # If we extracted no functions, try to check if it contains function calls in the content
    if not function_calls and hasattr(llm_response, 'content') and llm_response.content:
        try:
            # Try to find function calls in content using pattern matching
            import re
            # Look for patterns like: "function_call: { "name": "functionName", "arguments": {...} }"
            function_call_pattern = r'function_call["\']*\s*:\s*\{\s*["\']name["\']\s*:\s*["\']([\w\d_]+)["\'].*?["\']arguments["\']\s*:\s*(\{.*?\})'
            matches = re.findall(function_call_pattern, llm_response.content, re.DOTALL)
            
            for match in matches:
                name = match[0]
                try:
                    args = json.loads(match[1])
                except:
                    args = {}
                
                function_calls.append({
                    "name": name,
                    "arguments": args
                })
        except Exception:
            pass
            
    return function_calls

def format_function_results(function_responses):
    """
    Format function results for the LLM.
    
    Args:
        function_responses (list): List of function responses
        
    Returns:
        str: Formatted function results
    """
    result_parts = []
    
    for response in function_responses:
        func_name = response.get("name", "unknown")
        
        if "error" in response:
            result = f"Error: {response['error']}"
        else:
            result = json.dumps(response.get("response", {}), indent=2)
        
        result_parts.append(f"Function: {func_name}\nResult: {result}\n")
    
    return "\n".join(result_parts)

def get_default_system_message():
    """Get the default system message for the LLM"""
    return """You are an AI assistant for an educational platform. Your goal is to help users by answering questions
and providing information about courses, assignments, user profiles, and other educational resources.

When a user asks you a question, you should:
1. Determine if you need information from the system to answer the question.
2. If needed, call the appropriate function to get that information.
3. Provide a helpful and concise response based on the information you receive.

You have access to several functions that can retrieve information from the system. Call these functions when needed
to provide accurate and helpful responses."""

def get_system_message_with_context(user_id):
    """
    Get a system message with user context.
    
    Args:
        user_id (str): The user ID
        
    Returns:
        str: System message with context
    """
    return f"""You are an AI assistant for an educational platform. Your goal is to help users by answering questions
and providing information about courses, assignments, user profiles, and other educational resources.

You are currently speaking with user ID: {user_id}

When a user asks you a question, you should:
1. Determine if you need information from the system to answer the question.
2. If needed, call the appropriate function to get that information.
3. Provide a helpful and concise response based on the information you receive.

You have access to several functions that can retrieve information from the system. Call these functions when needed
to provide accurate and helpful responses.""" 