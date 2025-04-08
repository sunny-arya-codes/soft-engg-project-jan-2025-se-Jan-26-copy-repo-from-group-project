#!/usr/bin/env python3
"""
Direct test for function calling with Google Gemini, minimal dependencies.
This script bypasses most of the application infrastructure to test the core function calling.
"""

import os
import json
import asyncio
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("direct_test")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY environment variable not set")
    exit(1)

# Import necessary Google APIs directly
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)

# Define a simple test function
def test_function(param1: str = "default", param2: int = 0):
    """A simple test function that returns its parameters"""
    logger.info(f"test_function called with param1={param1}, param2={param2}")
    return {
        "param1": param1,
        "param2": param2,
        "status": "success"
    }

# Function declaration for Gemini
test_function_declaration = FunctionDeclaration(
    name="test_function",
    description="A simple test function that returns its parameters",
    parameters={
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "A string parameter"
            },
            "param2": {
                "type": "integer",
                "description": "An integer parameter"
            }
        }
    }
)

# Create a Tool from the function declaration
test_tool = Tool(
    function_declarations=[test_function_declaration]
)

async def test_direct_function_calling():
    """Test function calling directly with the Google API"""
    logger.info("Testing direct function calling with Google Gemini API...")
    
    # List available models
    try:
        models = genai.list_models()
        model_names = [model.name for model in models if 'gemini' in model.name]
        logger.info(f"Available Gemini models: {model_names}")
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        model_names = ["gemini-1.5-flash", "gemini-1.0-pro"]
    
    # Choose the model - match the same priority as in llm_service.py
    models_to_try = [
        # 2.5 preview first
        "gemini-2.5-pro-preview",
        "gemini-2.5-pro-exp",
        
        # Then 2.0 flash
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp",
        
        # Fallbacks
        "gemini-1.5-pro", 
        "gemini-1.5-flash"
    ]
    
    # Find first available model
    model_name = None
    for m in models_to_try:
        # The API returns names with 'models/' prefix, so check if our model name is in the API model name
        matching_models = [name for name in model_names if m in name.replace('models/', '')]
        if matching_models:
            # Use the first match
            model_name = matching_models[0].replace('models/', '')
            logger.info(f"Found matching model for {m}: {model_name}")
            break
    
    if not model_name:
        model_name = "gemini-1.0-pro"  # Fallback
        logger.info(f"No matching models found, using fallback: {model_name}")
    
    logger.info(f"Using model: {model_name}")
    
    # Initialize the model with tools
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config={"temperature": 0.0},
        tools=[test_tool]
    )
    
    # Create a chat session - note that tools are specified when creating the model, not the chat
    chat = model.start_chat()
    
    # Send a message to trigger function calling
    try:
        logger.info("Sending test message to chat...")
        response = chat.send_message("Please call the test_function with param1='hello' and param2=42.")
        
        # Log the response - safely access text
        try:
            response_text = str(response)
            logger.info(f"Response received (type: {type(response)})")
            logger.info(f"Response content: {response_text[:200]}...")  # First 200 chars
        except Exception as e:
            logger.warning(f"Unable to get response text: {e}")
        
        # Check for function calls
        if hasattr(response, 'candidates') and response.candidates:
            logger.info(f"Found {len(response.candidates)} candidates")
            for i, candidate in enumerate(response.candidates):
                logger.info(f"Examining candidate {i+1}")
                
                if hasattr(candidate, 'content') and candidate.content:
                    logger.info("Candidate has content")
                    
                    # Check for function calls in parts
                    if hasattr(candidate.content, 'parts'):
                        logger.info(f"Content has {len(candidate.content.parts)} parts")
                        
                        for part_index, part in enumerate(candidate.content.parts):
                            logger.info(f"Examining part {part_index+1}")
                            
                            # Check for function_call attribute first
                            if hasattr(part, 'function_call'):
                                function_call = part.function_call
                                logger.info(f"Found function call: {function_call.name}")
                                logger.info(f"Arguments: {function_call.args}")
                                
                                # Execute the function
                                if function_call.name == "test_function":
                                    args = function_call.args
                                    result = test_function(**args)
                                    logger.info(f"Function result: {result}")
                                    
                                    # Try to send the function result back to the model if supported
                                    try:
                                        # Check documentation for the correct way to return function results
                                        # Current API might not support this directly
                                        
                                        # Method 1: Try with function_response parameter
                                        try:
                                            followup = chat.send_message(
                                                f"The function returned: {json.dumps(result)}",
                                            )
                                            logger.info("Successfully sent function result as regular message")
                                        except Exception as e1:
                                            logger.warning(f"Method 1 failed: {e1}")
                                            
                                            # Method 2: Try with different parameter names
                                            try:
                                                # This is just for testing different possible parameter names
                                                # If none work, we'll just log it
                                                followup = chat.send_message(
                                                    f"Function {function_call.name} was called and returned: {json.dumps(result)}"
                                                )
                                                logger.info("Sent function result as text message instead")
                                            except Exception as e2:
                                                logger.warning(f"Method 2 failed: {e2}")
                                        
                                        # Get followup safely
                                        if 'followup' in locals():
                                            try:
                                                followup_text = str(followup)
                                                logger.info(f"Model response after function result: {followup_text[:200]}...")
                                            except Exception as e:
                                                logger.warning(f"Unable to get followup text: {e}")
                                    except Exception as e:
                                        logger.warning(f"Could not send function result back to model: {e}")
                                        logger.info("Function execution succeeded even though result couldn't be sent back to model")
                            # For protocol buffer objects, they might use WhichOneof instead
                            elif hasattr(part, '_pb'):
                                try:
                                    which_field = part._pb.WhichOneof("data")
                                    logger.info(f"Part contains field type: {which_field}")
                                    if which_field == "function_call":
                                        function_call = part._pb.function_call
                                        logger.info(f"Found function call via pb: {function_call.name}")
                                        
                                        # Handle args parsing
                                        args = {}
                                        if hasattr(function_call, 'args') and function_call.args:
                                            try:
                                                args = json.loads(function_call.args)
                                            except:
                                                logger.error(f"Failed to parse args: {function_call.args}")
                                                
                                        logger.info(f"Arguments: {args}")
                                        
                                        # Execute the function
                                        if function_call.name == "test_function":
                                            result = test_function(**args)
                                            logger.info(f"Function result: {result}")
                                            
                                            # Try to send the function result back to the model if supported
                                            try:
                                                # Check documentation for the correct way to return function results
                                                # Current API might not support this directly
                                                
                                                # Method 1: Try with function_response parameter
                                                try:
                                                    followup = chat.send_message(
                                                        f"The function returned: {json.dumps(result)}",
                                                    )
                                                    logger.info("Successfully sent function result as regular message")
                                                except Exception as e1:
                                                    logger.warning(f"Method 1 failed: {e1}")
                                                    
                                                    # Method 2: Try with different parameter names
                                                    try:
                                                        # This is just for testing different possible parameter names
                                                        # If none work, we'll just log it
                                                        followup = chat.send_message(
                                                            f"Function {function_call.name} was called and returned: {json.dumps(result)}"
                                                        )
                                                        logger.info("Sent function result as text message instead")
                                                    except Exception as e2:
                                                        logger.warning(f"Method 2 failed: {e2}")
                                                
                                                # Get followup safely
                                                if 'followup' in locals():
                                                    try:
                                                        followup_text = str(followup)
                                                        logger.info(f"Model response after function result: {followup_text[:200]}...")
                                                    except Exception as e:
                                                        logger.warning(f"Unable to get followup text: {e}")
                                            except Exception as e:
                                                logger.warning(f"Could not send function result back to model: {e}")
                                                logger.info("Function execution succeeded even though result couldn't be sent back to model")
                                except AttributeError as e:
                                    logger.warning(f"AttributeError accessing protocol buffer: {e}")
                            else:
                                # Try to inspect the part's content
                                logger.info(f"Part type: {type(part)}")
                                try:
                                    part_content = str(part)[:100]
                                    logger.info(f"Part content: {part_content}...")
                                except:
                                    logger.info("Could not string-convert part")
                                    
                    # If no function call found in parts structure, check for our regex patterns
                    if response_text and ("function_call" in response_text or "test_function" in response_text):
                        logger.info("Response may contain function call in text - attempting extraction")
                        
                        # Regular expression patterns to try
                        patterns = [
                            r'test_function\(.*?param1=[\'"]?(.*?)[\'"]?,.*?param2=(\d+)',
                            r'test_function\(.*?\{.*?[\'"]?param1[\'"]?\s*:\s*[\'"]?(.*?)[\'"]?,.*?[\'"]?param2[\'"]?\s*:\s*(\d+)',
                            r'(?:function|tool)_call.*?\{.*?name.*?[\'"]?test_function[\'"]?.*?\}'
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, response_text, re.DOTALL)
                            if match:
                                logger.info(f"Extracted function call with pattern: {pattern}")
                                if len(match.groups()) >= 2:
                                    param1 = match.group(1)
                                    param2 = int(match.group(2))
                                    logger.info(f"Extracted params: param1={param1}, param2={param2}")
                                    
                                    # Execute the function with extracted params
                                    result = test_function(param1=param1, param2=param2)
                                    logger.info(f"Function result: {result}")
                                break
        
    except Exception as e:
        logger.error(f"Error calling model: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting direct function calling test")
    asyncio.run(test_direct_function_calling())
    logger.info("Test completed") 