# Re-export CourseEnrollment from course.py for backwards compatibility
from app.models.course import CourseEnrollment, EnrollmentStatus

# Alias CourseEnrollment as Enrollment for backward compatibility
Enrollment = CourseEnrollment

__all__ = ['Enrollment', 'CourseEnrollment', 'EnrollmentStatus'] 