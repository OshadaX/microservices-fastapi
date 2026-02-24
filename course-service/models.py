# course-service/models.py
from pydantic import BaseModel
from typing import Optional

class Course(BaseModel):
    id: int
    title: str
    description: str
    duration_weeks: int
    instructor: str
    max_students: int

class CourseCreate(BaseModel):
    title: str
    description: str
    duration_weeks: int
    instructor: str
    max_students: int

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_weeks: Optional[int] = None
    instructor: Optional[str] = None
    max_students: Optional[int] = None