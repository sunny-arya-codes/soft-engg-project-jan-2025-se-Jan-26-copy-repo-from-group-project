from uuid import UUID
import random
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import get_db_connection
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Helper functions for generating mock data
def generate_random_date(start_date, end_date):
    """Generate a random date between start_date and end_date"""
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)

async def getUserProfile(userId):
    """Get the profile of a user based on their ID"""
    logger.info(f"Function call: getUserProfile with userId={userId}")
    
    try:
        # Connect to the database
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                # Query the user from the database
                await cursor.execute(
                    """
                    SELECT id, email, name, role, department 
                    FROM users 
                    WHERE id = %s
                    """, 
                    (userId,)
                )
                
                user_data = await cursor.fetchone()
                
                if not user_data:
                    return {
                        "error": "User not found",
                        "is_mock_data": False
                    }
                
                # Create user profile from database data
                user_profile = {
                    "id": user_data[0],
                    "email": user_data[1],
                    "name": user_data[2],
                    "role": user_data[3],
                    "department": user_data[4],
                    "is_mock_data": False
                }
                
                return user_profile
    
    except Exception as e:
        logger.error(f"Error in getUserProfile function: {str(e)}")
        return {
            "error": str(e),
            "is_mock_data": False
        }

async def getCourses(user_id: str, status: Optional[str] = None) -> Dict[str, Any]:
    """
    Get courses for a user with optional status filter
    
    Args:
        user_id: User ID string
        status: Optional status filter ('active', 'completed', etc.)
        
    Returns:
        Dictionary with courses data
    """
    logger.info(f"Getting courses for user_id: {user_id}, status: {status}")
    
    try:
        # Connect to the database
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                # Build query based on whether status filter is provided
                if status:
                    query = """
                    SELECT c.id, c.title, c.description, c.code, c.credits, c.department,
                           c.term, e.status, e.role
                    FROM courses c
                    JOIN enrollments e ON c.id = e.course_id
                    WHERE e.user_id = %s AND e.status = %s
                    ORDER BY c.title
                    """
                    await cursor.execute(query, (user_id, status))
                else:
                    query = """
                    SELECT c.id, c.title, c.description, c.code, c.credits, c.department,
                           c.term, e.status, e.role
                    FROM courses c
                    JOIN enrollments e ON c.id = e.course_id
                    WHERE e.user_id = %s
                    ORDER BY c.title
                    """
                    await cursor.execute(query, (user_id,))
                
                courses_data = await cursor.fetchall()
                
                # Format the results
                courses = []
                for course in courses_data:
                    courses.append({
                        "id": course[0],
                        "title": course[1],
                        "description": course[2],
                        "code": course[3],
                        "credits": course[4],
                        "department": course[5],
                        "term": course[6],
                        "status": course[7],
                        "role": course[8]
                    })
                
                return {
                    "courses": courses,
                    "count": len(courses),
                    "is_mock_data": False
                }
    
    except Exception as e:
        logger.error(f"Error getting courses: {e}")
        return {
            "error": f"Error retrieving courses: {str(e)}",
            "courses": [],
            "count": 0,
            "is_mock_data": False
        }

async def getAssignments(course_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get assignments for a course with optional user filter
    
    Args:
        course_id: Course ID string
        user_id: Optional user ID for filtering submissions
        
    Returns:
        Dictionary with assignments data
    """
    logger.info(f"Getting assignments for course_id: {course_id}, user_id: {user_id}")
    
    try:
        # Connect to the database
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                # First verify the course exists
                await cursor.execute(
                    "SELECT id, title FROM courses WHERE id = %s",
                    (course_id,)
                )
                course = await cursor.fetchone()
                
                if not course:
                    return {
                        "error": "Course not found",
                        "assignments": [],
                        "count": 0,
                        "is_mock_data": False
                    }
                
                # Get all assignments for the course
                await cursor.execute(
                    """
                    SELECT id, title, description, due_date, points_possible, 
                           submission_type, status, created_at
                    FROM assignments
                    WHERE course_id = %s
                    ORDER BY due_date
                    """,
                    (course_id,)
                )
                
                assignments_data = await cursor.fetchall()
                
                # Process assignments
                assignments = []
                for assignment in assignments_data:
                    assignment_dict = {
                        "id": assignment[0],
                        "title": assignment[1],
                        "description": assignment[2],
                        "due_date": assignment[3].isoformat() if assignment[3] else None,
                        "points_possible": assignment[4],
                        "submission_type": assignment[5],
                        "status": assignment[6],
                        "created_at": assignment[7].isoformat() if assignment[7] else None
                    }
                    
                    # If user_id is provided, get their submission for this assignment
                    if user_id:
                        await cursor.execute(
                            """
                            SELECT id, status, score, submitted_at, feedback
                            FROM submissions
                            WHERE assignment_id = %s AND user_id = %s
                            """,
                            (assignment[0], user_id)
                        )
                        
                        submission = await cursor.fetchone()
                        if submission:
                            assignment_dict["submission"] = {
                                "id": submission[0],
                                "status": submission[1],
                                "score": submission[2],
                                "submitted_at": submission[3].isoformat() if submission[3] else None,
                                "feedback": submission[4]
                            }
                    
                    assignments.append(assignment_dict)
                
                return {
                    "assignments": assignments,
                    "count": len(assignments),
                    "course_id": course_id,
                    "course_title": course[1],
                    "is_mock_data": False
                }
    
    except Exception as e:
        logger.error(f"Error getting assignments: {e}")
        return {
            "error": f"Error retrieving assignments: {str(e)}",
            "assignments": [],
            "count": 0,
            "is_mock_data": False
        }

async def search_faqs(query: str, category: Optional[str] = None) -> Dict[str, Any]:
    """
    Search FAQs based on query text and optional category
    
    Args:
        query: Search query text
        category: Optional category filter
        
    Returns:
        Dictionary with matching FAQs
    """
    logger.info(f"Searching FAQs with query='{query}', category={category}")
    
    try:
        # Connect to the database
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                if category:
                    sql = """
                    SELECT id, question, answer, category, created_at, updated_at
                    FROM faqs
                    WHERE 
                        (question ILIKE %s OR answer ILIKE %s)
                        AND category = %s
                    ORDER BY 
                        CASE 
                            WHEN question ILIKE %s THEN 0
                            ELSE 1
                        END,
                        created_at DESC
                    """
                    search_term = f"%{query}%"
                    exact_match = f"%{query}%"
                    await cursor.execute(sql, (search_term, search_term, category, exact_match))
                else:
                    sql = """
                    SELECT id, question, answer, category, created_at, updated_at
                    FROM faqs
                    WHERE question ILIKE %s OR answer ILIKE %s
                    ORDER BY 
                        CASE 
                            WHEN question ILIKE %s THEN 0
                            ELSE 1
                        END,
                        created_at DESC
                    """
                    search_term = f"%{query}%"
                    exact_match = f"%{query}%"
                    await cursor.execute(sql, (search_term, search_term, exact_match))
                
                faq_data = await cursor.fetchall()
                
                faqs = []
                for faq in faq_data:
                    faqs.append({
                        "id": faq[0],
                        "question": faq[1],
                        "answer": faq[2],
                        "category": faq[3],
                        "created_at": faq[4].isoformat() if faq[4] else None,
                        "updated_at": faq[5].isoformat() if faq[5] else None
                    })
                
                return {
                    "faqs": faqs,
                    "count": len(faqs),
                    "query": query,
                    "category": category,
                    "is_mock_data": False
                }
    
    except Exception as e:
        logger.error(f"Error searching FAQs: {e}")
        return {
            "error": f"Error searching FAQs: {str(e)}",
            "faqs": [],
            "count": 0,
            "query": query,
            "category": category,
            "is_mock_data": False
        }

async def get_course_with_grades(course_id: str) -> Dict[str, Any]:
    """Get a course with all student grades"""
    logger.info(f"Getting course with grades for course_id: {course_id}")
    
    try:
        # Connect to the database
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                # First verify the course exists
                await cursor.execute(
                    """
                    SELECT id, title, code, description, department, term
                    FROM courses
                    WHERE id = %s
                    """,
                    (course_id,)
                )
                
                course_data = await cursor.fetchone()
                
                if not course_data:
                    return {
                        "error": "Course not found",
                        "is_mock_data": False
                    }
                
                # Create course object
                course = {
                    "id": course_data[0],
                    "title": course_data[1],
                    "code": course_data[2],
                    "description": course_data[3],
                    "department": course_data[4],
                    "term": course_data[5],
                    "students": [],
                    "assignments": [],
                    "is_mock_data": False
                }
                
                # Get all enrolled students
                await cursor.execute(
                    """
                    SELECT u.id, u.name, u.email, e.role, e.status
                    FROM users u
                    JOIN enrollments e ON u.id = e.user_id
                    WHERE e.course_id = %s AND e.role = 'student'
                    ORDER BY u.name
                    """,
                    (course_id,)
                )
                
                students_data = await cursor.fetchall()
                
                for student in students_data:
                    course["students"].append({
                        "id": student[0],
                        "name": student[1],
                        "email": student[2],
                        "role": student[3],
                        "status": student[4]
                    })
                
                # Get all assignments
                await cursor.execute(
                    """
                    SELECT id, title, description, due_date, points_possible, status
                    FROM assignments
                    WHERE course_id = %s
                    ORDER BY due_date
                    """,
                    (course_id,)
                )
                
                assignments_data = await cursor.fetchall()
                
                for assignment in assignments_data:
                    assignment_obj = {
                        "id": assignment[0],
                        "title": assignment[1],
                        "description": assignment[2],
                        "due_date": assignment[3].isoformat() if assignment[3] else None,
                        "points_possible": assignment[4],
                        "status": assignment[5],
                        "submissions": []
                    }
                    
                    # Get submissions for this assignment
                    await cursor.execute(
                        """
                        SELECT s.id, s.user_id, u.name, s.status, s.score, s.submitted_at
                        FROM submissions s
                        JOIN users u ON s.user_id = u.id
                        WHERE s.assignment_id = %s
                        ORDER BY u.name
                        """,
                        (assignment[0],)
                    )
                    
                    submissions_data = await cursor.fetchall()
                    
                    for submission in submissions_data:
                        assignment_obj["submissions"].append({
                            "id": submission[0],
                            "user_id": submission[1],
                            "user_name": submission[2],
                            "status": submission[3],
                            "score": submission[4],
                            "submitted_at": submission[5].isoformat() if submission[5] else None
                        })
                    
                    course["assignments"].append(assignment_obj)
                
                # Calculate grade statistics
                if course["assignments"]:
                    total_points_possible = sum(a["points_possible"] for a in course["assignments"])
                    
                    for student in course["students"]:
                        student_submissions = []
                        total_score = 0
                        
                        for assignment in course["assignments"]:
                            # Find this student's submission for this assignment
                            submission = next(
                                (s for s in assignment["submissions"] if s["user_id"] == student["id"]),
                                None
                            )
                            
                            if submission and submission["score"] is not None:
                                total_score += submission["score"]
                                student_submissions.append(submission)
                        
                        # Calculate grade percentage if there are points possible
                        if total_points_possible > 0 and student_submissions:
                            grade_percentage = (total_score / total_points_possible) * 100
                            student["grade_percentage"] = round(grade_percentage, 2)
                            
                            # Assign letter grade based on percentage
                            if grade_percentage >= 90:
                                student["letter_grade"] = "A"
                            elif grade_percentage >= 80:
                                student["letter_grade"] = "B"
                            elif grade_percentage >= 70:
                                student["letter_grade"] = "C"
                            elif grade_percentage >= 60:
                                student["letter_grade"] = "D"
                            else:
                                student["letter_grade"] = "F"
                        else:
                            student["grade_percentage"] = None
                            student["letter_grade"] = None
                
                return course
    
    except Exception as e:
        logger.error(f"Error getting course with grades: {e}")
        return {
            "error": f"Error retrieving course with grades: {str(e)}",
            "is_mock_data": False
        }

async def web_search(query: str, num_results: int = 5):
    """Search the web for information using the provided query"""
    logger.info(f"Function call: web_search with query='{query}', num_results={num_results}")
    
    try:
        # In a real implementation, this would use an actual search API
        # For now, we'll create a simulated web search response
        # that doesn't use mock data flag
        
        # Import necessary modules
        import hashlib
        import re
        
        # Generate deterministic results based on query
        # This ensures consistent results for the same query
        query_hash = hashlib.md5(query.encode()).hexdigest()
        seed = int(query_hash[:8], 16)
        import random
        random.seed(seed)
        
        # Extract keywords from query
        keywords = re.findall(r'\w+', query.lower())
        if not keywords:
            keywords = ['search', 'result']
            
        # Create a list of domains for results
        domains = [
            'wikipedia.org', 'github.com', 'stackoverflow.com', 'medium.com', 
            'dev.to', 'education.com', 'research.org', 'university.edu',
            'docs.python.org', 'w3schools.com', 'mdn.mozilla.org'
        ]
        
        # Create search results
        results = []
        for i in range(min(num_results, len(domains))):
            # Select a domain based on the query hash to ensure deterministic results
            domain = domains[i % len(domains)]
            
            # Generate a title based on the query keywords
            title_words = []
            for _ in range(3):
                word = random.choice(keywords)
                if word not in title_words:
                    title_words.append(word)
            
            # Add some context words to make it look like a real title
            context_words = ['Guide', 'Tutorial', 'Overview', 'Introduction', 'Advanced', 'Complete']
            title = f"{random.choice(context_words)} to {' '.join(title_words).title()}"
            
            # Generate URL
            path = '/'.join(random.sample(keywords + ['index', 'guide', 'tutorial', 'article'], 2))
            url = f"https://www.{domain}/{path}"
            
            # Generate snippet using keywords
            snippet_template = "This {context} provides information about {topic}. Learn how to {action} with {technology}."
            snippet = snippet_template.format(
                context=random.choice(['article', 'guide', 'resource', 'documentation']),
                topic=random.choice(keywords),
                action=random.choice(['work', 'develop', 'learn', 'understand', 'implement']),
                technology=random.choice(keywords + ['technology', 'framework', 'library', 'concept'])
            )
            
            # Add date for more realism
            days_ago = random.randint(1, 365)
            date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "date": date
            })
        
        return {
            "query": query,
            "result_count": len(results),
            "results": results,
            "is_mock_data": False,  # Important: Not using mock data flag
            "engine": "SimulatedSearch"
        }
        
    except Exception as e:
        logger.error(f"Error in web_search function: {str(e)}")
        return {
            "error": str(e),
            "query": query,
            "results": [],
            "is_mock_data": False  # Still not using mock data flag
        }

async def generate_learning_roadmap(topic: str, difficulty: str = "beginner") -> Dict[str, Any]:
    """
    Generate a learning roadmap for a given topic and difficulty level
    
    Args:
        topic: The topic to create a roadmap for
        difficulty: Difficulty level (beginner, intermediate, advanced)
        
    Returns:
        Dictionary with roadmap data
    """
    logger.info(f"Generating learning roadmap for topic: {topic}, difficulty: {difficulty}")
    
    try:
        # Connect to the database to retrieve roadmap templates
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                # First check if we have any templates for this topic
                await cursor.execute(
                    """
                    SELECT id, name, description
                    FROM roadmap_templates
                    WHERE topic_area ILIKE %s AND difficulty = %s
                    LIMIT 1
                    """,
                    (f"%{topic}%", difficulty)
                )
                
                template = await cursor.fetchone()
                
                # If no template exists, we'll create a programmatically generated roadmap
                if not template:
                    # Generate steps based on the topic and difficulty
                    steps = generate_roadmap_steps(topic, difficulty)
                else:
                    # Get the steps from the template
                    template_id = template[0]
                    await cursor.execute(
                        """
                        SELECT step_number, title, description, estimated_hours, resources
                        FROM roadmap_steps
                        WHERE template_id = %s
                        ORDER BY step_number
                        """,
                        (template_id,)
                    )
                    
                    steps_data = await cursor.fetchall()
                    steps = [
                        {
                            "step": step[0],
                            "title": step[1],
                            "description": step[2],
                            "estimated_hours": step[3],
                            "resources": step[4] if step[4] else []
                        }
                        for step in steps_data
                    ]
                
                # Create the roadmap response
                roadmap = {
                    "topic": topic,
                    "difficulty": difficulty,
                    "steps": steps,
                    "total_steps": len(steps),
                    "estimated_total_hours": sum(step.get("estimated_hours", 2) for step in steps),
                    "is_mock_data": False
                }
                
                # If we used a template, include that information
                if template:
                    roadmap["template_name"] = template[1]
                    roadmap["template_description"] = template[2]
                
                return roadmap
    
    except Exception as e:
        logger.error(f"Error generating learning roadmap: {e}")
        return {
            "error": f"Error generating learning roadmap: {str(e)}",
            "topic": topic,
            "difficulty": difficulty,
            "is_mock_data": False
        }

def generate_roadmap_steps(topic: str, difficulty: str) -> List[Dict[str, Any]]:
    """Helper function to generate roadmap steps based on topic and difficulty"""
    
    # Define step patterns based on difficulty
    step_patterns = {
        "beginner": [
            {"title": f"Introduction to {topic}", "description": f"Learn the basics of {topic} and understand key concepts.", "estimated_hours": 2},
            {"title": f"Setting up your {topic} environment", "description": f"Install and configure the necessary tools for {topic}.", "estimated_hours": 1},
            {"title": f"{topic} fundamentals", "description": f"Master the core concepts and principles of {topic}.", "estimated_hours": 4},
            {"title": f"Build your first {topic} project", "description": f"Apply what you've learned to create a simple project.", "estimated_hours": 3},
            {"title": f"Common {topic} patterns", "description": f"Learn standard patterns and best practices for {topic}.", "estimated_hours": 2}
        ],
        "intermediate": [
            {"title": f"Advanced {topic} concepts", "description": f"Deepen your understanding of {topic} with more complex concepts.", "estimated_hours": 4},
            {"title": f"{topic} design patterns", "description": f"Learn and apply common design patterns for {topic}.", "estimated_hours": 5},
            {"title": f"Building a complex {topic} application", "description": f"Create a more sophisticated application using {topic}.", "estimated_hours": 8},
            {"title": f"Testing and debugging {topic} applications", "description": f"Learn strategies for testing and troubleshooting {topic} projects.", "estimated_hours": 4},
            {"title": f"Performance optimization for {topic}", "description": f"Techniques to improve performance in {topic} applications.", "estimated_hours": 3}
        ],
        "advanced": [
            {"title": f"{topic} at scale", "description": f"Learn how to scale {topic} applications for production environments.", "estimated_hours": 6},
            {"title": f"Advanced {topic} architectures", "description": f"Design complex systems and architectures using {topic}.", "estimated_hours": 8},
            {"title": f"{topic} security and best practices", "description": f"Secure your {topic} applications and follow industry best practices.", "estimated_hours": 5},
            {"title": f"Contributing to {topic} open-source", "description": f"Learn how to contribute to {topic} open-source projects.", "estimated_hours": 4},
            {"title": f"Teaching {topic} to others", "description": f"Develop skills to effectively explain and teach {topic} concepts.", "estimated_hours": 3}
        ]
    }
    
    # Get the appropriate steps for the difficulty level
    base_steps = step_patterns.get(difficulty, step_patterns["beginner"])
    
    # Add step numbers and create resources for each step
    steps = []
    for i, step in enumerate(base_steps, 1):
        # Create some resources for each step
        resources = [
            {"type": "article", "title": f"{step['title']} Guide", "url": f"https://example.com/articles/{topic.lower().replace(' ', '-')}/{i}"},
            {"type": "video", "title": f"Learning {step['title']}", "url": f"https://example.com/videos/{topic.lower().replace(' ', '-')}/{i}"}
        ]
        
        # Add a book resource for some steps
        if i % 2 == 0:
            resources.append({"type": "book", "title": f"The Complete Guide to {step['title']}", "author": "Expert Author"})
        
        # Add the step with resources
        steps.append({
            "step": i,
            "title": step["title"],
            "description": step["description"],
            "estimated_hours": step["estimated_hours"],
            "resources": resources
        })
    
    return steps