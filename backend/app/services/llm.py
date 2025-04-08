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
            content = llm_response.get("content", "")
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
    
    # Map function names to actual functions
    function_map = {
        # User functions
        "getUserProfile": getUserProfile,
        
        # Course functions
        "getCourses": getCourses,
        "get_course_with_grades": get_course_with_grades,
        
        # Assignment functions
        "getAssignments": getAssignments,
        
        # FAQ functions
        "search_faqs": search_faqs,
        
        # Web search functions
        "web_search": web_search,
        
        # Learning roadmap functions 
        "generate_learning_roadmap": generate_learning_roadmap,
        
        # Simple test functions
        "add_numbers": add_numbers,
        "multiply_numbers": multiply_numbers,
    }
    
    if function_name not in function_map:
        logger.error(f"Function {function_name} not found in function map")
        return {"error": f"Function '{function_name}' not found"}
    
    try:
        # Get the actual function
        function = function_map[function_name]
        
        # Special handling for certain functions
        if function_name == "getUserProfile":
            # Make sure user_id is in the args
            if "user_id" not in function_args and user_id:
                function_args["user_id"] = user_id
        
        # Execute the function with the provided arguments
        result = await function(**function_args)
        return result
    
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
        llm_response (dict): The LLM response
        
    Returns:
        list: List of function calls
    """
    function_calls = []
    
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