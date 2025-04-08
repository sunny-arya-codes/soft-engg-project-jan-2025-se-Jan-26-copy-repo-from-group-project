import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Float, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base, UUID

class Quiz(Base):
    """
    Quiz model representing a quiz within a course
    """
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(UUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    topic = Column(String, nullable=True)  # Topic category for the quiz
    time_limit = Column(Integer, nullable=True)  # Time limit in minutes
    passing_score = Column(Float, default=0.6)  # Default passing score (60%)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = relationship("Course", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")
    
    # Add indexes for frequently queried fields
    __table_args__ = (
        Index('idx_quiz_course', 'course_id'),
        Index('idx_quiz_topic', 'topic'),
    )
    
    def to_dict(self):
        """Converts the Quiz object to a dictionary"""
        return {
            "id": self.id,
            "course_id": str(self.course_id),
            "title": self.title,
            "description": self.description,
            "topic": self.topic,
            "time_limit": self.time_limit,
            "passing_score": self.passing_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class QuizQuestion(Base):
    """
    Quiz Question model representing individual questions within a quiz
    """
    __tablename__ = "quiz_questions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String, nullable=False)  # multiple_choice, true_false, short_answer, etc.
    options = Column(Text, nullable=True)  # JSON string containing options for multiple choice
    correct_answer = Column(Text, nullable=False)
    points = Column(Integer, default=1)
    explanation = Column(Text, nullable=True)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    
    # Add indexes for frequently queried fields
    __table_args__ = (
        Index('idx_question_quiz', 'quiz_id'),
    )
    
    def to_dict(self):
        """Converts the QuizQuestion object to a dictionary"""
        return {
            "id": self.id,
            "quiz_id": self.quiz_id,
            "question_text": self.question_text,
            "question_type": self.question_type,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "points": self.points,
            "explanation": self.explanation
        }

class QuizAttempt(Base):
    """
    Quiz Attempt model tracking user attempts at quizzes
    """
    __tablename__ = "quiz_attempts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)  # Score as a percentage (0.0 to 1.0)
    time_taken = Column(Integer, nullable=True)  # Time taken in seconds
    answers = Column(Text, nullable=True)  # JSON string containing user's answers
    feedback = Column(Text, nullable=True)  # Feedback provided to the user
    started_at = Column(DateTime, default=datetime.utcnow)
    completion_date = Column(DateTime, nullable=True)  # When the attempt was completed
    
    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    user = relationship("User", back_populates="quiz_attempts")
    
    # Add indexes for frequently queried fields
    __table_args__ = (
        Index('idx_attempt_quiz', 'quiz_id'),
        Index('idx_attempt_user', 'user_id'),
        Index('idx_attempt_completion', 'completion_date'),
    )
    
    def to_dict(self):
        """Converts the QuizAttempt object to a dictionary"""
        return {
            "id": self.id,
            "quiz_id": self.quiz_id,
            "user_id": str(self.user_id),
            "score": self.score,
            "time_taken": self.time_taken,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "feedback": self.feedback
        } 