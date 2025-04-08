import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
from app.services.learning_insights_service import LearningInsightsService
from app.models.user import User

@pytest.fixture
def mock_user():
    """Create a mock user for testing"""
    user = MagicMock(spec=User)
    user.id = "12345"
    user.name = "Test User"
    user.email = "test@example.com"
    return user

@pytest.fixture
def learning_insights_service():
    """Create a learning insights service for testing"""
    return LearningInsightsService()

@pytest.mark.asyncio
async def test_get_learning_insights_cache_miss(learning_insights_service, mock_user):
    """Test getting learning insights with a cache miss"""
    # Mock the redis client
    with patch('app.services.learning_insights_service.redis_client') as mock_redis:
        # Set up the mock to simulate a cache miss
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        
        # Call the service
        insights = await learning_insights_service.get_learning_insights(mock_user)
        
        # Check the result
        assert isinstance(insights, dict)
        assert "studyPatterns" in insights
        assert "suggestions" in insights
        assert "opportunities" in insights
        assert len(insights["opportunities"]) == 2
        
        # Verify redis interactions
        mock_redis.get.assert_called_once_with(f"learning_insights_{mock_user.id}")
        mock_redis.setex.assert_called_once()

@pytest.mark.asyncio
async def test_get_learning_insights_cache_hit(learning_insights_service, mock_user):
    """Test getting learning insights with a cache hit"""
    # Create mock cached data
    cached_insights = {
        "studyPatterns": {
            "optimalTime": "morning hours",
            "preferredContent": "video content",
            "recommendedSchedule": "8-10am"
        },
        "suggestions": {
            "contentType": "practice exercises",
            "reason": "interaction patterns"
        },
        "opportunities": [
            {
                "type": "quiz",
                "subject": "Data Structures Quiz",
                "reason": "knowledge reinforcement"
            },
            {
                "type": "review",
                "subject": "Web Security Fundamentals",
                "reason": "preparation for advanced topics"
            }
        ]
    }
    
    # Mock the redis client
    with patch('app.services.learning_insights_service.redis_client') as mock_redis:
        # Set up the mock to simulate a cache hit
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_insights))
        
        # Call the service
        insights = await learning_insights_service.get_learning_insights(mock_user)
        
        # Check the result
        assert insights == cached_insights
        
        # Verify redis interactions
        mock_redis.get.assert_called_once_with(f"learning_insights_{mock_user.id}")

@pytest.mark.asyncio
async def test_invalidate_cache(learning_insights_service):
    """Test invalidating the cache for learning insights"""
    # Mock the redis client
    with patch('app.services.learning_insights_service.redis_client') as mock_redis:
        mock_redis.delete = AsyncMock()
        
        # Call the service
        user_id = "12345"
        await learning_insights_service.invalidate_cache(user_id)
        
        # Verify redis interactions
        mock_redis.delete.assert_called_once_with(f"learning_insights_{user_id}")

@pytest.mark.asyncio
async def test_learning_insights_structure(learning_insights_service, mock_user):
    """Test the structure of the generated learning insights"""
    # Mock the redis client to simulate a cache miss
    with patch('app.services.learning_insights_service.redis_client') as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        
        # Call the service
        insights = await learning_insights_service.get_learning_insights(mock_user)
        
        # Check the structure
        assert "studyPatterns" in insights
        assert "optimalTime" in insights["studyPatterns"]
        assert "preferredContent" in insights["studyPatterns"]
        assert "recommendedSchedule" in insights["studyPatterns"]
        
        assert "suggestions" in insights
        assert "contentType" in insights["suggestions"]
        assert "reason" in insights["suggestions"]
        
        assert "opportunities" in insights
        assert isinstance(insights["opportunities"], list)
        assert len(insights["opportunities"]) == 2
        
        for opportunity in insights["opportunities"]:
            assert "type" in opportunity
            assert "subject" in opportunity
            assert "reason" in opportunity 