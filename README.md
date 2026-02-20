# Online Cinema API

A comprehensive FastAPI-based backend for an online cinema platform with robust user authentication, authorization, role-based access control, and complete movie management system.

## Features

### Authentication & Authorization
- **User Registration** with email verification
- **Account Activation** via email token (24-hour expiration)
- **Login/Logout** with JWT tokens (access + refresh)
- **Password Management**:
  - Change password (requires old password)
  - Reset password via email (for forgotten passwords)
  - Password complexity validation
- **Role-Based Access Control**:
  - **User**: Basic access + movie interactions
  - **Moderator**: Content management + basic access
  - **Admin**: Full user management + all permissions

### User Management
- User profile management (name, avatar, gender, bio, etc.)
- Admin capabilities:
  - View all users
  - Change user roles
  - Manually activate/deactivate accounts
  - Delete users

### Movies Module 🎬
**User Features:**
- Browse paginated movie catalog with advanced filtering
- Full-text search across titles, descriptions, actors, directors
- Filter by genre, year, IMDb rating, price, certification
- Sort by price, year, rating, popularity, name
- View detailed movie information with stats
- Like/Dislike movies
- Rate movies (1-10 scale)
- Write and edit comments with nested replies
- Like comments
- Add movies to favorites
- Manage favorites list with same search/filter capabilities
- View genres with movie counts

**Moderator Features:**
- Complete CRUD operations for movies
- Manage genres, stars, directors, certifications
- Protected movie deletion (prevents deletion if purchased)
- Batch operations for content management

### Shopping Cart & Purchases 🛒 (NEW!)
**User Features:**
- Add movies to cart with validation
- Prevent adding already-purchased movies
- Prevent duplicate items in cart
- View cart with movie details and total
- Remove items or clear entire cart
- Get cart summary (count & total)
- Validate cart before checkout
- Complete purchase with payment method selection
- View paginated purchase history
- List all purchased movies with purchase details
- Check if specific movie is purchased
- Prices preserved at time of purchase

**Validation & Protection:**
- Cannot add purchased movies to cart
- Cannot add same movie twice to cart
- Checkout validates all items
- Removes unavailable/purchased items automatically
- Requires authentication before purchase

**Admin Features:**
- View all user carts (analytics)
- Inspect specific user's cart
- Check if movie exists in any carts
- Get list of affected users before deletion
- Clear user carts (troubleshooting)
- Complete deletion protection system

### Background Tasks
- **Celery Beat** for periodic token cleanup
- Automated removal of expired activation and password reset tokens

## Tech Stack

- **FastAPI** - Modern, fast web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Primary database
- **Alembic** - Database migrations
- **JWT** - Token-based authentication
- **Celery** - Asynchronous task queue
- **Redis** - Celery broker and caching
- **Pydantic** - Data validation
- **Stripe** - Payment processing
- **Poetry** - Dependency management
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **MinIO** - Object storage
- **Nginx** - Reverse proxy (production)

## Project Structure

```
online-cinema/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection
│   ├── security.py          # Password hashing, JWT functions
│   ├── email.py             # Email sending functions
│   ├── dependencies.py      # Auth dependencies
│   ├── schemas.py           # Pydantic schemas
│   ├── celery_worker.py     # Celery tasks
│   ├── models/
│   │   ├── __init__.py
│   │   ├── enums.py         # Enums (UserGroup, Gender)
│   │   └── models.py        # SQLAlchemy models
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # Authentication routes
│       ├── users.py         # User profile routes
│       └── admin.py         # Admin routes
├── alembic/
│   ├── versions/
│   │   └── 001_initial_migration.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup Instructions

### 1. Prerequisites

- Python 3.10+
- PostgreSQL
- Redis

### 2. Clone and Install

```bash
# Clone the repository
git clone <repository-url>
cd online-cinema

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Important**: Update the following in `.env`:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Generate a secure random key
- `SMTP_*` - Email server settings
- `REDIS_URL` - Redis connection string

### 4. Database Setup

```bash
# Run migrations
alembic upgrade head
```

This will:
- Create all database tables
- Insert default user groups (USER, MODERATOR, ADMIN)

### 5. Run the Application

**Terminal 1 - FastAPI Server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
celery -A app.celery_worker worker --loglevel=info
```

**Terminal 3 - Celery Beat (for scheduled tasks):**
```bash
celery -A app.celery_worker beat --loglevel=info
```

### 6. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### 7. (Optional) Seed Sample Data

Load sample movies, genres, and actors for testing:

```bash
python seed_movies.py
```

This creates:
- 22 genres (Action, Drama, Sci-Fi, etc.)
- 18 sample actors/stars
- 11 sample directors
- 5 sample movies (The Matrix, Inception, The Dark Knight, Interstellar, Oppenheimer)

## API Endpoints

### Authentication (`/auth`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/activate` | Activate account with token | No |
| POST | `/auth/resend-activation` | Resend activation email | No |
| POST | `/auth/login` | Login and get tokens | No |
| POST | `/auth/refresh` | Refresh access token | No |
| POST | `/auth/logout` | Logout (delete refresh token) | Yes |
| POST | `/auth/change-password` | Change password | Yes |
| POST | `/auth/forgot-password` | Request password reset | No |
| POST | `/auth/reset-password` | Reset password with token | No |

### Users (`/users`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/users/me` | Get current user info | Yes |
| GET | `/users/me/profile` | Get current user profile | Yes |
| PUT | `/users/me/profile` | Update profile | Yes |

### Admin (`/admin`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/admin/users` | Get all users | Admin |
| GET | `/admin/users/{user_id}` | Get user by ID | Admin |
| PATCH | `/admin/users/{user_id}/group` | Update user group | Admin |
| PATCH | `/admin/users/{user_id}/activate` | Activate/deactivate user | Admin |
| DELETE | `/admin/users/{user_id}` | Delete user | Admin |

### Movies (`/movies`) 🎬

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/movies` | Get paginated movies with filters | Yes |
| GET | `/movies/{movie_id}` | Get movie details | Yes |
| POST | `/movies/{movie_id}/like` | Like/dislike movie | Yes |
| DELETE | `/movies/{movie_id}/like` | Remove like | Yes |
| POST | `/movies/{movie_id}/rate` | Rate movie (1-10) | Yes |
| DELETE | `/movies/{movie_id}/rate` | Remove rating | Yes |
| POST | `/movies/{movie_id}/favorite` | Add to favorites | Yes |
| DELETE | `/movies/{movie_id}/favorite` | Remove from favorites | Yes |
| GET | `/movies/favorites/list` | Get favorites list | Yes |
| GET | `/movies/genres/list` | Get genres with counts | Yes |

### Comments (`/movies/{movie_id}/comments`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/comments` | Create comment/reply | Yes |
| GET | `/comments` | Get comments (paginated) | Yes |
| GET | `/comments/{comment_id}` | Get comment with replies | Yes |
| PUT | `/comments/{comment_id}` | Update own comment | Yes |
| DELETE | `/comments/{comment_id}` | Delete own comment | Yes |
| POST | `/comments/{comment_id}/like` | Like comment | Yes |
| DELETE | `/comments/{comment_id}/like` | Unlike comment | Yes |

### Moderator (`/moderator`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/moderator/movies` | Create movie | Moderator |
| PUT | `/moderator/movies/{id}` | Update movie | Moderator |
| DELETE | `/moderator/movies/{id}` | Delete movie | Moderator |
| POST/GET/PUT/DELETE | `/moderator/genres` | CRUD genres | Moderator |
| POST/GET/PUT/DELETE | `/moderator/stars` | CRUD stars | Moderator |
| POST/GET/PUT/DELETE | `/moderator/directors` | CRUD directors | Moderator |
| POST/GET/PUT/DELETE | `/moderator/certifications` | CRUD certifications | Moderator |

### Shopping Cart (`/cart`) 🛒

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/cart` | Get cart with items | Yes |
| POST | `/cart/items` | Add movie to cart | Yes |
| DELETE | `/cart/items/{movie_id}` | Remove from cart | Yes |
| DELETE | `/cart/clear` | Clear entire cart | Yes |
| GET | `/cart/summary` | Get cart summary | Yes |
| POST | `/cart/validate` | Validate cart items | Yes |
| GET | `/cart/check-movie/{id}` | Check movie status | Yes |

### Purchases (`/purchases`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/purchases/checkout` | Complete purchase | Yes |
| GET | `/purchases` | Get purchase history | Yes |
| GET | `/purchases/{id}` | Get purchase details | Yes |
| GET | `/purchases/movies/list` | List purchased movies | Yes |
| GET | `/purchases/check/{movie_id}` | Check if purchased | Yes |

### Admin Cart Management (`/admin/carts`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/admin/carts` | Get all user carts | Admin |
| GET | `/admin/carts/{user_id}` | Get user's cart | Admin |
| GET | `/admin/carts/movie/{id}/usage` | Check movie in carts | Moderator |
| DELETE | `/admin/carts/user/{id}/clear` | Clear user cart | Admin |

For detailed Movies API documentation, see [MOVIES_MODULE.md](MOVIES_MODULE.md)  
For detailed Shopping Cart documentation, see [SHOPPING_CART_MODULE.md](SHOPPING_CART_MODULE.md)
| GET | `/admin/users/{user_id}` | Get user by ID | Admin |
| PATCH | `/admin/users/{user_id}/group` | Update user group | Admin |
| PATCH | `/admin/users/{user_id}/activate` | Activate/deactivate user | Admin |
| DELETE | `/admin/users/{user_id}` | Delete user | Admin |

## Usage Examples

### 1. Register a New User

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### 2. Activate Account

```bash
curl -X POST "http://localhost:8000/auth/activate?token=<activation_token>"
```

### 3. Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "xyzabc...",
  "token_type": "bearer"
}
```

### 4. Access Protected Endpoint

```bash
curl -X GET "http://localhost:8000/users/me" \
  -H "Authorization: Bearer <access_token>"
```

### 5. Update Profile

```bash
curl -X PUT "http://localhost:8000/users/me/profile" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "gender": "MAN",
    "date_of_birth": "1990-01-01"
  }'
```

### 6. Admin: Change User Role

```bash
curl -X PATCH "http://localhost:8000/admin/users/2/group" \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "group": "MODERATOR"
  }'
```

## Password Requirements

All passwords must meet the following complexity requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*(),.?":{}|<>)

## Token Expiration

- **Access Token**: 30 minutes (configurable)
- **Refresh Token**: 7 days (configurable)
- **Activation Token**: 24 hours
- **Password Reset Token**: 1 hour

## Database Models

### User Groups
- **USER**: Standard user access
- **MODERATOR**: Can manage content
- **ADMIN**: Full system access

### User
- id, email, hashed_password, is_active
- created_at, updated_at
- Relationships: group, profile, tokens

### UserProfile
- first_name, last_name, avatar
- gender, date_of_birth, info
- One-to-one with User

### Tokens
- **ActivationToken**: For account activation
- **PasswordResetToken**: For password resets
- **RefreshToken**: For JWT refresh

## Background Tasks

### Token Cleanup (Celery Beat)

Runs every hour to delete expired tokens:
- Expired activation tokens
- Expired password reset tokens

This keeps the database clean and secure.

## Security Features

1. **Password Hashing**: Using bcrypt
2. **JWT Tokens**: Secure access/refresh token system
3. **Email Verification**: Required for account activation
4. **Role-Based Access**: Granular permission control
5. **Token Expiration**: Automatic cleanup of old tokens
6. **HTTPS Ready**: Configure for production use

## Development

### Create Migration

```bash
alembic revision --autogenerate -m "description"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

## Production Deployment

1. **Set Strong SECRET_KEY**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Configure CORS** properly in `main.py`

3. **Use HTTPS** with a reverse proxy (nginx/caddy)

4. **Set up proper email service** (SendGrid, AWS SES, etc.)

5. **Use production WSGI server**:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

6. **Set up monitoring** for Celery tasks

7. **Configure database backups**

## Testing

The API documentation at `/docs` provides an interactive interface to test all endpoints.

## License

MIT License

## Support

For issues or questions, please open an issue in the repository.
