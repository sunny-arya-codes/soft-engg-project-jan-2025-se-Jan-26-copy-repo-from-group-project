import asyncio
import logging
from datetime import datetime, timedelta
import uuid

import asyncpg

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tables to create
TABLES = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL,
        department VARCHAR(100),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS courses (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        title VARCHAR(255) NOT NULL,
        code VARCHAR(50) NOT NULL,
        description TEXT,
        department VARCHAR(100),
        term VARCHAR(100),
        credits INTEGER DEFAULT 3,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS enrollments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        role VARCHAR(50) NOT NULL,
        status VARCHAR(50) DEFAULT 'active',
        enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(user_id, course_id)
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS assignments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        due_date TIMESTAMP WITH TIME ZONE,
        points_possible INTEGER NOT NULL,
        submission_type VARCHAR(50) DEFAULT 'text',
        status VARCHAR(50) DEFAULT 'active',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS submissions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        assignment_id UUID NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        content TEXT,
        status VARCHAR(50) DEFAULT 'submitted',
        score INTEGER,
        feedback TEXT,
        submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        graded_at TIMESTAMP WITH TIME ZONE,
        UNIQUE(assignment_id, user_id)
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS faqs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        category VARCHAR(100) DEFAULT 'general',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS roadmap_templates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        topic_area VARCHAR(100) NOT NULL,
        difficulty VARCHAR(50) DEFAULT 'beginner',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS roadmap_steps (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        template_id UUID NOT NULL REFERENCES roadmap_templates(id) ON DELETE CASCADE,
        step_number INTEGER NOT NULL,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        estimated_hours INTEGER DEFAULT 1,
        resources JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(template_id, step_number)
    )
    """
]

# Sample data to insert
async def insert_sample_data(conn):
    # Insert users
    user_ids = []
    users = [
        ('admin@example.com', 'Admin User', 'password123', 'admin', 'Administration'),
        ('professor@example.com', 'Professor Smith', 'password123', 'faculty', 'Computer Science'),
        ('student1@example.com', 'Student One', 'password123', 'student', 'Computer Science'),
        ('student2@example.com', 'Student Two', 'password123', 'student', 'Computer Science'),
        ('student3@example.com', 'Student Three', 'password123', 'student', 'Mathematics')
    ]
    
    for user in users:
        user_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO users (id, email, name, password_hash, role, department)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id, user[0], user[1], user[2], user[3], user[4]
        )
        user_ids.append(user_id)
    
    # Insert courses
    course_ids = []
    courses = [
        ('Introduction to Programming', 'CS101', 'An introductory course to programming concepts', 'Computer Science', 'Fall 2023'),
        ('Data Structures', 'CS201', 'Study of data structures and algorithms', 'Computer Science', 'Fall 2023'),
        ('Database Systems', 'CS301', 'Introduction to database design and SQL', 'Computer Science', 'Spring 2024'),
        ('Calculus I', 'MATH101', 'Introduction to differential calculus', 'Mathematics', 'Fall 2023')
    ]
    
    for course in courses:
        course_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO courses (id, title, code, description, department, term)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            course_id, course[0], course[1], course[2], course[3], course[4]
        )
        course_ids.append(course_id)
    
    # Enroll students and faculty in courses
    # Professor (user_ids[1]) teaches all CS courses
    await conn.execute(
        """
        INSERT INTO enrollments (user_id, course_id, role, status)
        VALUES ($1, $2, 'instructor', 'active'),
               ($1, $3, 'instructor', 'active'),
               ($1, $4, 'instructor', 'active')
        """,
        user_ids[1], course_ids[0], course_ids[1], course_ids[2]
    )
    
    # Student 1 (user_ids[2]) enrolled in all CS courses
    await conn.execute(
        """
        INSERT INTO enrollments (user_id, course_id, role, status)
        VALUES ($1, $2, 'student', 'active'),
               ($1, $3, 'student', 'active'),
               ($1, $4, 'student', 'active')
        """,
        user_ids[2], course_ids[0], course_ids[1], course_ids[2]
    )
    
    # Student 2 (user_ids[3]) enrolled in intro CS and math
    await conn.execute(
        """
        INSERT INTO enrollments (user_id, course_id, role, status)
        VALUES ($1, $2, 'student', 'active'),
               ($1, $3, 'student', 'active')
        """,
        user_ids[3], course_ids[0], course_ids[3]
    )
    
    # Student 3 (user_ids[4]) enrolled in math only
    await conn.execute(
        """
        INSERT INTO enrollments (user_id, course_id, role, status)
        VALUES ($1, $2, 'student', 'active')
        """,
        user_ids[4], course_ids[3]
    )
    
    # Create assignments for CS101
    now = datetime.now()
    assignment_ids = []
    
    assignments = [
        (course_ids[0], 'Hello World', 'Write your first program that prints "Hello, World!"', 
         now + timedelta(days=7), 10, 'code'),
        (course_ids[0], 'Variables and Types', 'Create a program demonstrating variable usage', 
         now + timedelta(days=14), 15, 'code'),
        (course_ids[0], 'Control Structures', 'Implement if/else and loops', 
         now + timedelta(days=21), 20, 'code'),
        (course_ids[1], 'Array Implementation', 'Implement a dynamic array from scratch', 
         now + timedelta(days=10), 30, 'code'),
        (course_ids[1], 'Linked List', 'Implement a linked list with insert and delete operations', 
         now + timedelta(days=20), 40, 'code')
    ]
    
    for assignment in assignments:
        assignment_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO assignments (id, course_id, title, description, due_date, points_possible, submission_type)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            assignment_id, assignment[0], assignment[1], assignment[2], 
            assignment[3], assignment[4], assignment[5]
        )
        assignment_ids.append(assignment_id)
    
    # Add some submissions
    await conn.execute(
        """
        INSERT INTO submissions (assignment_id, user_id, content, status, score, submitted_at)
        VALUES 
            ($1, $2, 'print("Hello, World!")', 'graded', 10, $3),
            ($4, $2, 'int x = 10; String name = "John";', 'graded', 13, $5),
            ($6, $2, 'for(int i=0; i<10; i++) { print(i); }', 'submitted', NULL, $7),
            ($1, $8, 'System.out.println("Hello, World!");', 'graded', 9, $9)
        """,
        assignment_ids[0], user_ids[2], now - timedelta(days=2),
        assignment_ids[1], user_ids[2], now - timedelta(days=1),
        assignment_ids[2], user_ids[2], now - timedelta(hours=5),
        assignment_ids[0], user_ids[3], now - timedelta(days=3)
    )
    
    # Add some FAQs
    faqs = [
        ('How do I enroll in a course?', 'Go to the Courses page and click "Enroll" button next to the course you want to join.', 'enrollment'),
        ('How do I submit an assignment?', 'Navigate to the assignment page and click the "Submit" button to upload your work.', 'assignments'),
        ('What is the late submission policy?', 'Late submissions are accepted up to 48 hours after the deadline with a 10% penalty per day.', 'assignments'),
        ('How do I contact my professor?', 'You can message your professor directly through the course page messaging system.', 'general'),
        ('How do I change my password?', 'Go to your account settings page and select "Change Password".', 'account')
    ]
    
    for faq in faqs:
        await conn.execute(
            """
            INSERT INTO faqs (question, answer, category)
            VALUES ($1, $2, $3)
            """,
            faq[0], faq[1], faq[2]
        )
    
    # Add a roadmap template
    template_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO roadmap_templates (id, name, description, topic_area, difficulty)
        VALUES ($1, $2, $3, $4, $5)
        """,
        template_id, 'Python Programming Roadmap', 
        'A comprehensive roadmap to learn Python programming from scratch',
        'python', 'beginner'
    )
    
    # Add roadmap steps
    steps = [
        (1, 'Getting Started with Python', 'Install Python and set up your development environment', 1),
        (2, 'Python Basics', 'Learn about variables, data types, and basic operations', 2),
        (3, 'Control Flow', 'Master if statements, loops, and basic program control', 2),
        (4, 'Functions and Modules', 'Learn how to create reusable code with functions and modules', 3),
        (5, 'Data Structures', 'Work with lists, dictionaries, sets, and tuples', 3)
    ]
    
    for step in steps:
        # Create some sample resources
        resources = [
            {"type": "article", "title": f"Guide to {step[1]}", 
             "url": f"https://example.com/python/{step[0]}"},
            {"type": "video", "title": f"Tutorial on {step[1]}", 
             "url": f"https://example.com/videos/python/{step[0]}"}
        ]
        
        await conn.execute(
            """
            INSERT INTO roadmap_steps (template_id, step_number, title, description, estimated_hours, resources)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            template_id, step[0], step[1], step[2], step[3], resources
        )
    
    logger.info("Sample data inserted successfully")

async def init_db():
    logger.info("Creating database connection")
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        logger.info("Creating database tables")
        for table_sql in TABLES:
            await conn.execute(table_sql)
        
        logger.info("Inserting sample data")
        await insert_sample_data(conn)
        
        logger.info("Database initialized successfully")
    
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    
    finally:
        await conn.close()
        logger.info("Database connection closed")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db()) 