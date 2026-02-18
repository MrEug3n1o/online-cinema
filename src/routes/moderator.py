from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from src.database import get_db
from src.models import (
    Movie, Genre, Star, Director, Certification, User,
    movie_genres, movie_directors, movie_stars
)
from src.schemas.movie import (
    MovieCreate, MovieUpdate, MovieResponse,
    GenreCreate, GenreUpdate, GenreResponse,
    StarCreate, StarUpdate, StarResponse,
    DirectorCreate, DirectorUpdate, DirectorResponse,
    CertificationCreate, CertificationUpdate, CertificationResponse,
    Message
)
from src.dependencies import get_moderator_user

router = APIRouter(prefix="/moderator", tags=["Moderator"])


# ============ Genre CRUD ============

@router.post("/genres", response_model=GenreResponse, status_code=status.HTTP_201_CREATED)
def create_genre(
        genre_data: GenreCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Create a new genre (Moderator only)"""
    # Check if genre already exists
    existing = db.query(Genre).filter(Genre.name == genre_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Genre already exists"
        )

    genre = Genre(name=genre_data.name)
    db.add(genre)
    db.commit()
    db.refresh(genre)
    return genre


@router.get("/genres", response_model=List[GenreResponse])
def get_all_genres(db: Session = Depends(get_db)):
    """Get all genres"""
    genres = db.query(Genre).all()
    return genres


@router.put("/genres/{genre_id}", response_model=GenreResponse)
def update_genre(
        genre_id: int,
        genre_data: GenreUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Update a genre (Moderator only)"""
    genre = db.query(Genre).filter(Genre.id == genre_id).first()
    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre not found"
        )

    if genre_data.name != genre.name:
        existing = db.query(Genre).filter(Genre.name == genre_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Genre name already exists"
            )

    genre.name = genre_data.name
    db.commit()
    db.refresh(genre)
    return genre


@router.delete("/genres/{genre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_genre(
        genre_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Delete a genre (Moderator only)"""
    genre = db.query(Genre).filter(Genre.id == genre_id).first()
    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre not found"
        )

    db.delete(genre)
    db.commit()


# ============ Star CRUD ============

@router.post("/stars", response_model=StarResponse, status_code=status.HTTP_201_CREATED)
def create_star(
        star_data: StarCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Create a new star/actor (Moderator only)"""
    existing = db.query(Star).filter(Star.name == star_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Star already exists"
        )

    star = Star(name=star_data.name)
    db.add(star)
    db.commit()
    db.refresh(star)
    return star


@router.get("/stars", response_model=List[StarResponse])
def get_all_stars(db: Session = Depends(get_db)):
    """Get all stars"""
    stars = db.query(Star).all()
    return stars


@router.put("/stars/{star_id}", response_model=StarResponse)
def update_star(
        star_id: int,
        star_data: StarUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Update a star (Moderator only)"""
    star = db.query(Star).filter(Star.id == star_id).first()
    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star not found"
        )

    if star_data.name != star.name:
        existing = db.query(Star).filter(Star.name == star_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Star name already exists"
            )

    star.name = star_data.name
    db.commit()
    db.refresh(star)
    return star


@router.delete("/stars/{star_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_star(
        star_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Delete a star (Moderator only)"""
    star = db.query(Star).filter(Star.id == star_id).first()
    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star not found"
        )

    db.delete(star)
    db.commit()


# ============ Director CRUD ============

@router.post("/directors", response_model=DirectorResponse, status_code=status.HTTP_201_CREATED)
def create_director(
        director_data: DirectorCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Create a new director (Moderator only)"""
    existing = db.query(Director).filter(Director.name == director_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Director already exists"
        )

    director = Director(name=director_data.name)
    db.add(director)
    db.commit()
    db.refresh(director)
    return director


@router.get("/directors", response_model=List[DirectorResponse])
def get_all_directors(db: Session = Depends(get_db)):
    """Get all directors"""
    directors = db.query(Director).all()
    return directors


@router.put("/directors/{director_id}", response_model=DirectorResponse)
def update_director(
        director_id: int,
        director_data: DirectorUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Update a director (Moderator only)"""
    director = db.query(Director).filter(Director.id == director_id).first()
    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director not found"
        )

    if director_data.name != director.name:
        existing = db.query(Director).filter(Director.name == director_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Director name already exists"
            )

    director.name = director_data.name
    db.commit()
    db.refresh(director)
    return director


@router.delete("/directors/{director_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_director(
        director_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Delete a director (Moderator only)"""
    director = db.query(Director).filter(Director.id == director_id).first()
    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director not found"
        )

    db.delete(director)
    db.commit()


# ============ Certification CRUD ============

@router.post("/certifications", response_model=CertificationResponse, status_code=status.HTTP_201_CREATED)
def create_certification(
        cert_data: CertificationCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Create a new certification (Moderator only)"""
    existing = db.query(Certification).filter(Certification.name == cert_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certification already exists"
        )

    certification = Certification(name=cert_data.name)
    db.add(certification)
    db.commit()
    db.refresh(certification)
    return certification


@router.get("/certifications", response_model=List[CertificationResponse])
def get_all_certifications(db: Session = Depends(get_db)):
    """Get all certifications"""
    certifications = db.query(Certification).all()
    return certifications


@router.put("/certifications/{cert_id}", response_model=CertificationResponse)
def update_certification(
        cert_id: int,
        cert_data: CertificationUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Update a certification (Moderator only)"""
    certification = db.query(Certification).filter(Certification.id == cert_id).first()
    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certification not found"
        )

    if cert_data.name != certification.name:
        existing = db.query(Certification).filter(Certification.name == cert_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Certification name already exists"
            )

    certification.name = cert_data.name
    db.commit()
    db.refresh(certification)
    return certification


@router.delete("/certifications/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certification(
        cert_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Delete a certification (Moderator only)"""
    certification = db.query(Certification).filter(Certification.id == cert_id).first()
    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certification not found"
        )

    db.delete(certification)
    db.commit()


# ============ Movie CRUD ============

@router.post("/movies", response_model=MovieResponse, status_code=status.HTTP_201_CREATED)
def create_movie(
        movie_data: MovieCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Create a new movie (Moderator only)"""
    certification = db.query(Certification).filter(
        Certification.id == movie_data.certification_id
    ).first()
    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certification not found"
        )

    movie = Movie(
        name=movie_data.name,
        year=movie_data.year,
        time=movie_data.time,
        imdb=movie_data.imdb,
        votes=movie_data.votes,
        meta_score=movie_data.meta_score,
        gross=movie_data.gross,
        description=movie_data.description,
        price=movie_data.price,
        certification_id=movie_data.certification_id
    )
    db.add(movie)
    db.flush()

    if movie_data.genre_ids:
        genres = db.query(Genre).filter(Genre.id.in_(movie_data.genre_ids)).all()
        movie.genres = genres

    if movie_data.director_ids:
        directors = db.query(Director).filter(Director.id.in_(movie_data.director_ids)).all()
        movie.directors = directors

    if movie_data.star_ids:
        stars = db.query(Star).filter(Star.id.in_(movie_data.star_ids)).all()
        movie.stars = stars

    db.commit()
    db.refresh(movie)

    return MovieResponse(
        id=movie.id,
        uuid=movie.uuid,
        name=movie.name,
        year=movie.year,
        time=movie.time,
        imdb=movie.imdb,
        votes=movie.votes,
        meta_score=movie.meta_score,
        gross=movie.gross,
        description=movie.description,
        price=movie.price,
        certification_id=movie.certification_id,
        created_at=movie.created_at,
        updated_at=movie.updated_at,
        certification=movie.certification,
        genres=movie.genres,
        directors=movie.directors,
        stars=movie.stars
    )


@router.put("/movies/{movie_id}", response_model=MovieResponse)
def update_movie(
        movie_id: int,
        movie_data: MovieUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Update a movie (Moderator only)"""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    update_data = movie_data.model_dump(exclude_unset=True, exclude={'genre_ids', 'director_ids', 'star_ids'})
    for field, value in update_data.items():
        setattr(movie, field, value)

    if movie_data.genre_ids is not None:
        genres = db.query(Genre).filter(Genre.id.in_(movie_data.genre_ids)).all()
        movie.genres = genres

    if movie_data.director_ids is not None:
        directors = db.query(Director).filter(Director.id.in_(movie_data.director_ids)).all()
        movie.directors = directors

    if movie_data.star_ids is not None:
        stars = db.query(Star).filter(Star.id.in_(movie_data.star_ids)).all()
        movie.stars = stars

    db.commit()
    db.refresh(movie)

    return MovieResponse(
        id=movie.id,
        uuid=movie.uuid,
        name=movie.name,
        year=movie.year,
        time=movie.time,
        imdb=movie.imdb,
        votes=movie.votes,
        meta_score=movie.meta_score,
        gross=movie.gross,
        description=movie.description,
        price=movie.price,
        certification_id=movie.certification_id,
        created_at=movie.created_at,
        updated_at=movie.updated_at,
        certification=movie.certification,
        genres=movie.genres,
        directors=movie.directors,
        stars=movie.stars
    )


@router.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movie(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """
    Delete a movie (Moderator only)
    Cannot delete if movie has been purchased or is in user carts
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    from app.models import PurchaseItem, CartItem

    purchases = db.query(PurchaseItem).filter(
        PurchaseItem.movie_id == movie_id
    ).count()

    if purchases > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete movie that has been purchased by {purchases} user(s)"
        )

    cart_items = db.query(CartItem).filter(
        CartItem.movie_id == movie_id
    ).count()

    if cart_items > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"WARNING: Movie exists in {cart_items} user cart(s). Remove from carts first or proceed with force delete."
        )

    db.delete(movie)
    db.commit()
