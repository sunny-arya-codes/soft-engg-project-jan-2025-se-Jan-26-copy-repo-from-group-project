import logging
import json
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, and_, or_
from app.models.user import User
from app.models.course import Course, CourseEnrollment, Lecture, LectureProgress
from app.models.quiz import Quiz, QuizAttempt, QuizQuestion
from app.models.assignment import Assignment, AssignmentSubmission
from app.cache import redis_client
from app.database import get_db
from app.services.llm_service import generate_learning_insights
from app.config import settings
import numpy as np
from collections import Counter

logger = logging.getLogger(__name__)

class LearningInsightsService:
    """
    Service for generating personalized learning insights based on user activity
    
    This service analyzes user learning patterns, content engagement, and performance
    data to provide actionable insights and recommendations for improving learning outcomes.
    """
    
    def __init__(self):
        self.cache_expiry = 60 * 60 * 24  # 24 hours in seconds
        self.min_data_points = 5  # Minimum data points needed for reliable analysis
    
    async def get_learning_insights(self, user: User, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Get personalized learning insights for a user
        
        Args:
            user: The user to generate insights for
            db: Optional database session
            
        Returns:
            Dict containing learning insights
        """
        # Use user_id for caching and queries
        user_id = str(user.id)
        
        # Check cache first
        cache_key = f"learning_insights_{user_id}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            logger.info(f"Returning cached learning insights for user {user_id}")
            return json.loads(cached_data)
        
        # Create DB session if not provided
        if db is None:
            async for session in get_db():
                db = session
                break

        # Collect user activity data
        data = await self._collect_user_data(user, db)
        
        # Generate insights from collected data
        insights = await self._generate_insights(user, data)
        
        # Cache the insights
        await redis_client.setex(
            cache_key,
            self.cache_expiry,
            json.dumps(insights)
        )
        
        logger.info(f"Generated new learning insights for user {user_id}")
        return insights
    
    async def _collect_user_data(self, user: User, db: AsyncSession) -> Dict[str, Any]:
        """
        Collect comprehensive user activity data for analysis
        
        Args:
            user: The user to collect data for
            db: Database session
            
        Returns:
            Dict containing user activity data
        """
        user_id = user.id
        
        # Execute all queries concurrently for performance
        tasks = [
            self._get_course_activity(user_id, db),
            self._get_lecture_activity(user_id, db),
            self._get_quiz_performance(user_id, db),
            self._get_assignment_data(user_id, db),
            self._get_engagement_patterns(user_id, db)
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {
            "courses": results[0],
            "lectures": results[1],
            "quizzes": results[2],
            "assignments": results[3],
            "engagement": results[4]
        }
    
    async def _get_course_activity(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get course enrollment and progress data"""
        # Get all enrolled courses
        enrolled_courses = await db.execute(
            select(CourseEnrollment)
            .where(CourseEnrollment.user_id == user_id)
            .order_by(desc(CourseEnrollment.enrollment_date))
        )
        enrolled_courses = enrolled_courses.scalars().all()
        
        # Get course details
        course_ids = [enrollment.course_id for enrollment in enrolled_courses]
        courses = await db.execute(
            select(Course).where(Course.id.in_(course_ids))
        )
        courses = {course.id: course for course in courses.scalars().all()}
        
        return {
            "enrollments": [
                {
                    "course_id": str(enrollment.course_id),
                    "title": courses[enrollment.course_id].title if enrollment.course_id in courses else "Unknown Course",
                    "enrollment_date": enrollment.enrollment_date.isoformat(),
                    "progress": enrollment.progress or 0,
                    "is_active": enrollment.is_active,
                    "last_accessed": enrollment.last_accessed.isoformat() if enrollment.last_accessed else None
                } for enrollment in enrolled_courses
            ],
            "count": len(enrolled_courses),
            "subjects": [course.category for course_id, course in courses.items() if course.category],
            "levels": [course.level for course_id, course in courses.items() if course.level]
        }
    
    async def _get_lecture_activity(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get lecture engagement and progress data"""
        # Get lecture progress data
        lecture_progress = await db.execute(
            select(LectureProgress)
            .where(LectureProgress.user_id == user_id)
            .order_by(desc(LectureProgress.last_accessed))
        )
        lecture_progress = lecture_progress.scalars().all()
        
        # Calculate time spent on each day and time slot
        time_spent = {}
        day_distribution = Counter()
        hour_distribution = Counter()
        
        for progress in lecture_progress:
            if progress.last_accessed:
                day = progress.last_accessed.strftime("%A")
                hour = progress.last_accessed.hour
                day_distribution[day] += progress.time_spent or 0
                hour_distribution[hour] += progress.time_spent or 0
                
                day_str = progress.last_accessed.strftime("%Y-%m-%d")
                if day_str not in time_spent:
                    time_spent[day_str] = 0
                time_spent[day_str] += progress.time_spent or 0
        
        # Find optimal study time
        optimal_day = day_distribution.most_common(1)[0][0] if day_distribution else None
        
        # Group hours into time periods
        morning_hours = sum(hour_distribution[h] for h in range(5, 12))
        afternoon_hours = sum(hour_distribution[h] for h in range(12, 17))
        evening_hours = sum(hour_distribution[h] for h in range(17, 22))
        night_hours = sum(hour_distribution[h] for h in range(22, 24)) + sum(hour_distribution[h] for h in range(0, 5))
        
        time_periods = {
            "morning": morning_hours,
            "afternoon": afternoon_hours,
            "evening": evening_hours, 
            "night": night_hours
        }
        optimal_period = max(time_periods.items(), key=lambda x: x[1])[0] if any(time_periods.values()) else None
        
        # Get lecture details to analyze content preferences
        lecture_ids = [progress.lecture_id for progress in lecture_progress if progress.completion_status >= 0.5]
        lectures = await db.execute(
            select(Lecture).where(Lecture.id.in_(lecture_ids))
        )
        lectures = lectures.scalars().all()
        
        # Analyze content preferences
        content_types = Counter()
        for lecture in lectures:
            if lecture.content_type:
                content_types[lecture.content_type] += 1
        
        preferred_content = content_types.most_common(1)[0][0] if content_types else None
        
        return {
            "time_patterns": {
                "optimal_day": optimal_day,
                "optimal_period": optimal_period,
                "day_distribution": dict(day_distribution),
                "hour_distribution": dict(hour_distribution)
            },
            "content_preferences": {
                "preferred_type": preferred_content,
                "type_distribution": dict(content_types)
            },
            "engagement_metrics": {
                "completed_lectures": len([p for p in lecture_progress if p.completion_status == 1.0]),
                "partial_lectures": len([p for p in lecture_progress if 0 < p.completion_status < 1.0]),
                "total_time_spent": sum(p.time_spent or 0 for p in lecture_progress),
                "average_completion": 
                    np.mean([p.completion_status for p in lecture_progress]) 
                    if lecture_progress else 0
            }
        }
    
    async def _get_quiz_performance(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get quiz performance data"""
        # Get quiz attempts
        quiz_attempts = await db.execute(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == user_id)
            .order_by(desc(QuizAttempt.completion_date))
        )
        quiz_attempts = quiz_attempts.scalars().all()
        
        if not quiz_attempts:
            return {
                "attempts": 0,
                "average_score": 0,
                "performance_trend": "no_data",
                "strength_topics": [],
                "weakness_topics": []
            }
        
        # Get quiz details to analyze topic strengths/weaknesses
        quiz_ids = [attempt.quiz_id for attempt in quiz_attempts]
        quizzes = await db.execute(
            select(Quiz).where(Quiz.id.in_(quiz_ids))
        )
        quizzes = {quiz.id: quiz for quiz in quizzes.scalars().all()}
        
        # Analyze scores by topic
        topic_scores = {}
        for attempt in quiz_attempts:
            if attempt.quiz_id in quizzes:
                topic = quizzes[attempt.quiz_id].topic
                if topic:
                    if topic not in topic_scores:
                        topic_scores[topic] = []
                    topic_scores[topic].append(attempt.score)
        
        # Calculate average score by topic
        topic_averages = {topic: np.mean(scores) for topic, scores in topic_scores.items()}
        
        # Identify strengths and weaknesses
        strengths = [topic for topic, avg in topic_averages.items() if avg >= 0.8]
        weaknesses = [topic for topic, avg in topic_averages.items() if avg < 0.6]
        
        # Calculate performance trend
        sorted_attempts = sorted(quiz_attempts, key=lambda x: x.completion_date)
        if len(sorted_attempts) >= 3:
            first_third = sorted_attempts[:len(sorted_attempts)//3]
            last_third = sorted_attempts[-len(sorted_attempts)//3:]
            
            first_avg = np.mean([a.score for a in first_third])
            last_avg = np.mean([a.score for a in last_third])
            
            if last_avg - first_avg > 0.1:
                trend = "improving"
            elif first_avg - last_avg > 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "attempts": len(quiz_attempts),
            "average_score": np.mean([attempt.score for attempt in quiz_attempts]),
            "performance_trend": trend,
            "strength_topics": strengths,
            "weakness_topics": weaknesses,
            "topic_performance": topic_averages
        }
    
    async def _get_assignment_data(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get assignment submission and feedback data"""
        # Get assignment submissions
        submissions = await db.execute(
            select(AssignmentSubmission)
            .where(AssignmentSubmission.user_id == user_id)
            .order_by(desc(AssignmentSubmission.submission_date))
        )
        submissions = submissions.scalars().all()
        
        if not submissions:
            return {
                "submissions": 0,
                "average_grade": 0,
                "on_time_rate": 0,
                "feedback_themes": {}
            }
        
        # Get assignment details
        assignment_ids = [sub.assignment_id for sub in submissions]
        assignments = await db.execute(
            select(Assignment).where(Assignment.id.in_(assignment_ids))
        )
        assignments = {asmt.id: asmt for asmt in assignments.scalars().all()}
        
        # Calculate on-time rate
        on_time_count = 0
        for sub in submissions:
            if sub.assignment_id in assignments:
                due_date = assignments[sub.assignment_id].due_date
                if due_date and sub.submission_date <= due_date:
                    on_time_count += 1
        
        on_time_rate = on_time_count / len(submissions) if submissions else 0
        
        # Extract common feedback themes if available
        feedback_themes = Counter()
        for sub in submissions:
            if sub.feedback and sub.feedback_themes:
                try:
                    themes = json.loads(sub.feedback_themes)
                    for theme in themes:
                        feedback_themes[theme] += 1
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return {
            "submissions": len(submissions),
            "average_grade": np.mean([sub.grade for sub in submissions if sub.grade is not None]),
            "on_time_rate": on_time_rate,
            "feedback_themes": dict(feedback_themes.most_common(5))
        }
    
    async def _get_engagement_patterns(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get overall engagement patterns and learning behaviors"""
        # Get course enrollments with last access data
        enrollments = await db.execute(
            select(CourseEnrollment)
            .where(CourseEnrollment.user_id == user_id)
            .order_by(desc(CourseEnrollment.last_accessed))
        )
        enrollments = enrollments.scalars().all()
        
        # Calculate activity frequency and consistency
        now = datetime.utcnow()
        recent_activities = [e for e in enrollments if e.last_accessed and (now - e.last_accessed).days <= 30]
        
        # Calculate active days in the last 30 days
        active_days = set()
        for enrollment in recent_activities:
            if enrollment.last_accessed:
                active_days.add(enrollment.last_accessed.strftime("%Y-%m-%d"))
        
        # Get lecture progress data to analyze session patterns
        lecture_progresses = await db.execute(
            select(LectureProgress)
            .where(LectureProgress.user_id == user_id)
            .order_by(LectureProgress.last_accessed)
        )
        lecture_progresses = lecture_progresses.scalars().all()
        
        # Analyze study session patterns
        session_durations = []
        session_gaps = []
        last_timestamp = None
        current_session = 0
        SESSION_BREAK_THRESHOLD = timedelta(hours=2)  # Define a session break as 2+ hours of inactivity
        
        for progress in lecture_progresses:
            if not progress.last_accessed:
                continue
                
            if last_timestamp:
                gap = progress.last_accessed - last_timestamp
                
                if gap > SESSION_BREAK_THRESHOLD:
                    # New session starts
                    if current_session > 0:
                        session_durations.append(current_session)
                    current_session = progress.time_spent or 0
                    session_gaps.append(gap.total_seconds() / 3600)  # Convert to hours
                else:
                    # Continue current session
                    current_session += progress.time_spent or 0
            else:
                current_session = progress.time_spent or 0
                
            last_timestamp = progress.last_accessed
            
        # Add the last session
        if current_session > 0:
            session_durations.append(current_session)
        
        # Calculate average session duration in minutes
        avg_session_duration = np.mean(session_durations) / 60 if session_durations else 0
        
        return {
            "activity_level": {
                "active_days_last_month": len(active_days),
                "consistency_score": len(active_days) / 30,  # Simple consistency metric
                "course_count": len(enrollments)
            },
            "study_sessions": {
                "average_duration_minutes": avg_session_duration,
                "average_gap_hours": np.mean(session_gaps) if session_gaps else 0,
                "total_sessions": len(session_durations),
                "preferred_session_length": "short" if avg_session_duration < 30 else
                                            "medium" if avg_session_duration < 90 else "long"
            }
        }
    
    async def _generate_insights(self, user: User, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate personalized learning insights from user data
        
        Args:
            user: The user to generate insights for
            data: Collected user activity data
            
        Returns:
            Dict containing learning insights
        """
        # First, check if we have enough data for reliable analysis
        has_sufficient_data = (
            data["courses"]["count"] > 0 and
            data["lectures"]["engagement_metrics"]["total_time_spent"] > 0 and
            (data["quizzes"]["attempts"] > 0 or data["assignments"]["submissions"] > 0)
        )
        
        if not has_sufficient_data:
            # Return basic insights with limited data
            return self._generate_basic_insights(user, data)
            
        # Determine optimal study time
        time_patterns = data["lectures"]["time_patterns"]
        optimal_period = time_patterns["optimal_period"]
        
        period_to_time = {
            "morning": "morning hours (5-11am)",
            "afternoon": "afternoon sessions (12-4pm)",
            "evening": "evening periods (5-9pm)",
            "night": "late night (10pm-4am)"
        }
        
        period_to_schedule = {
            "morning": "8-10am",
            "afternoon": "2-4pm",
            "evening": "6-8pm",
            "night": "10pm-midnight"
        }
        
        # Format optimal time information
        optimal_time = period_to_time.get(optimal_period, "various times")
        recommended_schedule = period_to_schedule.get(optimal_period, "flexible hours")
        
        # Determine content preferences
        content_prefs = data["lectures"]["content_preferences"]
        preferred_content = content_prefs["preferred_type"] or "varied formats"
        
        # Determine content recommendation based on weaknesses
        quiz_data = data["quizzes"]
        weak_topics = quiz_data["weakness_topics"]
        
        if weak_topics:
            recommendation_topic = weak_topics[0]
            recommendation_type = "practice exercises" if quiz_data["average_score"] < 0.7 else "conceptual videos"
            recommendation_reason = "addressing knowledge gaps"
        else:
            recommendation_topic = None
            recommendation_type = "interactive assignments" if data["lectures"]["engagement_metrics"]["average_completion"] < 0.8 else "advanced content"
            recommendation_reason = "improving engagement"
        
        # Learning opportunities based on strengths and weaknesses
        opportunities = []
        
        # Quiz opportunity
        if quiz_data["weakness_topics"]:
            opportunities.append({
                "type": "quiz",
                "subject": f"{quiz_data['weakness_topics'][0]} Quiz",
                "reason": "addressing knowledge gaps"
            })
        elif quiz_data["strength_topics"]:
            opportunities.append({
                "type": "quiz",
                "subject": f"Advanced {quiz_data['strength_topics'][0]}",
                "reason": "building on existing strengths"
            })
        else:
            opportunities.append({
                "type": "quiz",
                "subject": "Core Concepts Review",
                "reason": "knowledge reinforcement"
            })
        
        # Review/study opportunity
        engagement = data["engagement"]["study_sessions"]
        if engagement["preferred_session_length"] == "short":
            opportunities.append({
                "type": "review",
                "subject": "Focused Study Techniques",
                "reason": "improving retention with longer sessions"
            })
        else:
            opportunities.append({
                "type": "review",
                "subject": "Active Learning Strategies",
                "reason": "maximizing productive study time"
            })
        
        # Try to use LLM for enhanced insights if configured
        try:
            enhanced_insights = await generate_learning_insights(user, data)
            if enhanced_insights and "studyPatterns" in enhanced_insights:
                return enhanced_insights
        except Exception as e:
            logger.warning(f"Failed to generate enhanced LLM insights: {str(e)}")
        
        # Fallback to rules-based insights if LLM fails
        return {
            "studyPatterns": {
                "optimalTime": optimal_time,
                "preferredContent": preferred_content,
                "recommendedSchedule": recommended_schedule
            },
            "suggestions": {
                "contentType": recommendation_type,
                "reason": recommendation_reason,
                "topic": recommendation_topic
            },
            "opportunities": opportunities,
            "statistics": {
                "completionRate": data["lectures"]["engagement_metrics"]["average_completion"],
                "quizAverage": quiz_data["average_score"],
                "activeLastMonth": data["engagement"]["activity_level"]["active_days_last_month"],
                "strengthTopics": quiz_data["strength_topics"]
            }
        }
    
    def _generate_basic_insights(self, user: User, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic insights when we have limited data"""
        # Get the user's name to personalize even basic insights
        name = user.name.split()[0] if user.name else "there"
        
        # Check what minimal data we have
        has_lectures = data["lectures"]["engagement_metrics"]["total_time_spent"] > 0
        has_course = data["courses"]["count"] > 0
        
        # Create a personalized but generic insight package
        return {
            "studyPatterns": {
                "optimalTime": "not enough data yet",
                "preferredContent": "building your learning profile",
                "recommendedSchedule": "regular study times"
            },
            "suggestions": {
                "contentType": "interactive content and quizzes",
                "reason": "building your learning profile",
                "topic": "core fundamentals"
            },
            "opportunities": [
                {
                    "type": "quiz",
                    "subject": "Knowledge Assessment Quiz",
                    "reason": "establishing your baseline"
                },
                {
                    "type": "review",
                    "subject": "Learning Strategies Introduction",
                    "reason": "optimizing your study approach"
                }
            ],
            "limited_data_message": f"Hi {name}! Complete more lessons and quizzes to receive personalized learning insights."
        }
    
    async def invalidate_cache(self, user_id: str) -> None:
        """
        Invalidate the cached learning insights for a user
        
        Args:
            user_id: ID of the user to invalidate cache for
        """
        cache_key = f"learning_insights_{user_id}"
        await redis_client.delete(cache_key)
        logger.info(f"Invalidated learning insights cache for user {user_id}")

# Create a singleton instance
learning_insights_service = LearningInsightsService() 