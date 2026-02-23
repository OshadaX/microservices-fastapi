from fastapi import FastAPI, HTTPException, status
from models import Student, StudentCreate, StudentUpdate
from service import StudentService
from typing import List

app = FastAPI(title="Student Microservice", version="1.0.0")

student_service = StudentService()

@app.get("/")
def root():
    return {"message": "Student Microservice is running"}

@app.get("/api/students", response_model=List[Student])
def get_students():
    return student_service.get_all()

@app.get("/api/students/{student_id}", response_model=Student)
def get_student(student_id: int):
    student = student_service.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@app.post("/api/students", response_model=Student, status_code=status.HTTP_201_CREATED)
def create_student(student: StudentCreate):
    return student_service.create(student)

@app.put("/api/students/{student_id}", response_model=Student)
def update_student(student_id: int, student: StudentUpdate):
    updated = student_service.update(student_id, student)
    if not updated:
        raise HTTPException(status_code=404, detail="Student not found")
    return updated

@app.delete("/api/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int):
    success = student_service.delete(student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Student not found")
    return None