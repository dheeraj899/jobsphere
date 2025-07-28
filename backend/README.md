# JobSphere Backend

## Introduction
JobSphere backend provides a modular, scalable REST API for a full-featured job marketplace platform. It handles user authentication, profile management, job postings, applications, geolocation, messaging, notifications, search, analytics, and more.

## Technical Stack
- Python 3.10+
- Django 4.2
- Django REST Framework (DRF)
- djangorestframework-simplejwt (JWT Authentication)
- PostgreSQL 14+ with PostGIS
- Redis (caching & Celery broker)
- Celery 5 (Asynchronous tasks)
- django-filter (request filtering)
- drf-yasg (Swagger/OpenAPI documentation)
- django-redis (Redis cache integration)
- Pillow (image handling)

## Prerequisites
- Python 3.10 or higher installed
- pip package manager
- Virtualenv or venv module
- PostgreSQL server with PostGIS extension
- Redis server
- A valid TLS certificate for HTTPS in production

## Features
- Secure JWT authentication (registration, login, token refresh, logout)
- User profile management with avatars and extended contact info
- CRUD operations for Jobs, with geospatial filtering and proximity search
- Job Applications and Saved Jobs functionality
- Interactive mapping: Regions, Locations, and Nearby searches
- Activity dashboard and analytics reporting
- Real-time messaging and notification system
- Full-text search and dynamic filter-driven suggestions
- Admin interface for all models with custom list displays and inlines
- Swagger/OpenAPI API documentation with drf-yasg
- Redis caching for high-traffic endpoints
- Asynchronous email and analytics tasks via Celery
- Rate limiting and security best practices enforced

## Steps to Start
1. **Clone the repository**
   ```bash
   git clone <REPO_URL>
   cd jobsphere/backend
   ```
2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\\Scripts\\activate
   # macOS/Linux
   source venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with real values
   ```
5. **Generate and apply database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```
7. **Run Redis and PostgreSQL services**
8. **Start Celery worker (in separate terminal)**
   ```bash
   celery -A Project worker -l info
   ```
9. **Run the development server**
   ```bash
   python manage.py runserver
   ```
   - **Admin Panel:** Visit `http://localhost:8000/admin/` and log in with your superuser.
10. **Access the API**
    - Base API: `http://localhost:8000/api/v1/`
    - Swagger UI: `http://localhost:8000/swagger/`
11. **Run tests**
    ```bash
    python manage.py test
    ```
12. **Seed database (optional)**
    ```bash
    python manage.py seed_db
    # e.g. python manage.py seed_db
    ```
