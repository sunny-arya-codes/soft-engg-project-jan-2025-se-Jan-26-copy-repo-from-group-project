import os
import logging
import json
import time
import requests
import re  # Add import at the top level
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.services.function_router import function_router
import asyncio
import aiohttp
import backoff
from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)

# Available models cache to avoid repeated API calls
_available_models_cache = None

# Gemini API configuration
GEMINI_API_KEY = settings.GOOGLE_API_KEY
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
GEMINI_MODEL = "gemini-2.5-pro-exp"

INSIGHT_PROMPT_TEMPLATE = """
You are an AI learning analytics expert integrated into an educational platform. Your task is to analyze a student's learning data and provide personalized insights to help improve their learning outcomes.

## User Information
- Name: {name}
- Email: {email}

## Learning Data (JSON format)
```json
{data}
```

## Instructions
Analyze the provided learning data to generate personalized insights. Focus on:
1. Study patterns (when and how they learn best)
2. Content preferences
3. Strengths and weaknesses
4. Specific improvement recommendations
5. Learning opportunities tailored to their needs

## Response Format
Return a JSON object with the following structure:
```json
{
  "studyPatterns": {
    "optimalTime": "String describing when they learn best",
    "preferredContent": "String describing content they engage with most",
    "recommendedSchedule": "String with specific time suggestions"
  },
  "suggestions": {
    "contentType": "String with recommended content type to focus on",
    "reason": "String explaining why this content type is recommended",
    "topic": "String with a specific topic to focus on (if applicable)"
  },
  "opportunities": [
    {
      "type": "String (quiz, review, practice, etc.)",
      "subject": "String with specific subject",
      "reason": "String explaining why this opportunity is valuable"
    },
    {
      "type": "String (quiz, review, practice, etc.)",
      "subject": "String with specific subject",
      "reason": "String explaining why this opportunity is valuable"
    }
  ],
  "statistics": {
    "completionRate": Number,
    "quizAverage": Number,
    "activeLastMonth": Number,
    "strengthTopics": [String topics they excel at]
  }
}
```

Important guidelines:
- Make insights actionable, specific, and personalized
- Base all insights on the actual data provided
- Use a professional, encouraging tone
- Do not reference your own capabilities or that you are an AI
- Focus only on providing the JSON output without any other text

"""

def get_available_models():
    """Get a list of available models from the Gemini API"""
    global _available_models_cache
    
    # Hard-coded list of commonly available models for fast path
    common_models = [
        "gemini-1.5-pro-latest", 
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro", 
        "gemini-1.5-flash",
        "gemini-2.0-flash", 
        "gemini-1.0-pro"
    ]
    
    # Return cached models if available
    if _available_models_cache is not None:
        return _available_models_cache
    
    # Try fast path first - if we can't connect to the API, use common models
    try:
        # Check if model list was cached on disk
        cache_path = os.path.join(os.path.dirname(__file__), "model_cache.json")
        cache_expiry = 3600  # Cache validity in seconds (1 hour)
        
        # Check for valid cache file
        if os.path.exists(cache_path):
            file_age = time.time() - os.path.getmtime(cache_path)
            if file_age < cache_expiry:
                try:
                    with open(cache_path, 'r') as f:
                        cached_data = json.load(f)
                        _available_models_cache = cached_data.get('models', common_models)
                        logger.info(f"Using cached model list ({len(_available_models_cache)} models)")
                        return _available_models_cache
                except (json.JSONDecodeError, IOError):
                    logger.warning("Failed to read model cache file")
        
        # If no valid cache, fetch from API
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY not found in environment")
            _available_models_cache = common_models
            return common_models
        
        # Call the models.list API endpoint with timeout
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        response = requests.get(url, params={"key": api_key}, timeout=2.0)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract model names from response
            models = [model.get("name", "").split("/")[-1] for model in data.get("models", [])]
            
            # Filter to include only Gemini models
            gemini_models = [model for model in models if model.startswith("gemini")]
            
            if gemini_models:
                logger.info(f"Available Gemini models: {len(gemini_models)} models")
                # Cache the results
                _available_models_cache = gemini_models
                
                # Write to cache file
                try:
                    with open(cache_path, 'w') as f:
                        json.dump({'models': gemini_models}, f)
                except IOError:
                    logger.warning("Failed to write model cache file")
                
                return gemini_models
            else:
                logger.warning("No Gemini models found in API response")
                _available_models_cache = common_models
                return common_models
        else:
            logger.error(f"Failed to get models: {response.status_code} - {response.text}")
            _available_models_cache = common_models
            return common_models
    except Exception as e:
        logger.warning(f"Error getting available models: {str(e)}, using default list")
        _available_models_cache = common_models
        return common_models

# Initialize chat model
def get_llm(functions=None, use_fallback=False, use_grounding=True):
    """Get the LLM model instance with function calling enabled
    
    Args:
        functions: List of function declarations to pass to the model
        use_fallback: Whether to use the fallback model (gemini-2.0-flash)
        use_grounding: Whether to enable grounding capabilities
        
    Returns:
        LLM instance configured with the appropriate model
    """
    # Format tools for Gemini API via LangChain
    tools = []
    
    # Add function tools if provided
    if functions:
        # Ensure functions are in the OpenAI-compatible format expected by the Gemini API
        # Each function should be an object with "type": "function" and a nested "function" object
        for func in functions:
            # Check if the function is already in the correct format
            if isinstance(func, dict) and "type" in func and func.get("type") == "function":
                tools.append(func)
            else:
                # Convert to OpenAI-compatible format
                formatted_func = {
                    "type": "function",
                    "function": {
                        "name": func["name"],
                        "description": func["description"],
                        "parameters": func["parameters"]
                    }
                }
                tools.append(formatted_func)
    
    # Add grounding tool if enabled
    if use_grounding:
        logger.info("Enabling grounding with Google Search")
        tools.append({"google_search": {}})
    
    # Get available models
    available_models = get_available_models()
    logger.info(f"All available models: {available_models}")
    
    # Define model preferences - updated with newest experimental models first
    preferred_models = [
        # Use Gemini 2.5 preview first
        "gemini-2.5-pro-preview",
        "gemini-2.5-pro-exp",
        
        # Then Gemini 2.0 flash
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-exp-image-generation",
        
        # Other experimental versions
        "gemini-exp-",
        "gemini-2.0-pro-exp",
        
        # Fallback to other models
        "gemini-1.5-pro-latest",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro", 
        "gemini-1.5-flash"
    ]
    
    fallback_models = [
        "gemini-2.0-flash",  # Primary fallback
        "gemini-1.5-flash-latest",  # Secondary fallback
        "gemini-1.0-pro"  # Last resort fallback
    ]
    
    # Select model based on availability
    model_candidates = fallback_models if use_fallback else preferred_models
    
    # Find the first available model from our candidates
    model_name = None
    matched_prefix = None
    
    # Clean up model names for matching (strip 'models/' prefix)
    clean_available_models = [m.replace('models/', '') if m.startswith('models/') else m for m in available_models]
    logger.debug(f"Clean available models: {clean_available_models}")
    
    # First try exact matches (with more flexible name handling)
    for model in model_candidates:
        # Check for exact match
        if model in clean_available_models:
            model_name = model
            logger.info(f"Found exact match for model: {model_name}")
            break
            
        # Also check for model names that contain our candidate (for versioned models like gemini-2.5-pro-preview-03-25)
        matching_models = [m for m in clean_available_models if model in m]
        if matching_models:
            model_name = matching_models[0]  # Use the first match
            logger.info(f"Found match for {model}: {model_name}")
            break
    
    # If no exact match, try prefix matches
    if not model_name:
        for prefix in model_candidates:
            matching_models = [m for m in clean_available_models if m.startswith(prefix)]
            if matching_models:
                model_name = matching_models[0]  # Use the first match
                matched_prefix = prefix
                logger.info(f"Found prefix match for {prefix}: {model_name}")
                break
    
    # If no preferred models are available, use any gemini model
    if not model_name and available_models:
        model_name = available_models[0]  # Use the first available model
        logger.info(f"No preferred models available, using: {model_name}")
    
    # Last resort fallback
    if not model_name:
        model_name = "gemini-1.0-pro"  # Default fallback if API didn't return models
        logger.warning(f"No models found in API response, using default: {model_name}")
    
    # Detailed logging about model selection
    logger.info(f"SELECTED MODEL: {model_name}")
    if matched_prefix:
        logger.info(f"Matched from prefix: {matched_prefix}")
    logger.info(f"Fallback mode: {use_fallback}")
    logger.info(f"Grounding enabled: {use_grounding}")
    logger.info(f"Tools configured: {len(tools)} tools")
    
    # Create the model instance
    model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.0,  # Use zero temperature for deterministic function calling
        convert_system_message_to_human=False,  # Updated - no longer using deprecated approach
        tools=tools if tools else None,  # Pass the function definitions and grounding tools to the model
        max_retries=1,  # Reduce retry attempts to fail faster
        additional_kwargs={
            "tool_choice": "auto"  # Enable automatic tool choice for OpenAI compatibility
        }
    )
    
    logger.info(f"Successfully created LLM instance with model: {model_name}")
    return model

# System message to help the LLM understand available functions
def get_system_prompt():
    """Get the system prompt for the LLM with instructions about function usage"""
    return """
    You are a helpful AI assistant for an educational platform. 
You have access to tools that you can call to retrieve information or perform actions.
you should anaswer only about the course related questions 
in case of questions that are quiz and assignemnt related avoid direct answer guide the user to the correct answer by step by step solving on his part.  
talk only about the courses and dont talk about other stuff. 

GUIDELINES FOR TOOL CALLING:
1. When a user asks for specific information that requires database access, like courses, FAQs, or user details, ALWAYS use the appropriate function tool.
2. Call functions with all required parameters and appropriate optional parameters when helpful.
3. Directly respond to simple questions that don't require database access.
4. Return function execution results in a user-friendly format.
5. If a function returns an error, explain the issue to the user in simple terms.
6. When multiple functions might apply, choose the most specific one for the task.

FUNCTION CALLING INSTRUCTIONS:
- ALWAYS use function calling for retrieving data from the system
- When function calling is needed, call the function FIRST, then provide your response
- DO NOT make up information about courses, users, assignments, or other system data
- DO format function arguments correctly based on the function's parameter schema
- Each function call will be automatically executed and the results will be returned to you
- DO NOT print the function call JSON in your response content - it must be provided in the designated tool_calls field

CRITICAL INSTRUCTIONS ABOUT FUNCTION OUTPUTS:
- NEVER output function calls directly in your text response like this:
  ❌ WRONG: "Let me call getCourses()"
  ❌ WRONG: "print(getCourses())"
  ❌ WRONG: "getCourses()"
  ❌ WRONG: "function getCourses()"
- ALWAYS use the proper tool_calls or function_call format as structured data
- NEVER include code blocks with function calls
- DO NOT use backticks (```) to format function calls

IMPORTANT TECHNICAL NOTE ABOUT JSON FORMATTING:
- Function arguments MUST be valid JSON
- Always use double quotes (") for keys and string values, not single quotes (')
- Boolean values must be lowercase: true or false, not True or False
- Numbers should not have quotes
- Example of properly formatted arguments: {"name": "value", "count": 3, "active": true}

CRITICALLY IMPORTANT: DO NOT INCLUDE THE FUNCTION CALL JSON IN YOUR RESPONSE TEXT.
The AI system will automatically detect and execute your function calls - you only need to make them in the proper format.
The function call should be provided in the tool_calls field, NOT in your text response.

FUNCTION CALLING FORMAT:
You MUST use the EXACT OpenAI function calling format when using tools.
The correct format is a JSON object with tool_calls array containing function objects:
{
  "tool_calls": [
    {
      "id": "call_9g1881818181818181818181",
      "type": "function",
      "function": {
        "name": "function_name",
        "arguments": "{\"param1\": \"value1\", \"param2\": 42}"
      }
    }
  ]
}

EXAMPLE FUNCTION CALLING WORKFLOW:
1. User asks: "Show me my courses"
2. You call the getCourses() function using the correct tool_calls format (not printed in the response)
3. System executes the function and returns results to you
4. You provide a human-friendly response based on those results

GROUNDING INSTRUCTIONS:
- When you need information that is not available in the system or might be outdated, use Google Search
- For questions about current events, latest technologies, or general knowledge not specific to the educational platform, use grounding
- Use grounding to complement the system data, especially for providing up-to-date information
- Properly attribute information obtained through grounding by mentioning the source

Be helpful, concise, and professional in all your responses."""

# Store loaded LLM instances for reuse
_llm_cache = {}

async def call_llm(messages, use_fallback=False, use_grounding=True):
    """Function to call the LLM model with the provided messages and handle function calling"""
    # Get function declarations for the LLM
    functions = function_router.get_function_declarations()
    
    # Format functions correctly for Gemini API OpenAI compatibility
    if not hasattr(call_llm, '_formatted_functions'):
        formatted_functions = []
        for func in functions:
            # Use OpenAI-compatible format with type:function
            formatted_func = {
                "type": "function",
                "function": {
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": func["parameters"]
                }
            }
            formatted_functions.append(formatted_func)
        call_llm._formatted_functions = formatted_functions
    else:
        formatted_functions = call_llm._formatted_functions
    
    # Create a cache key based on the model settings - fixed with local variables
    cache_key = f"primary_grounding_{use_grounding}" if not use_fallback else f"fallback_grounding_{use_grounding}"
    
    # Try with the primary model first
    try:
        # Check if we have a cached LLM instance
        if cache_key not in _llm_cache:
            # Create and cache the LLM
            logger.info(f"Creating new LLM instance with cache key: {cache_key}")
            _llm_cache[cache_key] = get_llm(formatted_functions, use_fallback=use_fallback, use_grounding=use_grounding)
        else:
            logger.info(f"Using cached LLM instance with key: {cache_key}")
        
        # Get the cached LLM
        llm = _llm_cache[cache_key]
        
        # Get cached prompt template if available, create it otherwise
        if not hasattr(call_llm, '_prompt_template'):
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessage(content=get_system_prompt()),
                MessagesPlaceholder(variable_name="messages")
            ])
            call_llm._prompt_template = prompt_template
            logger.info("Created new prompt template")
        else:
            prompt_template = call_llm._prompt_template
            logger.info("Using cached prompt template")
        
        # Apply the prompt template to the current state (this can't be cached as messages change)
        prompt = await prompt_template.ainvoke({"messages": messages})
        
        # Call the LLM with the prompt
        start_time = time.time()
        logger.info("Sending request to LLM...")
        response = await llm.ainvoke(prompt)
        elapsed = time.time() - start_time
        logger.info(f"LLM response received in {elapsed:.2f} seconds")
        
        # Log the raw response for debugging
        if hasattr(response, 'additional_kwargs'):
            logger.debug(f"Response additional_kwargs: {json.dumps(response.additional_kwargs, default=str)}")
        
        # Check for grounding evidence in the response
        has_grounding = False
        if hasattr(response, 'additional_kwargs') and 'grounding' in str(response.additional_kwargs):
            has_grounding = True
            logger.info("Grounding information detected in response")
        
        logger.info(f"Grounding enabled: {use_grounding}, Grounding detected: {has_grounding}")
        
    except Exception as e:
        logger.warning(f"Primary model failed: {str(e)}. Falling back to secondary model")
        import traceback
        logger.warning(traceback.format_exc())
        
        # Try the fallback model
        try:
            # Check if we have a cached fallback LLM instance
            fallback_key = "fallback_grounding_true"
            if fallback_key not in _llm_cache:
                # Create and cache the fallback LLM
                logger.info("Creating new fallback LLM instance")
                _llm_cache[fallback_key] = get_llm(formatted_functions, use_fallback=True, use_grounding=True)
            else:
                logger.info("Using cached fallback LLM instance")
            
            # Get the cached fallback LLM
            llm_fallback = _llm_cache[fallback_key]
            
            # Use the same prompt template as before
            prompt_template = call_llm._prompt_template
            prompt = await prompt_template.ainvoke({"messages": messages})
            
            # Call the fallback LLM
            start_time = time.time()
            logger.info("Sending request to fallback LLM...")
            response = await llm_fallback.ainvoke(prompt)
            elapsed = time.time() - start_time
            logger.info(f"Fallback LLM response received in {elapsed:.2f} seconds")
            
            # Check for grounding evidence in fallback response
            has_grounding = False
            if hasattr(response, 'additional_kwargs') and 'grounding' in str(response.additional_kwargs):
                has_grounding = True
                logger.info("Grounding information detected in fallback response")
            
            logger.info(f"Fallback grounding enabled: {use_grounding}, Grounding detected: {has_grounding}")
            
        except Exception as fallback_error:
            logger.error(f"Fallback model also failed: {str(fallback_error)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    # Process tool/function calls from the response
    function_calls = []
    
    try:
        # Check for various tool/function call formats
        
        # 1. Check for OpenAI format tool_calls
        if hasattr(response, 'additional_kwargs') and response.additional_kwargs.get('tool_calls'):
            logger.info("Found tool_calls in OpenAI format")
            tool_calls = response.additional_kwargs.get('tool_calls', [])
            
            for tool_call in tool_calls:
                # Handle OpenAI-style tool call
                if isinstance(tool_call, dict) and 'function' in tool_call:
                    function_name = tool_call['function'].get('name')
                    
                    # Parse arguments
                    if 'arguments' in tool_call['function']:
                        args_str = tool_call['function'].get('arguments', '{}')
                        # Convert from string if needed
                        if isinstance(args_str, str):
                            try:
                                args = json.loads(args_str)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse function arguments for {function_name}: {args_str}")
                                logger.error(f"JSON error: {str(e)}")
                                # Try to salvage by cleaning the string
                                cleaned_args = args_str.replace("'", "\"").strip()
                                try:
                                    args = json.loads(cleaned_args)
                                    logger.info(f"Successfully parsed arguments after cleaning: {args}")
                                except json.JSONDecodeError:
                                    logger.error(f"Failed to parse arguments even after cleaning: {cleaned_args}")
                                    args = {}
                        else:
                            args = args_str
                            
                        function_calls.append({
                            "name": function_name,
                            "arguments": args
                        })
                        logger.info(f"Parsed OpenAI-format function call: {function_name}")
        
        # 2. Check for LangChain standard tool_calls attribute
        elif hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"Found tool_calls directly on response: {response.tool_calls}")
            
            for tool_call in response.tool_calls:
                # Skip Google Search grounding tool calls
                if tool_call.get("name") == "google_search":
                    logger.info(f"Found Google Search grounding call: {tool_call}")
                    continue
                
                function_calls.append({
                    "name": tool_call.get("name"),
                    "arguments": tool_call.get("args", {})
                })
                logger.info(f"Parsed LangChain tool call: {tool_call.get('name')}")
        
        # 3. Check legacy function_call format
        elif hasattr(response, 'additional_kwargs') and 'function_call' in response.additional_kwargs:
            function_call = response.additional_kwargs['function_call']
            function_name = function_call.get('name')
            args_str = function_call.get('arguments', '{}')
            
            try:
                if isinstance(args_str, str):
                    args = json.loads(args_str)
                else:
                    args = args_str
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse function arguments for {function_name}: {args_str}")
                logger.error(f"JSON error: {str(e)}")
                # Try to salvage by cleaning the string
                cleaned_args = args_str.replace("'", "\"").strip()
                try:
                    args = json.loads(cleaned_args)
                    logger.info(f"Successfully parsed arguments after cleaning: {args}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse arguments even after cleaning: {cleaned_args}")
                    args = {}
            
            function_calls.append({
                "name": function_name,
                "arguments": args
            })
            logger.info(f"Parsed legacy function call: {function_name}")
        
        # 4. Check for {type: 'function', function: {name, arguments}} format
        elif hasattr(response, 'content') and isinstance(response.content, str):
            try:
                # Log the full content for debugging
                logger.debug(f"Checking content for function calls: {response.content[:300]}...")
                
                # Try to parse content to see if it contains function calls in JSON format
                if '[' in response.content and ']' in response.content:
                    # Look for array of function calls in the content
                    
                    # More robust JSON pattern that matches arrays with objects
                    json_pattern = r'\[\s*\{(?:\s*"[^"]*"|\s*\'[^\']*\'|\s*[^{}"\',])*\}\s*\]'
                    match = re.search(json_pattern, response.content, re.DOTALL)
                    
                    if match:
                        logger.debug(f"Found potential JSON match: {match.group(0)}")
                        try:
                            content_json = json.loads(match.group(0))
                            logger.info(f"Found potential function calls array in content: {content_json}")
                            
                            if isinstance(content_json, list):
                                for item in content_json:
                                    logger.debug(f"Processing array item: {item}")
                                    if isinstance(item, dict) and 'type' in item and item['type'] == 'function' and 'function' in item:
                                        function_info = item['function']
                                        function_name = function_info.get('name', '')
                                        args_raw = function_info.get('arguments', {})
                                        
                                        logger.debug(f"Found function in content: {function_name} with args: {args_raw}")
                                        
                                        # Handle string arguments
                                        args = args_raw
                                        if isinstance(args_raw, str):
                                            try:
                                                args = json.loads(args_raw)
                                                logger.debug(f"Successfully parsed arguments as JSON: {args}")
                                            except json.JSONDecodeError:
                                                logger.error(f"Failed to parse function arguments for {function_name}: {args_raw}")
                                                # Try to clean up problematic characters
                                                clean_args = args_raw.replace("'", "\"").strip()
                                                try:
                                                    args = json.loads(clean_args)
                                                    logger.info(f"Successfully parsed arguments after cleaning: {args}")
                                                except json.JSONDecodeError:
                                                    logger.error(f"Failed to parse arguments even after cleaning: {clean_args}")
                                                    args = {}
                                        
                                        function_calls.append({
                                            "name": function_name,
                                            "arguments": args
                                        })
                                        logger.info(f"Parsed function call from content JSON: {function_name}")
                                        
                                        # Remove the JSON array from content to avoid double-processing
                                        response.content = response.content.replace(match.group(0), "").strip()
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSON array from content: {match.group(0)}, error: {str(e)}")
                            
                # Also try to extract function calls with a more explicit pattern
                function_pattern = r'\{\s*"type"\s*:\s*"function"\s*,\s*"function"\s*:\s*\{(?:\s*"[^"]*"|\s*\'[^\']*\'|\s*[^{}"\',])*\}\s*\}'
                matches = re.findall(function_pattern, response.content, re.DOTALL)
                
                if matches:
                    logger.debug(f"Found individual function matches: {matches}")
                    for match in matches:
                        try:
                            func_obj = json.loads(match)
                            if func_obj.get('type') == 'function' and 'function' in func_obj:
                                function_info = func_obj['function']
                                function_name = function_info.get('name', '')
                                args_raw = function_info.get('arguments', {})
                                
                                logger.debug(f"Found individual function: {function_name} with args: {args_raw}")
                                
                                # Handle string arguments
                                args = args_raw
                                if isinstance(args_raw, str):
                                    try:
                                        args = json.loads(args_raw)
                                    except json.JSONDecodeError:
                                        logger.error(f"Failed to parse function arguments for {function_name}: {args_raw}")
                                        # Try cleaning
                                        clean_args = args_raw.replace("'", "\"").strip()
                                        try:
                                            args = json.loads(clean_args)
                                        except json.JSONDecodeError:
                                            args = {}
                                
                                function_calls.append({
                                    "name": function_name,
                                    "arguments": args
                                })
                                logger.info(f"Parsed individual function call from content: {function_name}")
                                
                                # Remove the match from content
                                response.content = response.content.replace(match, "").strip()
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse individual function: {match}, error: {str(e)}")
            except Exception as e:
                logger.error(f"Error checking for function calls in content: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())

        # 5. Check for code blocks with function calls using a pattern like print(test(...))
        if not function_calls and "```" in response.content:
            logger.debug("Checking for function calls in code blocks")
            
            # Extract code blocks with better support for tool_code
            code_block_pattern = r"```(?:tool_code|python|json)?\n(.*?)```"
            code_blocks = re.findall(code_block_pattern, response.content, re.DOTALL)
            
            if code_blocks:
                logger.debug(f"Found {len(code_blocks)} code blocks: {code_blocks}")
                
                for code_block in code_blocks:
                    # Look for print(function_name(param1='value', param2=42)) pattern
                    print_func_pattern = r'print\(\s*(\w+)\s*\(([^)]*)\)\s*\)'
                    print_matches = re.findall(print_func_pattern, code_block, re.DOTALL)
                    
                    if print_matches:
                        logger.debug(f"Found print function calls: {print_matches}")
                        for function_match in print_matches:
                            function_name = function_match[0]
                            args_str = function_match[1].strip()
                            
                            logger.debug(f"Parsing function: {function_name} with args: {args_str}")
                            
                            # Extract key-value pairs from args string
                            # Pattern matches param1='value', param2=42
                            param_pattern = r"(\w+)\s*=\s*([^,]+)"
                            param_matches = re.findall(param_pattern, args_str)
                            
                            args_dict = {}
                            for param in param_matches:
                                param_name = param[0]
                                param_value = param[1].strip()
                                
                                # Handle string values (remove quotes)
                                if (param_value.startswith("'") and param_value.endswith("'")) or \
                                   (param_value.startswith('"') and param_value.endswith('"')):
                                    param_value = param_value[1:-1]
                                # Handle numbers
                                elif param_value.isdigit():
                                    param_value = int(param_value)
                                elif param_value.lower() == 'true':
                                    param_value = True
                                elif param_value.lower() == 'false':
                                    param_value = False
                                    
                                args_dict[param_name] = param_value
                            
                            logger.info(f"Extracted function call from code block: {function_name}({args_dict})")
                            function_calls.append({
                                "name": function_name,
                                "arguments": args_dict
                            })
                    
                    # Also look for direct function calls without print
                    direct_func_pattern = r'(\w+)\s*\(([^)]*)\)'
                    direct_matches = re.findall(direct_func_pattern, code_block, re.DOTALL)
                    
                    if direct_matches:
                        logger.debug(f"Found direct function calls: {direct_matches}")
                        for function_match in direct_matches:
                            function_name = function_match[0]
                            
                            # Skip if we already processed this via print() pattern
                            if any(call.get("name") == function_name for call in function_calls):
                                continue
                                
                            # Skip common Python functions that aren't API functions
                            if function_name in ['print', 'str', 'int', 'list', 'dict', 'set', 'tuple']:
                                continue
                            
                            args_str = function_match[1].strip()
                            
                            logger.debug(f"Parsing direct function: {function_name} with args: {args_str}")
                            
                            # Extract key-value pairs from args string
                            param_pattern = r"(\w+)\s*=\s*([^,]+)"
                            param_matches = re.findall(param_pattern, args_str)
                            
                            args_dict = {}
                            for param in param_matches:
                                param_name = param[0]
                                param_value = param[1].strip()
                                
                                # Handle string values (remove quotes)
                                if (param_value.startswith("'") and param_value.endswith("'")) or \
                                   (param_value.startswith('"') and param_value.endswith('"')):
                                    param_value = param_value[1:-1]
                                # Handle numbers
                                elif param_value.isdigit():
                                    param_value = int(param_value)
                                elif param_value.lower() == 'true':
                                    param_value = True
                                elif param_value.lower() == 'false':
                                    param_value = False
                                    
                                args_dict[param_name] = param_value
                            
                            logger.info(f"Extracted direct function call from code block: {function_name}({args_dict})")
                            function_calls.append({
                                "name": function_name,
                                "arguments": args_dict
                            })
    except Exception as parse_error:
        logger.error(f"Error parsing function calls: {str(parse_error)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Add function calls to response if we found any
    if function_calls:
        if not hasattr(response, 'additional_kwargs'):
            response.additional_kwargs = {}
        response.additional_kwargs['function_calls'] = function_calls
        logger.info(f"Added {len(function_calls)} function calls to response")
    
    return response

class LLMApp:
    """Simple LLM application class to replace LangGraph"""
    
    def __init__(self):
        self.conversations = {}
        
    async def ainvoke(self, state, config=None):
        """Process a message and return a response with potential function calls"""
        messages = state.get("messages", [])
        thread_id = config.get("configurable", {}).get("thread_id", "default") if config else "default"
        
        # Extract model options if provided in config
        options = config.get("configurable", {}).get("model_options", {}) if config else {}
        use_fallback = options.get("use_fallback", False)
        use_grounding = options.get("use_grounding", True)
        
        # Retrieve existing conversation or start a new one
        conversation = self.conversations.get(thread_id, [])
        
        # Add new messages to the conversation
        conversation.extend(messages)
        
        # Get response from LLM with specified options
        try:
            response = await call_llm(
                conversation, 
                use_fallback=use_fallback, 
                use_grounding=use_grounding
            )
            
            # Update the conversation with the response
            conversation.append(response)
            
            # Store updated conversation
            self.conversations[thread_id] = conversation
            
            # Return response
            return response
            
        except Exception as e:
            logger.error(f"Error in LLMApp.ainvoke: {str(e)}")
            # Return error as a message
            return AIMessage(content=f"I'm sorry, I encountered an error: {str(e)}")
    
    async def aget_state(self, config=None):
        """Get the current state of a conversation"""
        thread_id = config.get("configurable", {}).get("thread_id", "default") if config else "default"
        conversation = self.conversations.get(thread_id, [])
        return [{"messages": conversation}]

async def create_llm_app(app):
    """Initialize a simple LLM application
    
    Args:
        app: FastAPI application instance
    """
    logger.info("Initializing LLM application")
    
    # Create a new LLMApp instance
    llm_app = LLMApp()
    
    # Store the initialized app in application state
    app.state.llmapp = llm_app
    
    logger.info("LLM application initialized successfully")
    return llm_app

@backoff.on_exception(
    backoff.expo,
    (aiohttp.ClientError, asyncio.TimeoutError),
    max_tries=3,
    max_time=30
)
async def generate_learning_insights(user: User, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Generate enhanced learning insights using the Gemini API
    
    Args:
        user: User object
        data: Dictionary containing user learning analytics data
        
    Returns:
        Dict containing AI-generated learning insights or None if generation fails
    """
    if not GEMINI_API_KEY:
        logger.warning("Gemini API key not configured, skipping enhanced insights generation")
        return None
    
    try:
        # Format the prompt with user data
        prompt = INSIGHT_PROMPT_TEMPLATE.format(
            name=user.name or "Student",
            email=user.email,
            data=json.dumps(data, default=str)
        )
        
        # Create request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json"
            }
        }
        
        # Send request to Gemini API
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            ) as response:
                # Check for successful response
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Gemini API error: {response.status}, {error_text}")
                    return None
                
                # Parse the response
                response_data = await response.json()
                
                # Extract the content from the response
                if "candidates" in response_data and response_data["candidates"]:
                    candidate = response_data["candidates"][0]
                    if "content" in candidate and candidate["content"]["parts"]:
                        # Extract the JSON text from the response
                        result_text = candidate["content"]["parts"][0]["text"]
                        
                        # Try to parse the JSON (clean it if necessary)
                        try:
                            # Clean up the text to extract just the JSON part
                            json_text = result_text.strip()
                            if json_text.startswith("```json"):
                                json_text = json_text.split("```json", 1)[1]
                            if "```" in json_text:
                                json_text = json_text.split("```", 1)[0]
                            
                            json_text = json_text.strip()
                            insights = json.loads(json_text)
                            
                            # Validate the response format
                            if not all(key in insights for key in ["studyPatterns", "suggestions", "opportunities"]):
                                logger.warning("Gemini response missing required fields")
                                return None
                            
                            logger.info(f"Successfully generated enhanced learning insights for user {user.id}")
                            return insights
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON from Gemini response: {e}")
                            logger.debug(f"Raw response text: {result_text}")
                            return None
                
                logger.warning("Unexpected Gemini API response format")
                return None
                
    except Exception as e:
        logger.error(f"Error generating insights with Gemini: {str(e)}")
        return None

# Additional LLM utility functions can be added here
async def summarize_lecture_text(text: str, max_length: int = 1000) -> Optional[str]:
    """
    Summarize lecture text using Gemini API (placeholder for implementation)
    """
    # Implementation would be similar to generate_learning_insights but with different prompt
    pass

async def generate_quiz_questions(topic: str, difficulty: str, count: int = 5) -> Optional[List[Dict[str, Any]]]:
    """
    Generate quiz questions for a given topic using Gemini API (placeholder for implementation)
    """
    # Implementation would be similar to generate_learning_insights but with different prompt
    pass
