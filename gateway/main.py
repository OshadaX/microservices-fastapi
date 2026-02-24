# gateway/main.py
# Includes all 4 activities:
# Activity 1: Course Microservice routes
# Activity 2: JWT Authentication
# Activity 3: Request Logging Middleware
# Activity 4: Enhanced Error Handling

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import jwt
import logging
import time
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# Activity 3: Logging Setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),                      # prints to terminal
        logging.FileHandler("gateway_requests.log")   # saves to file
    ]
)
logger = logging.getLogger("api_gateway")

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────
app = FastAPI(title="API Gateway", version="1.0.0")

# ─────────────────────────────────────────────
# Activity 2: JWT Config
# ─────────────────────────────────────────────
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

# ─────────────────────────────────────────────
# Service URLs
# ─────────────────────────────────────────────
SERVICES = {
    "student": "http://localhost:8001",
    "course":  "http://localhost:8002"   # Activity 1: Course Service
}

# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────
class StudentCreate(BaseModel):
    name: str
    age: int
    email: str
    course: str

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    email: Optional[str] = None
    course: Optional[str] = None

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

class LoginRequest(BaseModel):
    username: str
    password: str

# ─────────────────────────────────────────────
# Activity 3: Request Logging Middleware
# ─────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log incoming request
    logger.info(f"REQUEST  | {request.method} {request.url.path} | Client: {request.client.host}")

    # Process the request
    try:
        response = await call_next(request)
        process_time = round((time.time() - start_time) * 1000, 2)

        # Log response
        logger.info(f"RESPONSE | {request.method} {request.url.path} | Status: {response.status_code} | Time: {process_time}ms")

        # Add timing header to response
        response.headers["X-Process-Time"] = f"{process_time}ms"
        return response

    except Exception as e:
        process_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"ERROR    | {request.method} {request.url.path} | Error: {str(e)} | Time: {process_time}ms")
        raise

# ─────────────────────────────────────────────
# Activity 2: JWT Helper Functions
# ─────────────────────────────────────────────
def create_access_token(data: dict) -> str:
    """Create a JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token - use this as a dependency on protected routes"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_TOKEN",
                    "message": "Token payload is invalid",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TOKEN_EXPIRED",
                "message": "Token has expired. Please login again.",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_TOKEN",
                "message": "Could not validate token",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# ─────────────────────────────────────────────
# Activity 4: Enhanced forward_request with Error Handling
# ─────────────────────────────────────────────
async def forward_request(service: str, path: str, method: str, **kwargs) -> Any:
    """Forward request to the appropriate microservice with enhanced error handling"""

    # Activity 4: Check service exists
    if service not in SERVICES:
        logger.warning(f"Unknown service requested: {service}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "SERVICE_NOT_FOUND",
                "message": f"Service '{service}' does not exist",
                "available_services": list(SERVICES.keys()),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    url = f"{SERVICES[service]}{path}"
    logger.info(f"FORWARDING | {method} → {url}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            if method == "GET":
                response = await client.get(url, **kwargs)
            elif method == "POST":
                response = await client.post(url, **kwargs)
            elif method == "PUT":
                response = await client.put(url, **kwargs)
            elif method == "DELETE":
                response = await client.delete(url, **kwargs)
            else:
                raise HTTPException(
                    status_code=405,
                    detail={
                        "error": "METHOD_NOT_ALLOWED",
                        "message": f"HTTP method '{method}' is not supported",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

            # Activity 4: Handle non-2xx responses with detailed messages
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "RESOURCE_NOT_FOUND",
                        "message": f"The requested resource was not found in {service} service",
                        "path": path,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            elif response.status_code == 422:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "VALIDATION_ERROR",
                        "message": "Request data failed validation",
                        "details": response.json() if response.text else None,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            elif response.status_code >= 500:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": "SERVICE_ERROR",
                        "message": f"The {service} service encountered an internal error",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

            return JSONResponse(
                content=response.json() if response.text else None,
                status_code=response.status_code
            )

        except httpx.ConnectError:
            logger.error(f"Cannot connect to {service} service at {url}")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "SERVICE_UNAVAILABLE",
                    "message": f"Cannot connect to {service} service. Make sure it is running.",
                    "service_url": SERVICES[service],
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except httpx.TimeoutException:
            logger.error(f"Timeout connecting to {service} service at {url}")
            raise HTTPException(
                status_code=504,
                detail={
                    "error": "GATEWAY_TIMEOUT",
                    "message": f"The {service} service took too long to respond",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except httpx.RequestError as e:
            logger.error(f"Request error for {service} service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "REQUEST_FAILED",
                    "message": f"Failed to reach {service} service: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

# ─────────────────────────────────────────────
# Root Route
# ─────────────────────────────────────────────
@app.get("/")
def read_root():
    return {
        "message": "API Gateway is running",
        "available_services": list(SERVICES.keys()),
        "version": "1.0.0"
    }

# ─────────────────────────────────────────────
# Activity 2: Auth Routes (Login to get token)
# ─────────────────────────────────────────────
@app.post("/auth/login", tags=["Authentication"])
def login(credentials: LoginRequest):
    """
    Login to get a JWT token.
    Use username: admin  password: password123
    Then click Authorize (lock icon) at top of docs and paste the token.
    """
    # Simple hardcoded user for demo — in production use a database
    USERS = {
        "admin": "password123",
        "student": "student123"
    }

    if credentials.username not in USERS or USERS[credentials.username] != credentials.password:
        logger.warning(f"Failed login attempt for user: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_CREDENTIALS",
                "message": "Incorrect username or password",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    token = create_access_token({"sub": credentials.username})
    logger.info(f"Successful login for user: {credentials.username}")
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": f"{ACCESS_TOKEN_EXPIRE_MINUTES} minutes"
    }

# ─────────────────────────────────────────────
# Student Service Routes (Protected by JWT)
# ─────────────────────────────────────────────
@app.get("/gateway/students", tags=["Students"])
async def get_all_students(current_user: str = Depends(verify_token)):
    """Get all students (requires authentication)"""
    return await forward_request("student", "/api/students", "GET")

@app.get("/gateway/students/{student_id}", tags=["Students"])
async def get_student(student_id: int, current_user: str = Depends(verify_token)):
    """Get a student by ID (requires authentication)"""
    return await forward_request("student", f"/api/students/{student_id}", "GET")

@app.post("/gateway/students", tags=["Students"])
async def create_student(student: StudentCreate, current_user: str = Depends(verify_token)):
    """Create a new student (requires authentication)"""
    return await forward_request("student", "/api/students", "POST", json=student.dict())

@app.put("/gateway/students/{student_id}", tags=["Students"])
async def update_student(student_id: int, student: StudentUpdate, current_user: str = Depends(verify_token)):
    """Update a student (requires authentication)"""
    return await forward_request("student", f"/api/students/{student_id}", "PUT", json=student.dict(exclude_unset=True))

@app.delete("/gateway/students/{student_id}", tags=["Students"])
async def delete_student(student_id: int, current_user: str = Depends(verify_token)):
    """Delete a student (requires authentication)"""
    return await forward_request("student", f"/api/students/{student_id}", "DELETE")

# ─────────────────────────────────────────────
# Activity 1: Course Service Routes (Protected by JWT)
# ─────────────────────────────────────────────
@app.get("/gateway/courses", tags=["Courses"])
async def get_all_courses(current_user: str = Depends(verify_token)):
    """Get all courses (requires authentication)"""
    return await forward_request("course", "/api/courses", "GET")

@app.get("/gateway/courses/{course_id}", tags=["Courses"])
async def get_course(course_id: int, current_user: str = Depends(verify_token)):
    """Get a course by ID (requires authentication)"""
    return await forward_request("course", f"/api/courses/{course_id}", "GET")

@app.post("/gateway/courses", tags=["Courses"])
async def create_course(course: CourseCreate, current_user: str = Depends(verify_token)):
    """Create a new course (requires authentication)"""
    return await forward_request("course", "/api/courses", "POST", json=course.dict())

@app.put("/gateway/courses/{course_id}", tags=["Courses"])
async def update_course(course_id: int, course: CourseUpdate, current_user: str = Depends(verify_token)):
    """Update a course (requires authentication)"""
    return await forward_request("course", f"/api/courses/{course_id}", "PUT", json=course.dict(exclude_unset=True))

@app.delete("/gateway/courses/{course_id}", tags=["Courses"])
async def delete_course(course_id: int, current_user: str = Depends(verify_token)):
    """Delete a course (requires authentication)"""
    return await forward_request("course", f"/api/courses/{course_id}", "DELETE")