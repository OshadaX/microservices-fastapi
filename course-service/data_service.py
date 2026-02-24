# course-service/data_service.py
from models import Course

class CourseMockDataService:
    def __init__(self):
        self.courses = [
            Course(id=1, title="Python Programming", description="Learn Python from scratch", duration_weeks=8, instructor="Dr. Smith", max_students=30),
            Course(id=2, title="Web Development", description="HTML, CSS, JavaScript basics", duration_weeks=10, instructor="Dr. Johnson", max_students=25),
            Course(id=3, title="Data Science", description="Data analysis and machine learning", duration_weeks=12, instructor="Dr. Williams", max_students=20),
        ]
        self.next_id = 4

    def get_all_courses(self):
        return self.courses

    def get_course_by_id(self, course_id: int):
        return next((c for c in self.courses if c.id == course_id), None)

    def add_course(self, course_data):
        new_course = Course(id=self.next_id, **course_data.dict())
        self.courses.append(new_course)
        self.next_id += 1
        return new_course

    def update_course(self, course_id: int, course_data):
        course = self.get_course_by_id(course_id)
        if course:
            update_data = course_data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(course, key, value)
            return course
        return None

    def delete_course(self, course_id: int):
        course = self.get_course_by_id(course_id)
        if course:
            self.courses.remove(course)
            return True
        return False