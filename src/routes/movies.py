from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_, desc, asc
from typing import Optional, List
from src.database import get_db
from src.models import (
    Movie, Genre, Star, Director, Certification,
    MovieLike, MovieComment, CommentLike, MovieFavorite, MovieRating, User
)
from src.schemas.movie import (
    MovieResponse, MovieListResponse, PaginatedMovies,
    MovieLikeCreate, MovieLikeResponse,
    CommentCreate, CommentUpdate, CommentResponse, CommentWithReplies, PaginatedComments,
    MovieRatingCreate, MovieRatingResponse,
    MovieFavoriteResponse, GenreWithCount
)
from src.dependencies import get_current_active_user
from decimal import Decimal

router = APIRouter(prefix="/movies", tags=["Movies"])


def _get_movie_query_with_stats(db: Session, user_id: Optional[int] = None):
    """Helper function to build movie query with aggregated stats"""
    query = db.query(Movie).options(
        joinedload(Movie.certification),
        joinedload(Movie.genres),
        joinedload(Movie.directors),
        joinedload(Movie.stars)
    )
    return query


def _add_user_interactions(movie_dict: dict, movie_id: int, user_id: int, db: Session):
    """Add user-specific interaction data to movie dict"""
    like = db.query(MovieLike).filter(
        MovieLike.movie_id == movie_id,
        MovieLike.user_id == user_id
    ).first()
    movie_dict['is_liked'] = like.is_like if like else None

    favorite = db.query(MovieFavorite).filter(
        MovieFavorite.movie_id == movie_id,
        MovieFavorite.user_id == user_id
    ).first()
    movie_dict['is_favorited'] = bool(favorite)

    rating = db.query(MovieRating).filter(
        MovieRating.movie_id == movie_id,
        MovieRating.user_id == user_id
    ).first()
    movie_dict['user_rating'] = rating.rating if rating else None


def _add_movie_stats(movie_dict: dict, movie_id: int, db: Session):
    """Add aggregated stats to movie dict"""
    likes_count = db.query(MovieLike).filter(
        MovieLike.movie_id == movie_id,
        MovieLike.is_like == True
    ).count()

    dislikes_count = db.query(MovieLike).filter(
        MovieLike.movie_id == movie_id,
        MovieLike.is_like == False
    ).count()

    comments_count = db.query(MovieComment).filter(
        MovieComment.movie_id == movie_id
    ).count()

    avg_rating = db.query(func.avg(MovieRating.rating)).filter(
        MovieRating.movie_id == movie_id
    ).scalar()

    movie_dict['likes_count'] = likes_count
    movie_dict['dislikes_count'] = dislikes_count
    movie_dict['comments_count'] = comments_count
    movie_dict['average_rating'] = float(avg_rating) if avg_rating else None


@router.get("", response_model=PaginatedMovies)
def get_movies(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        genre_ids: Optional[str] = Query(None, description="Comma-separated genre IDs"),
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        imdb_min: Optional[float] = None,
        imdb_max: Optional[float] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        certification_ids: Optional[str] = Query(None, description="Comma-separated certification IDs"),
        search: Optional[str] = None,
        sort_by: Optional[str] = Query("name_asc",
                                       description="Sort by: price_asc, price_desc, year_asc, year_desc, imdb_asc, imdb_desc, name_asc, name_desc, popularity_desc"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Get paginated list of movies with filters and sorting.
    Search works on: title, description, actors, directors.
    """
    query = _get_movie_query_with_stats(db, current_user.id)

    if genre_ids:
        genre_id_list = [int(x) for x in genre_ids.split(',')]
        query = query.join(Movie.genres).filter(Genre.id.in_(genre_id_list))

    if year_min:
        query = query.filter(Movie.year >= year_min)
    if year_max:
        query = query.filter(Movie.year <= year_max)

    if imdb_min:
        query = query.filter(Movie.imdb >= imdb_min)
    if imdb_max:
        query = query.filter(Movie.imdb <= imdb_max)

    if price_min:
        query = query.filter(Movie.price >= price_min)
    if price_max:
        query = query.filter(Movie.price <= price_max)

    if certification_ids:
        cert_id_list = [int(x) for x in certification_ids.split(',')]
        query = query.filter(Movie.certification_id.in_(cert_id_list))

    if search:
        search_term = f"%{search}%"
        query = query.outerjoin(Movie.stars).outerjoin(Movie.directors).filter(
            or_(
                Movie.name.ilike(search_term),
                Movie.description.ilike(search_term),
                Star.name.ilike(search_term),
                Director.name.ilike(search_term)
            )
        )

    if sort_by == "price_asc":
        query = query.order_by(asc(Movie.price))
    elif sort_by == "price_desc":
        query = query.order_by(desc(Movie.price))
    elif sort_by == "year_asc":
        query = query.order_by(asc(Movie.year))
    elif sort_by == "year_desc":
        query = query.order_by(desc(Movie.year))
    elif sort_by == "imdb_asc":
        query = query.order_by(asc(Movie.imdb))
    elif sort_by == "imdb_desc":
        query = query.order_by(desc(Movie.imdb))
    elif sort_by == "name_asc":
        query = query.order_by(asc(Movie.name))
    elif sort_by == "name_desc":
        query = query.order_by(desc(Movie.name))
    elif sort_by == "popularity_desc":
        query = query.outerjoin(MovieLike).outerjoin(MovieComment).group_by(Movie.id).order_by(
            desc(func.count(MovieLike.id) + func.count(MovieComment.id))
        )
    else:
        query = query.order_by(asc(Movie.name))

    total = query.distinct().count() if search or genre_ids else query.count()

    offset = (page - 1) * page_size
    movies = query.distinct().offset(offset).limit(page_size).all()

    movie_list = []
    for movie in movies:
        movie_dict = {
            'id': movie.id,
            'uuid': movie.uuid,
            'name': movie.name,
            'year': movie.year,
            'time': movie.time,
            'imdb': movie.imdb,
            'price': movie.price,
            'certification': movie.certification,
            'genres': movie.genres,
        }

        avg_rating = db.query(func.avg(MovieRating.rating)).filter(
            MovieRating.movie_id == movie.id
        ).scalar()
        movie_dict['average_rating'] = float(avg_rating) if avg_rating else None

        is_favorited = db.query(MovieFavorite).filter(
            MovieFavorite.movie_id == movie.id,
            MovieFavorite.user_id == current_user.id
        ).first() is not None
        movie_dict['is_favorited'] = is_favorited

        movie_list.append(MovieListResponse(**movie_dict))

    total_pages = (total + page_size - 1) // page_size

    return PaginatedMovies(
        items=movie_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{movie_id}", response_model=MovieResponse)
def get_movie(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get detailed movie information"""
    movie = db.query(Movie).options(
        joinedload(Movie.certification),
        joinedload(Movie.genres),
        joinedload(Movie.directors),
        joinedload(Movie.stars)
    ).filter(Movie.id == movie_id).first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    movie_dict = {
        'id': movie.id,
        'uuid': movie.uuid,
        'name': movie.name,
        'year': movie.year,
        'time': movie.time,
        'imdb': movie.imdb,
        'votes': movie.votes,
        'meta_score': movie.meta_score,
        'gross': movie.gross,
        'description': movie.description,
        'price': movie.price,
        'certification_id': movie.certification_id,
        'created_at': movie.created_at,
        'updated_at': movie.updated_at,
        'certification': movie.certification,
        'genres': movie.genres,
        'directors': movie.directors,
        'stars': movie.stars,
    }

    _add_movie_stats(movie_dict, movie.id, db)
    _add_user_interactions(movie_dict, movie.id, current_user.id, db)

    return MovieResponse(**movie_dict)


@router.post("/{movie_id}/like", response_model=MovieLikeResponse)
def like_movie(
        movie_id: int,
        like_data: MovieLikeCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Like or dislike a movie"""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    existing_like = db.query(MovieLike).filter(
        MovieLike.movie_id == movie_id,
        MovieLike.user_id == current_user.id
    ).first()

    if existing_like:
        existing_like.is_like = like_data.is_like
        db.commit()
        db.refresh(existing_like)
        return existing_like
    else:
        new_like = MovieLike(
            movie_id=movie_id,
            user_id=current_user.id,
            is_like=like_data.is_like
        )
        db.add(new_like)
        db.commit()
        db.refresh(new_like)
        return new_like


@router.delete("/{movie_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def remove_like(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Remove like/dislike from a movie"""
    like = db.query(MovieLike).filter(
        MovieLike.movie_id == movie_id,
        MovieLike.user_id == current_user.id
    ).first()

    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found"
        )

    db.delete(like)
    db.commit()


@router.post("/{movie_id}/rate", response_model=MovieRatingResponse)
def rate_movie(
        movie_id: int,
        rating_data: MovieRatingCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Rate a movie on a 1-10 scale"""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    existing_rating = db.query(MovieRating).filter(
        MovieRating.movie_id == movie_id,
        MovieRating.user_id == current_user.id
    ).first()

    if existing_rating:
        existing_rating.rating = rating_data.rating
        db.commit()
        db.refresh(existing_rating)
        return existing_rating
    else:
        new_rating = MovieRating(
            movie_id=movie_id,
            user_id=current_user.id,
            rating=rating_data.rating
        )
        db.add(new_rating)
        db.commit()
        db.refresh(new_rating)
        return new_rating


@router.delete("/{movie_id}/rate", status_code=status.HTTP_204_NO_CONTENT)
def remove_rating(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Remove rating from a movie"""
    rating = db.query(MovieRating).filter(
        MovieRating.movie_id == movie_id,
        MovieRating.user_id == current_user.id
    ).first()

    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found"
        )

    db.delete(rating)
    db.commit()


@router.post("/{movie_id}/favorite", response_model=MovieFavoriteResponse, status_code=status.HTTP_201_CREATED)
def add_to_favorites(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Add movie to favorites"""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    existing = db.query(MovieFavorite).filter(
        MovieFavorite.movie_id == movie_id,
        MovieFavorite.user_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie already in favorites"
        )

    favorite = MovieFavorite(
        movie_id=movie_id,
        user_id=current_user.id
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


@router.delete("/{movie_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_favorites(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Remove movie from favorites"""
    favorite = db.query(MovieFavorite).filter(
        MovieFavorite.movie_id == movie_id,
        MovieFavorite.user_id == current_user.id
    ).first()

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not in favorites"
        )

    db.delete(favorite)
    db.commit()


@router.get("/favorites/list", response_model=PaginatedMovies)
def get_favorites(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        search: Optional[str] = None,
        sort_by: Optional[str] = Query("name_asc"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get user's favorite movies with search, filter, and sort"""
    query = db.query(Movie).join(MovieFavorite).filter(
        MovieFavorite.user_id == current_user.id
    ).options(
        joinedload(Movie.certification),
        joinedload(Movie.genres),
        joinedload(Movie.directors),
        joinedload(Movie.stars)
    )

    if search:
        search_term = f"%{search}%"
        query = query.outerjoin(Movie.stars).outerjoin(Movie.directors).filter(
            or_(
                Movie.name.ilike(search_term),
                Movie.description.ilike(search_term),
                Star.name.ilike(search_term),
                Director.name.ilike(search_term)
            )
        )

    if sort_by == "price_asc":
        query = query.order_by(asc(Movie.price))
    elif sort_by == "price_desc":
        query = query.order_by(desc(Movie.price))
    elif sort_by == "year_asc":
        query = query.order_by(asc(Movie.year))
    elif sort_by == "year_desc":
        query = query.order_by(desc(Movie.year))
    elif sort_by == "imdb_asc":
        query = query.order_by(asc(Movie.imdb))
    elif sort_by == "imdb_desc":
        query = query.order_by(desc(Movie.imdb))
    else:
        query = query.order_by(asc(Movie.name))

    total = query.distinct().count() if search else query.count()

    offset = (page - 1) * page_size
    movies = query.distinct().offset(offset).limit(page_size).all()

    movie_list = []
    for movie in movies:
        movie_dict = {
            'id': movie.id,
            'uuid': movie.uuid,
            'name': movie.name,
            'year': movie.year,
            'time': movie.time,
            'imdb': movie.imdb,
            'price': movie.price,
            'certification': movie.certification,
            'genres': movie.genres,
        }

        avg_rating = db.query(func.avg(MovieRating.rating)).filter(
            MovieRating.movie_id == movie.id
        ).scalar()
        movie_dict['average_rating'] = float(avg_rating) if avg_rating else None
        movie_dict['is_favorited'] = True

        movie_list.append(MovieListResponse(**movie_dict))

    total_pages = (total + page_size - 1) // page_size

    return PaginatedMovies(
        items=movie_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/genres/list", response_model=List[GenreWithCount])
def get_genres_with_count(db: Session = Depends(get_db)):
    """Get all genres with movie count"""
    genres = db.query(
        Genre,
        func.count(Movie.id).label('movie_count')
    ).outerjoin(Genre.movies).group_by(Genre.id).all()

    result = []
    for genre, count in genres:
        result.append(GenreWithCount(
            id=genre.id,
            name=genre.name,
            movie_count=count
        ))

    return result
