import pytest
from unittest.mock import patch, AsyncMock
import uuid

from app.services.api_functions import (
    getUserProfile, getCourses, getAssignments, 
    search_faqs, web_search, generate_learning_roadmap
)

@pytest.mark.asyncio
async def test_getUserProfile():
    # Setup
    user_id = str(uuid.uuid4())
    
    # Test
    with patch('app.services.api_functions.get_db_connection') as mock_db:
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.__aenter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.__aenter__.return_value = mock_cursor
        
        # Mock the fetchone result
        mock_cursor.fetchone.return_value = (
            user_id, "test@example.com", "Test User", "student", "Computer Science"
        )
        
        result = await getUserProfile(user_id)
    
    # Verify
    assert result is not None
    assert "id" in result
    assert result["id"] == user_id
    assert "email" in result
    assert "name" in result
    assert "role" in result
    assert "department" in result
    assert "is_mock_data" in result
    assert result["is_mock_data"] is False

@pytest.mark.asyncio
async def test_getCourses():
    # Setup
    user_id = str(uuid.uuid4())
    
    # Test
    with patch('app.services.api_functions.get_db_connection') as mock_db:
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.__aenter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.__aenter__.return_value = mock_cursor
        
        # Mock the fetchall result
        mock_cursor.fetchall.return_value = [
            (str(uuid.uuid4()), "Course 1", "Description 1", "CS101", 3, "Computer Science", "Fall 2023", "active", "student"),
            (str(uuid.uuid4()), "Course 2", "Description 2", "CS102", 3, "Computer Science", "Fall 2023", "active", "student")
        ]
        
        result = await getCourses(user_id)
    
    # Verify
    assert result is not None
    assert "courses" in result
    assert isinstance(result["courses"], list)
    assert len(result["courses"]) == 2
    assert "count" in result
    assert result["count"] == 2
    assert "is_mock_data" in result
    assert result["is_mock_data"] is False
    
    # Check course structure
    course = result["courses"][0]
    assert "id" in course
    assert "title" in course
    assert "description" in course
    assert "code" in course
    assert "credits" in course
    assert "department" in course
    assert "term" in course
    assert "status" in course
    assert "role" in course

@pytest.mark.asyncio
async def test_getAssignments():
    # Setup
    course_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Test
    with patch('app.services.api_functions.get_db_connection') as mock_db:
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.__aenter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.__aenter__.return_value = mock_cursor
        
        # Mock the course fetchone result
        mock_cursor.fetchone.side_effect = [
            (course_id, "Test Course"),  # First call - course check
            (str(uuid.uuid4()), "submitted", 85, "2023-10-15T14:30:00", "Good work!")  # Second call - submission check
        ]
        
        # Mock the assignments fetchall result
        from datetime import datetime
        mock_cursor.fetchall.return_value = [
            (str(uuid.uuid4()), "Assignment 1", "Description 1", datetime.now(), 100, "text", "active", datetime.now())
        ]
        
        result = await getAssignments(course_id, user_id)
    
    # Verify
    assert result is not None
    assert "assignments" in result
    assert isinstance(result["assignments"], list)
    assert len(result["assignments"]) == 1
    assert "count" in result
    assert result["count"] == 1
    assert "course_id" in result
    assert result["course_id"] == course_id
    assert "course_title" in result
    assert "is_mock_data" in result
    assert result["is_mock_data"] is False
    
    # Check assignment structure
    assignment = result["assignments"][0]
    assert "id" in assignment
    assert "title" in assignment
    assert "description" in assignment
    assert "due_date" in assignment
    assert "points_possible" in assignment
    assert "submission_type" in assignment
    assert "status" in assignment
    assert "created_at" in assignment
    assert "submission" in assignment  # Submission data should be included

@pytest.mark.asyncio
async def test_search_faqs():
    # Setup
    query = "test query"
    
    # Test
    with patch('app.services.api_functions.get_db_connection') as mock_db:
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.__aenter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.__aenter__.return_value = mock_cursor
        
        # Mock the fetchall result
        from datetime import datetime
        mock_cursor.fetchall.return_value = [
            (str(uuid.uuid4()), "Test Question?", "Test Answer", "general", datetime.now(), datetime.now())
        ]
        
        result = await search_faqs(query)
    
    # Verify
    assert result is not None
    assert "faqs" in result
    assert isinstance(result["faqs"], list)
    assert len(result["faqs"]) == 1
    assert "count" in result
    assert result["count"] == 1
    assert "query" in result
    assert result["query"] == query
    assert "is_mock_data" in result
    assert result["is_mock_data"] is False
    
    # Check FAQ structure
    faq = result["faqs"][0]
    assert "id" in faq
    assert "question" in faq
    assert "answer" in faq
    assert "category" in faq
    assert "created_at" in faq
    assert "updated_at" in faq

@pytest.mark.asyncio
async def test_web_search():
    # Setup
    query = "test query"
    
    # Test
    result = await web_search(query)
    
    # Verify
    assert result is not None
    assert "query" in result
    assert result["query"] == query
    assert "results" in result
    assert isinstance(result["results"], list)
    assert "result_count" in result
    assert result["result_count"] == len(result["results"])
    assert "is_mock_data" in result
    assert result["is_mock_data"] is False
    
    # Check result structure if there are any results
    if result["results"]:
        search_result = result["results"][0]
        assert "title" in search_result
        assert "url" in search_result
        assert "snippet" in search_result

@pytest.mark.asyncio
async def test_generate_learning_roadmap():
    # Setup
    topic = "Python"
    difficulty = "beginner"
    
    # Test
    with patch('app.services.api_functions.get_db_connection') as mock_db:
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.__aenter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.__aenter__.return_value = mock_cursor
        
        # Mock the fetchone result to be None (no template found)
        mock_cursor.fetchone.return_value = None
        
        result = await generate_learning_roadmap(topic, difficulty)
    
    # Verify
    assert result is not None
    assert "topic" in result
    assert result["topic"] == topic
    assert "difficulty" in result
    assert result["difficulty"] == difficulty
    assert "steps" in result
    assert isinstance(result["steps"], list)
    assert "total_steps" in result
    assert result["total_steps"] == len(result["steps"])
    assert "estimated_total_hours" in result
    assert isinstance(result["estimated_total_hours"], (int, float))
    assert "is_mock_data" in result
    assert result["is_mock_data"] is False
    
    # Check step structure if there are any steps
    if result["steps"]:
        step = result["steps"][0]
        assert "step" in step
        assert "title" in step
        assert "description" in step
        assert "estimated_hours" in step
        assert "resources" in step 