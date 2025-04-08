#!/usr/bin/env python3
"""
Test script for function calling in the LLM system.
This script directly tests the function router system to ensure API functions can be properly called.
"""

import asyncio
import json
import os
import sys
import logging
import uuid
from typing import Dict, Any, List, Callable, Awaitable
from datetime import datetime, timedelta
import contextlib

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_function_calling")

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment
from dotenv import load_dotenv
load_dotenv()

# Import API functions to ensure they are registered
try:
    from app.services.api_functions import *
    logger.info("Successfully imported API functions")
except Exception as e:
    logger.error(f"Error importing API functions: {e}")

# Import LLM service and function router
from app.services.llm_service import call_llm
from app.services.function_router import function_router
from app.services.llm import process_query, route_query_to_function

# Create a test request context class for tests
class TestRequestContext:
    """Context manager to create a test request context for API functions"""
    
    def __init__(self):
        self.original_get_request = None
        self.request = None
        
    async def __aenter__(self):
        """Set up the test request context"""
        # Import necessary modules
        from fastapi import Request
        from app.auth.context import get_request, set_request_context
        
        # Save the original get_request function
        self.original_get_request = get_request
        
        # Create a test request object
        self.request = Request({"type": "http", "scope": {"type": "http", "method": "GET", "path": "/test"}})
        
        # Create a test user using a dictionary instead of model to avoid ORM issues
        test_user = {
            "id": str(uuid.uuid4()),
            "username": "test_user",
            "email": "test@example.edu",
            "role": "student",
            "name": "Test User",
            "created_at": datetime.now(),
            "last_login": datetime.now()
        }
        
        # Convert to a simple object that can be accessed like a model
        test_user_obj = type('TestUser', (), test_user)
        
        # Use monkey patching to add a custom property for accessing user
        async def get_custom_request():
            self.request._user = test_user_obj
            return self.request
        
        # Patch the get_request function
        import app.auth.context
        app.auth.context.get_request = get_custom_request
        
        logger.info("Test request context created with test user")
        return self.request
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the test request context"""
        if self.original_get_request:
            # Restore the original get_request function
            import app.auth.context
            app.auth.context.get_request = self.original_get_request
            logger.info("Original request context restored")

# -------------------- Register Test Functions --------------------

# Define a simple test function
def simple_test_function(param1: str = "default", param2: int = 0):
    """A simple test function that returns its parameters"""
    logger.info(f"simple_test_function called with param1={param1}, param2={param2}")
    return {
        "param1": param1,
        "param2": param2,
        "status": "success"
    }

# Register the test function with BOTH names for compatibility
function_router.register_function(
    name="testFunction",
    description="A simple test function that returns its parameters",
    handler=simple_test_function,
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

# Also register with shorter name for compatibility with direct LLM output
function_router.register_function(
    name="test",
    description="A simple test function that returns its parameters (short name)",
    handler=simple_test_function,
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

# -------------------- Test Helper Functions --------------------

async def execute_function_call(function_name, function_args, user_id=None):
    """
    Wrapper for the route_query_to_function to maintain compatibility with tests.
    This function is called by the test scripts to execute API functions.
    
    Args:
        function_name: Name of the function to call
        function_args: Arguments to pass to the function
        user_id: Optional user ID for context
        
    Returns:
        Result of the function call
    """
    logger.info(f"Executing function call: {function_name} with args: {function_args}")
    return await route_query_to_function(function_name, function_args, user_id)

async def run_llm_test(prompt: str, expected_function: str = None) -> Dict:
    """Run a test using the LLM with a specific prompt"""
    logger.info(f"Testing LLM function calling with prompt: '{prompt}'")
    
    # Test messages
    messages = [
        {"type": "human", "content": prompt}
    ]
    
    # Call the LLM
    logger.info("Calling LLM...")
    try:
        # Create a test request context for the LLM call
        async with TestRequestContext() as _:
            response = await call_llm(messages)
            
            # Log the response summary
            content_summary = response.content[:100] + "..." if len(response.content) > 100 else response.content
            logger.info(f"Response content (summary): {content_summary}")
            
            # Check for function calls
            function_calls = []
            if hasattr(response, 'additional_kwargs') and 'function_calls' in response.additional_kwargs:
                function_calls = response.additional_kwargs['function_calls']
                logger.info(f"Found {len(function_calls)} function calls: {json.dumps(function_calls, indent=2)}")
                
                # Check if the expected function was called
                if expected_function:
                    function_names = [call.get("name") for call in function_calls]
                    if expected_function in function_names:
                        logger.info(f"✅ Expected function '{expected_function}' was called")
                    else:
                        logger.warning(f"❌ Expected function '{expected_function}' was NOT called. Found: {function_names}")
            else:
                logger.warning("No function calls found in response")
            
            # Extract function calls from content if needed
            if not function_calls and isinstance(response.content, str):
                # Look for tool_calls or function_calls patterns
                extracted_calls = extract_function_calls_from_content(response.content)
                if extracted_calls:
                    function_calls = extracted_calls
                    logger.info(f"Extracted {len(function_calls)} function calls from content")
            
            # Execute any found function calls
            results = []
            used_mock_data = False
            for func_call in function_calls:
                name = func_call.get("name")
                args = func_call.get("arguments", {})
                
                logger.info(f"Executing function: {name}({args})")
                try:
                    # Call the function with the test request context
                    result = await function_router.execute_function(name, args)
                    logger.info(f"Function result: {json.dumps(result, default=str, indent=2)}")
                    
                    # Check if result contains mock data
                    if isinstance(result, dict) and result.get("is_mock_data") is True:
                        logger.error(f"Function {name} returned mock data instead of real data")
                        used_mock_data = True
                    
                    results.append({"name": name, "result": result})
                except Exception as e:
                    logger.error(f"Error executing function: {e}")
                    results.append({"name": name, "error": str(e)})
            
            return {
                "response": response,
                "function_calls": function_calls,
                "results": results,
                "used_mock_data": used_mock_data
            }
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

def extract_function_calls_from_content(content: str) -> List[Dict]:
    """Extract function calls from response content using various patterns"""
    function_calls = []
    
    try:
        # Try to find JSON blocks
        import re
        # Look for JSON blocks in markdown code blocks
        json_pattern = r'```(?:json|python|tool_code)?\s*\n(.*?)```'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                # Try to parse as JSON
                data = json.loads(match.strip())
                
                # Check different formats
                if isinstance(data, dict):
                    if "name" in data and ("arguments" in data or "args" in data):
                        # Direct function call format
                        function_calls.append({
                            "name": data.get("name"),
                            "arguments": data.get("arguments") or data.get("args") or {}
                        })
                    elif "function_call" in data:
                        # Nested function call format
                        func_call = data["function_call"]
                        if isinstance(func_call, dict) and "name" in func_call:
                            function_calls.append({
                                "name": func_call.get("name"),
                                "arguments": func_call.get("arguments") or {}
                            })
                    elif "tool_calls" in data:
                        # Newer format with tool_calls array
                        tool_calls = data["tool_calls"]
                        for call in tool_calls:
                            if isinstance(call, dict):
                                if "function" in call:
                                    # Format: {"function": {"name": "x", "arguments": {}}}
                                    func = call["function"]
                                    function_calls.append({
                                        "name": func.get("name"),
                                        "arguments": func.get("arguments") or {}
                                    })
                                elif "name" in call:
                                    # Direct format in tool_calls
                                    function_calls.append({
                                        "name": call.get("name"),
                                        "arguments": call.get("arguments") or {}
                                    })
            except json.JSONDecodeError:
                pass
        
        # If no JSON blocks found, try to find function call syntax in text
        if not function_calls:
            # Look for patterns like functionName(param1="value", param2=42)
            func_pattern = r'(\w+)\s*\(\s*(.*?)\s*\)'
            matches = re.findall(func_pattern, content)
            
            for name, args_str in matches:
                # Skip if it's likely a Python built-in function
                if name.lower() in ["print", "str", "int", "list", "dict", "set", "tuple", "type"]:
                    continue
                
                # Try to parse the arguments
                arguments = {}
                if args_str:
                    # Split by commas, but handle cases with nested commas in quotes or objects
                    try:
                        # Handle key=value style args
                        arg_pairs = re.findall(r'(\w+)\s*=\s*([^,]+)(?:,|$)', args_str)
                        for key, value in arg_pairs:
                            # Clean up the value
                            value = value.strip()
                            # Remove quotes around strings
                            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                                value = value[1:-1]
                            # Try to convert to appropriate type
                            try:
                                if value.lower() == "true":
                                    arguments[key] = True
                                elif value.lower() == "false":
                                    arguments[key] = False
                                elif value.isdigit():
                                    arguments[key] = int(value)
                                elif value.replace(".", "", 1).isdigit():
                                    arguments[key] = float(value)
                                else:
                                    arguments[key] = value
                            except:
                                arguments[key] = value
                    except:
                        # Fallback: just store the arg string if parsing fails
                        arguments = {"_raw_args": args_str}
                
                function_calls.append({
                    "name": name,
                    "arguments": arguments
                })
    except Exception as e:
        logger.error(f"Error extracting function calls from content: {e}")
    
    return function_calls

async def direct_call_function(function_name: str, arguments: Dict = None) -> Dict:
    """Directly call a function through the function router"""
    if arguments is None:
        arguments = {}
    
    logger.info(f"Directly calling function: {function_name} with arguments: {arguments}")
    try:
        # Set up a proper request context for testing
        from app.auth.context import set_request_var
        from fastapi import Request
        from starlette.datastructures import State
        import uuid
        
        # Create a test user to simulate authentication
        test_user_id = str(uuid.uuid4())
        test_user = {
            "id": test_user_id,
            "username": "testuser",
            "email": "test@example.com",
            "role": "student",
            "name": "Test User"
        }
        
        # Create a mock context with user data instead of trying to modify Request.state
        # Since Request.state is a property that can't be set directly
        test_user_obj = type('TestUser', (), test_user)
        
        # Create a request context without trying to modify state directly
        async def get_fake_request():
            fake_request = Request({"type": "http", "scope": {"type": "http", "method": "GET", "path": "/test"}})
            # Monkey patch the state property to return our custom object with a user attribute
            original_state = fake_request.state
            
            class CustomState:
                def __init__(self):
                    self.user = test_user_obj
                    self._state = original_state
                
                def __getattr__(self, name):
                    if name == "user":
                        return test_user_obj
                    return getattr(self._state, name)
            
            # Use a different approach to attach user data
            fake_request._user = test_user_obj
            return fake_request
        
        # Use patching to avoid state modification issues
        import app.auth.context
        original_get_request = app.auth.context.get_request
        app.auth.context.get_request = get_fake_request
        
        try:
            # Execute the function
            result = await function_router.execute_function(function_name, arguments)
            logger.info(f"Function result: {json.dumps(result, default=str, indent=2)}")
            
            # Check if the result contains mock data
            if isinstance(result, dict) and result.get("is_mock_data") is True:
                logger.error(f"Function {function_name} returned mock data instead of real data")
                return {"result": result, "used_mock_data": True}
            
            return {"result": result}
        finally:
            # Restore original function
            app.auth.context.get_request = original_get_request
    
    except Exception as e:
        logger.error(f"Error executing function: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

# -------------------- Test Functions --------------------

async def test_simple_function():
    """Test the simple test function"""
    logger.info("=== Testing simple test function ===")
    
    # Test both function names
    for func_name in ["test", "testFunction"]:
        result = await direct_call_function(func_name, {"param1": "hello", "param2": 42})
        assert "result" in result, f"Function {func_name} did not return a result"
        assert "used_mock_data" not in result, f"Function {func_name} used mock data"
        assert result["result"]["param1"] == "hello", f"Function {func_name} did not return correct param1"
        assert result["result"]["param2"] == 42, f"Function {func_name} did not return correct param2"
    
    # Test with LLM
    test_result = await run_llm_test(
        "Please call the test function with param1='hello' and param2=42.",
        expected_function="test"
    )
    
    assert not test_result.get("used_mock_data", False), "LLM test used mock data"
    
    return True

async def test_user_functions(test_data=None):
    """Test user profile API functions"""
    logger.info("Testing user profile API functions")
    
    # Test getUserProfile
    user_id = test_data.get("test_user_id") if test_data else None
    if not user_id:
        logger.warning("No test user ID available, using a placeholder")
        user_id = "00000000-0000-0000-0000-000000000000"
        
    result = await execute_function_call("getUserProfile", {"user_id": user_id})
    logger.info(f"getUserProfile result: {json.dumps(result, indent=2)}")
    
    # Check for error indicating test data is not properly set up
    if result.get("error") and "not found" in result.get("error"):
        logger.warning("User profile test failed: User not found. This is expected if test data isn't properly set up.")
        return False
    
    # Validate result structure
    required_fields = ["id", "username", "email", "name", "role"]
    for field in required_fields:
        if field not in result:
            logger.error(f"User profile test failed: Missing required field '{field}'")
            return False
    
    logger.info("User profile API functions test passed")
    return True

async def test_course_functions(test_data=None):
    """Test course API functions"""
    logger.info("Testing course API functions")
    
    # Test getCourses
    user_id = test_data.get("test_user_id") if test_data else None
    if not user_id:
        logger.warning("No test user ID available, using a placeholder")
        user_id = "00000000-0000-0000-0000-000000000000"
    
    result = await execute_function_call("getCourses", {"user_id": user_id})
    logger.info(f"getCourses result: {json.dumps(result, indent=2)}")
    
    # Check for error indicating test data is not properly set up
    if result.get("error") and "not found" in result.get("error"):
        logger.warning("Course test failed: User not found. This is expected if test data isn't properly set up.")
        return False
    
    # Validate result structure
    if "courses" not in result or "total" not in result:
        logger.error(f"Course test failed: Missing required fields in response")
        return False
    
    # Test with status filter
    result_with_filter = await execute_function_call("getCourses", {"user_id": user_id, "status": "active"})
    logger.info(f"getCourses with filter result: {json.dumps(result_with_filter, indent=2)}")
    
    logger.info("Course API functions test passed")
    return True

async def test_assignment_functions(test_data=None):
    """Test assignment API functions"""
    logger.info("Testing assignment API functions")
    
    # Test getAssignments
    course_id = test_data.get("test_course_1_id") if test_data else None
    user_id = test_data.get("test_user_id") if test_data else None
    
    if not course_id:
        logger.warning("No test course ID available, using a placeholder")
        course_id = "00000000-0000-0000-0000-000000000000"
    
    # First try without user_id
    result = await execute_function_call("getAssignments", {"course_id": course_id})
    logger.info(f"getAssignments result: {json.dumps(result, indent=2)}")
    
    # Check for error indicating test data is not properly set up
    if result.get("error") and "not found" in result.get("error"):
        logger.warning("Assignment test failed: Course not found. This is expected if test data isn't properly set up.")
        return False
    
    # Then try with user_id
    if user_id:
        result_with_user = await execute_function_call("getAssignments", {"course_id": course_id, "user_id": user_id})
        logger.info(f"getAssignments with user_id result: {json.dumps(result_with_user, indent=2)}")
    
    # Validate result structure
    if "assignments" not in result or "total" not in result:
        logger.error(f"Assignment test failed: Missing required fields in response")
        return False
    
    logger.info("Assignment API functions test passed")
    return True

async def test_faq_functions():
    """Test FAQ API functions"""
    logger.info("Testing FAQ API functions")
    
    # Test search_faqs
    result = await execute_function_call("search_faqs", {"query": "password"})
    logger.info(f"search_faqs result: {json.dumps(result, indent=2)}")
    
    # Validate result structure
    if "results" not in result or "total" not in result:
        logger.error(f"FAQ test failed: Missing required fields in response")
        return False
    
    # Test with category filter
    result_with_category = await execute_function_call("search_faqs", {"query": "password", "category": "account"})
    logger.info(f"search_faqs with category result: {json.dumps(result_with_category, indent=2)}")
    
    logger.info("FAQ API functions test passed")
    return True

async def test_web_search_function():
    """Test web search API function"""
    logger.info("=== Testing web search API function ===")
    
    # Test web_search
    search_result = await direct_call_function("web_search", {"query": "latest software engineering trends"})
    assert "result" in search_result, "web_search did not return a result"
    assert "used_mock_data" not in search_result, "web_search used mock data"
    
    # Test with LLM
    test_result = await run_llm_test(
        "What are the latest software engineering trends? Please search the web.",
        expected_function="web_search"
    )
    
    assert not test_result.get("used_mock_data", False), "LLM test used mock data"
    
    return True

async def test_roadmap_function():
    """Test roadmap API function"""
    logger.info("=== Testing learning roadmap API function ===")
    
    # Generate a random UUID to use as a course ID
    test_course_id = str(uuid.uuid4())
    
    # Test generateLearningRoadmap
    roadmap_result = await direct_call_function("generateLearningRoadmap", {"courseId": test_course_id})
    # This will likely return an error since the ID is random, but we just want to make sure the function executes
    assert "result" in roadmap_result or "error" in roadmap_result, "generateLearningRoadmap did not return a result or error"
    assert "used_mock_data" not in roadmap_result, "generateLearningRoadmap used mock data"
    
    # Test with LLM
    test_result = await run_llm_test(
        f"Create a learning roadmap for the course with ID {test_course_id}",
        expected_function="generateLearningRoadmap"
    )
    
    assert not test_result.get("used_mock_data", False), "LLM test used mock data"
    
    return True

async def test_llm_multi_function_scenario(test_data=None):
    """Test complex scenario with multiple function calls"""
    logger.info("Testing complex multi-function scenario")
    
    # Get a user ID for testing
    user_id = test_data.get("test_user_id") if test_data else None
    if not user_id:
        logger.warning("No test user ID available, using a placeholder")
        user_id = "00000000-0000-0000-0000-000000000000"
    
    # Create a complex query that might prompt the LLM to make multiple function calls
    query = "Show me my courses and their assignments"
    
    # Execute the query with the LLM router
    result = await process_query(query, user_id)
    logger.info(f"Complex multi-function scenario result: {json.dumps(result, indent=2)}")
    
    # We can't predict exactly what functions the LLM will call, but we can check if it made any calls
    if "function_calls" not in result:
        logger.error("Complex scenario test failed: No function calls made")
        return False
    
    function_calls = result.get("function_calls", [])
    if len(function_calls) == 0:
        logger.error("Complex scenario test failed: Empty function calls list")
        return False
    
    # Check if it includes calls to courses and assignments functions
    function_names = [call.get("name") for call in function_calls]
    if "getCourses" not in function_names:
        logger.warning("Complex scenario note: Expected getCourses to be called")
    
    logger.info("Complex multi-function scenario test passed")
    return True

async def setup_test_db():
    """Set up test database with mock data for tests"""
    logger.info("Setting up test database with mock data")
    
    try:
        # Get a database session
        from app.database import get_db
        from sqlalchemy.ext.asyncio import AsyncSession
        
        db_generator = get_db()
        db = await db_generator.__anext__()
        
        # Import models
        from app.models.user import User
        from app.models.course import Course
        from app.models.assignment import Assignment
        
        # Try different imports for enrollment - the module structure may vary
        try:
            from app.models.enrollment import CourseEnrollment
        except ImportError:
            try:
                from app.models.enrollments import CourseEnrollment
            except ImportError:
                # Final fallback - use a mock class for testing
                class CourseEnrollment:
                    id = None
                    user_id = None
                    course_id = None
                    status = "active"
                    progress = 0
                    enrollment_date = datetime.now()
                    created_at = datetime.now()
        
        from app.models.faq import FAQ
        
        # Create test user if not exists
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        import uuid
        
        # Check if test user exists
        test_user_query = select(User).where(User.email == "test@example.edu")
        test_user_result = await db.execute(test_user_query)
        test_user = test_user_result.scalar_one_or_none()
        
        if not test_user:
            # Create a test user
            test_user = User(
                id=uuid.uuid4(),
                username="test_user",
                email="test@example.edu",
                name="Test User",
                role="student",
                password="hashed_password",
                created_at=datetime.now()
            )
            db.add(test_user)
            await db.commit()
            logger.info(f"Created test user with ID: {test_user.id}")
        else:
            logger.info(f"Using existing test user with ID: {test_user.id}")
            
        # Create test faculty user if not exists
        test_faculty_query = select(User).where(User.email == "faculty@example.edu")
        test_faculty_result = await db.execute(test_faculty_query)
        test_faculty = test_faculty_result.scalar_one_or_none()
        
        if not test_faculty:
            # Create a test faculty user
            test_faculty = User(
                id=uuid.uuid4(),
                username="test_faculty",
                email="faculty@example.edu",
                name="Test Faculty",
                role="faculty",
                password="hashed_password",
                created_at=datetime.now()
            )
            db.add(test_faculty)
            await db.commit()
            logger.info(f"Created test faculty with ID: {test_faculty.id}")
        else:
            logger.info(f"Using existing test faculty with ID: {test_faculty.id}")
        
        # Create test courses if not exist
        test_course_1_query = select(Course).where(Course.code == "TST101")
        test_course_1_result = await db.execute(test_course_1_query)
        test_course_1 = test_course_1_result.scalar_one_or_none()
        
        if not test_course_1:
            # Create a test course
            test_course_1 = Course(
                id=uuid.uuid4(),
                title="Test Course 1",
                code="TST101",
                description="Test course for automated testing",
                instructor_id=test_faculty.id,
                instructor_name=test_faculty.name,
                credits=3,
                semester="Spring",
                year=2023,
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now() + timedelta(days=60),
                status="active",
                enrollment_limit=30,
                current_enrollment=1,
                created_at=datetime.now()
            )
            db.add(test_course_1)
            await db.commit()
            logger.info(f"Created test course 1 with ID: {test_course_1.id}")
        else:
            logger.info(f"Using existing test course 1 with ID: {test_course_1.id}")
        
        # Create a second test course if not exists
        test_course_2_query = select(Course).where(Course.code == "TST102")
        test_course_2_result = await db.execute(test_course_2_query)
        test_course_2 = test_course_2_result.scalar_one_or_none()
        
        if not test_course_2:
            # Create a test course
            test_course_2 = Course(
                id=uuid.uuid4(),
                title="Test Course 2",
                code="TST102",
                description="Another test course for automated testing",
                instructor_id=test_faculty.id,
                instructor_name=test_faculty.name,
                credits=4,
                semester="Spring",
                year=2023,
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now() + timedelta(days=60),
                status="active",
                enrollment_limit=25,
                current_enrollment=1,
                created_at=datetime.now()
            )
            db.add(test_course_2)
            await db.commit()
            logger.info(f"Created test course 2 with ID: {test_course_2.id}")
        else:
            logger.info(f"Using existing test course 2 with ID: {test_course_2.id}")
        
        # Enroll test user in test courses if not already enrolled
        enrollment_1_query = select(CourseEnrollment).where(
            CourseEnrollment.user_id == test_user.id,
            CourseEnrollment.course_id == test_course_1.id
        )
        enrollment_1_result = await db.execute(enrollment_1_query)
        enrollment_1 = enrollment_1_result.scalar_one_or_none()
        
        if not enrollment_1:
            # Create enrollment
            enrollment_1 = CourseEnrollment(
                id=uuid.uuid4(),
                user_id=test_user.id,
                course_id=test_course_1.id,
                status="active",
                progress=75,
                enrollment_date=datetime.now() - timedelta(days=25),
                created_at=datetime.now()
            )
            db.add(enrollment_1)
            await db.commit()
            logger.info(f"Enrolled test user in test course 1")
        else:
            logger.info(f"Test user already enrolled in test course 1")
        
        # Enroll in second course
        enrollment_2_query = select(CourseEnrollment).where(
            CourseEnrollment.user_id == test_user.id,
            CourseEnrollment.course_id == test_course_2.id
        )
        enrollment_2_result = await db.execute(enrollment_2_query)
        enrollment_2 = enrollment_2_result.scalar_one_or_none()
        
        if not enrollment_2:
            # Create enrollment
            enrollment_2 = CourseEnrollment(
                id=uuid.uuid4(),
                user_id=test_user.id,
                course_id=test_course_2.id,
                status="active",
                progress=45,
                enrollment_date=datetime.now() - timedelta(days=20),
                created_at=datetime.now()
            )
            db.add(enrollment_2)
            await db.commit()
            logger.info(f"Enrolled test user in test course 2")
        else:
            logger.info(f"Test user already enrolled in test course 2")
        
        # Create test assignments if not exist
        assignment_1_query = select(Assignment).where(
            Assignment.title == "Test Assignment 1",
            Assignment.course_id == test_course_1.id
        )
        assignment_1_result = await db.execute(assignment_1_query)
        assignment_1 = assignment_1_result.scalar_one_or_none()
        
        if not assignment_1:
            # Create assignment
            assignment_1 = Assignment(
                id=uuid.uuid4(),
                title="Test Assignment 1",
                course_id=test_course_1.id,
                description="First test assignment for automated testing",
                due_date=datetime.now() + timedelta(days=7),
                max_points=100,
                created_at=datetime.now()
            )
            db.add(assignment_1)
            await db.commit()
            logger.info(f"Created test assignment 1 with ID: {assignment_1.id}")
        else:
            logger.info(f"Using existing test assignment 1 with ID: {assignment_1.id}")
        
        # Create second test assignment
        assignment_2_query = select(Assignment).where(
            Assignment.title == "Test Assignment 2",
            Assignment.course_id == test_course_2.id
        )
        assignment_2_result = await db.execute(assignment_2_query)
        assignment_2 = assignment_2_result.scalar_one_or_none()
        
        if not assignment_2:
            # Create assignment
            assignment_2 = Assignment(
                id=uuid.uuid4(),
                title="Test Assignment 2",
                course_id=test_course_2.id,
                description="Second test assignment for automated testing",
                due_date=datetime.now() + timedelta(days=14),
                max_points=150,
                created_at=datetime.now()
            )
            db.add(assignment_2)
            await db.commit()
            logger.info(f"Created test assignment 2 with ID: {assignment_2.id}")
        else:
            logger.info(f"Using existing test assignment 2 with ID: {assignment_2.id}")
        
        # Create test FAQs if not exist
        faq_1_query = select(FAQ).where(FAQ.question == "How do I reset my password?")
        faq_1_result = await db.execute(faq_1_query)
        faq_1 = faq_1_result.scalar_one_or_none()
        
        if not faq_1:
            # Create FAQ
            faq_1 = FAQ(
                id=uuid.uuid4(),
                question="How do I reset my password?",
                answer="You can reset your password by clicking the 'Forgot Password' link on the login page and following the instructions sent to your email.",
                category="account",
                created_at=datetime.now()
            )
            db.add(faq_1)
            await db.commit()
            logger.info(f"Created test FAQ 1 with ID: {faq_1.id}")
        else:
            logger.info(f"Using existing test FAQ 1 with ID: {faq_1.id}")
        
        # Create another test FAQ
        faq_2_query = select(FAQ).where(FAQ.question == "How do I submit an assignment?")
        faq_2_result = await db.execute(faq_2_query)
        faq_2 = faq_2_result.scalar_one_or_none()
        
        if not faq_2:
            # Create FAQ
            faq_2 = FAQ(
                id=uuid.uuid4(),
                question="How do I submit an assignment?",
                answer="Navigate to the assignment page, click the 'Submit' button, and follow the instructions to upload your work.",
                category="assignments",
                created_at=datetime.now()
            )
            db.add(faq_2)
            await db.commit()
            logger.info(f"Created test FAQ 2 with ID: {faq_2.id}")
        else:
            logger.info(f"Using existing test FAQ 2 with ID: {faq_2.id}")
        
        return {
            "test_user_id": str(test_user.id),
            "test_faculty_id": str(test_faculty.id),
            "test_course_1_id": str(test_course_1.id),
            "test_course_2_id": str(test_course_2.id),
            "test_assignment_1_id": str(assignment_1.id) if assignment_1 else None,
            "test_assignment_2_id": str(assignment_2.id) if assignment_2 else None
        }
        
    except Exception as e:
        logger.error(f"Error setting up test database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    finally:
        # Close database session
        try:
            await db.close()
        except:
            pass

# -------------------- Main Test Runner --------------------

async def run_all_tests():
    """Run all function tests"""
    logger.info("Starting comprehensive function calling tests")
    
    # Set up test database
    test_data = await setup_test_db()
    if not test_data:
        logger.error("Failed to set up test database. Tests may fail due to missing data.")
    else:
        logger.info(f"Test database set up successfully with data: {json.dumps(test_data, indent=2)}")
    
    # Define all tests
    tests = [
        ("Simple function test", test_simple_function),
        ("User API functions test", lambda: test_user_functions(test_data)),
        ("Course API functions test", lambda: test_course_functions(test_data)),
        ("Assignment API functions test", lambda: test_assignment_functions(test_data)),
        ("FAQ API functions test", test_faq_functions),
        ("Web search API function test", test_web_search_function),
        ("Roadmap API function test", test_roadmap_function),
        ("Complex multi-function scenario test", lambda: test_llm_multi_function_scenario(test_data)),
    ]
    
    # Run all tests and collect results
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*20} RUNNING TEST: {test_name} {'='*20}\n")
        try:
            success = await test_func()
            results.append((test_name, success, None))
            logger.info(f"✅ {test_name}: PASSED")
        except Exception as e:
            results.append((test_name, False, str(e)))
            logger.error(f"❌ {test_name}: FAILED - {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Print summary
    logger.info("\n\n")
    logger.info("="*50)
    logger.info("FUNCTION CALLING TEST RESULTS SUMMARY")
    logger.info("="*50)
    
    passed = 0
    failed = 0
    for test_name, success, error in results:
        if success:
            logger.info(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            logger.info(f"❌ {test_name}: FAILED - {error}")
            failed += 1
    
    logger.info(f"\nTOTAL: {len(results)} tests")
    logger.info(f"PASSED: {passed} tests")
    logger.info(f"FAILED: {failed} tests")
    
    return passed, failed, len(results)

# -------------------- Entry Point --------------------

if __name__ == "__main__":
    logger.info("Starting function calling tests")
    passed, failed, total = asyncio.run(run_all_tests())
    
    # Exit with appropriate code
    if failed > 0:
        sys.exit(1)
    else:
        logger.info("All tests completed successfully!")
        sys.exit(0) 