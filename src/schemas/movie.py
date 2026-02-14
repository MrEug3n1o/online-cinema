from pydantic import BaseModel, Field, UUID4, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class GenreBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class GenreCreate(GenreBase):
    pass


class GenreUpdate(GenreBase):
    pass


class GenreResponse(GenreBase):
    id: int

    class Config:
        from_attributes = True


class GenreWithCount(GenreResponse):
    movie_count: int


class StarBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class StarCreate(StarBase):
    pass


class StarUpdate(StarBase):
    pass


class StarResponse(StarBase):
    id: int

    class Config:
        from_attributes = True


class DirectorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class DirectorCreate(DirectorBase):
    pass


class DirectorUpdate(DirectorBase):
    pass


class DirectorResponse(DirectorBase):
    id: int

    class Config:
        from_attributes = True


class CertificationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class CertificationCreate(CertificationBase):
    pass


class CertificationUpdate(CertificationBase):
    pass


class CertificationResponse(CertificationBase):
    id: int

    class Config:
        from_attributes = True


class MovieBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    year: int = Field(..., ge=1800, le=2100)
    time: int = Field(..., ge=1, description="Duration in minutes")
    imdb: float = Field(..., ge=0.0, le=10.0)
    votes: int = Field(..., ge=0)
    meta_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    gross: Optional[float] = Field(None, ge=0.0)
    description: str = Field(..., min_length=1)
    price: Decimal = Field(..., ge=0, decimal_places=2)
    certification_id: int


class MovieCreate(MovieBase):
    genre_ids: List[int] = Field(default_factory=list)
    director_ids: List[int] = Field(default_factory=list)
    star_ids: List[int] = Field(default_factory=list)


class MovieUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    year: Optional[int] = Field(None, ge=1800, le=2100)
    time: Optional[int] = Field(None, ge=1)
    imdb: Optional[float] = Field(None, ge=0.0, le=10.0)
    votes: Optional[int] = Field(None, ge=0)
    meta_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    gross: Optional[float] = None
    description: Optional[str] = Field(None, min_length=1)
    price: Optional[Decimal] = Field(None, ge=0)
    certification_id: Optional[int] = None
    genre_ids: Optional[List[int]] = None
    director_ids: Optional[List[int]] = None
    star_ids: Optional[List[int]] = None


class MovieResponse(MovieBase):
    id: int
    uuid: UUID4
    created_at: datetime
    updated_at: datetime
    certification: CertificationResponse
    genres: List[GenreResponse]
    directors: List[DirectorResponse]
    stars: List[StarResponse]

    likes_count: Optional[int] = 0
    dislikes_count: Optional[int] = 0
    comments_count: Optional[int] = 0
    average_rating: Optional[float] = None
    user_rating: Optional[int] = None  # Current user's rating
    is_liked: Optional[bool] = None  # Current user's like status
    is_favorited: Optional[bool] = False

    class Config:
        from_attributes = True


class MovieListResponse(BaseModel):
    id: int
    uuid: UUID4
    name: str
    year: int
    time: int
    imdb: float
    price: Decimal
    certification: CertificationResponse
    genres: List[GenreResponse]
    average_rating: Optional[float] = None
    is_favorited: Optional[bool] = False

    class Config:
        from_attributes = True


class MovieLikeCreate(BaseModel):
    is_like: bool  # True for like, False for dislike


class MovieLikeResponse(BaseModel):
    id: int
    user_id: int
    movie_id: int
    is_like: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class CommentUserInfo(BaseModel):
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    id: int
    user_id: int
    movie_id: int
    parent_id: Optional[int]
    content: str
    created_at: datetime
    updated_at: datetime
    user: CommentUserInfo
    likes_count: int = 0
    is_liked: Optional[bool] = False
    replies_count: int = 0

    class Config:
        from_attributes = True


class CommentWithReplies(CommentResponse):
    replies: List[CommentResponse] = []


class MovieRatingCreate(BaseModel):
    rating: int = Field(..., ge=1, le=10)


class MovieRatingResponse(BaseModel):
    id: int
    user_id: int
    movie_id: int
    rating: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MovieFavoriteResponse(BaseModel):
    id: int
    user_id: int
    movie_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MovieFilters(BaseModel):
    genre_ids: Optional[List[int]] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    imdb_min: Optional[float] = Field(None, ge=0.0, le=10.0)
    imdb_max: Optional[float] = Field(None, ge=0.0, le=10.0)
    price_min: Optional[Decimal] = Field(None, ge=0)
    price_max: Optional[Decimal] = None
    certification_ids: Optional[List[int]] = None
    search: Optional[str] = None  # Search in title, description, actor, director


class MovieSortBy(str):
    """Enum for movie sorting options"""
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    YEAR_ASC = "year_asc"
    YEAR_DESC = "year_desc"
    IMDB_ASC = "imdb_asc"
    IMDB_DESC = "imdb_desc"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    POPULARITY_DESC = "popularity_desc"  # Based on likes/comments


class PaginatedMovies(BaseModel):
    items: List[MovieListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedComments(BaseModel):
    items: List[CommentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
