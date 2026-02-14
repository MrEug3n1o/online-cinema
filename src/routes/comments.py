from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import Optional
from src.database import get_db
from src.models import Movie, MovieComment, CommentLike, User, UserProfile
from src.schemas.movie import (
    CommentCreate, CommentUpdate, CommentResponse,
    CommentWithReplies, PaginatedComments, Message
)
from src.dependencies import get_current_active_user

router = APIRouter(prefix="/movies/{movie_id}/comments", tags=["Comments"])


def _build_comment_response(comment: MovieComment, user_id: int, db: Session) -> dict:
    """Helper to build comment response with stats"""
    likes_count = db.query(CommentLike).filter(
        CommentLike.comment_id == comment.id
    ).count()

    is_liked = db.query(CommentLike).filter(
        CommentLike.comment_id == comment.id,
        CommentLike.user_id == user_id
    ).first() is not None

    replies_count = db.query(MovieComment).filter(
        MovieComment.parent_id == comment.id
    ).count()

    user_profile = db.query(User, UserProfile).outerjoin(UserProfile).filter(
        User.id == comment.user_id
    ).first()

    user_info = {
        'id': user_profile[0].id,
        'email': user_profile[0].email,
        'first_name': user_profile[1].first_name if user_profile[1] else None,
        'last_name': user_profile[1].last_name if user_profile[1] else None,
    }

    return {
        'id': comment.id,
        'user_id': comment.user_id,
        'movie_id': comment.movie_id,
        'parent_id': comment.parent_id,
        'content': comment.content,
        'created_at': comment.created_at,
        'updated_at': comment.updated_at,
        'user': user_info,
        'likes_count': likes_count,
        'is_liked': is_liked,
        'replies_count': replies_count
    }


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
        movie_id: int,
        comment_data: CommentCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Create a comment or reply on a movie"""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    if comment_data.parent_id:
        parent = db.query(MovieComment).filter(
            MovieComment.id == comment_data.parent_id,
            MovieComment.movie_id == movie_id
        ).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found"
            )

    new_comment = MovieComment(
        user_id=current_user.id,
        movie_id=movie_id,
        parent_id=comment_data.parent_id,
        content=comment_data.content
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    comment_dict = _build_comment_response(new_comment, current_user.id, db)
    return CommentResponse(**comment_dict)


@router.get("", response_model=PaginatedComments)
def get_comments(
        movie_id: int,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        parent_id: Optional[int] = Query(None,
                                         description="Filter by parent comment ID. Use null for top-level comments"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get comments for a movie with pagination"""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    query = db.query(MovieComment).filter(MovieComment.movie_id == movie_id)

    if parent_id is not None:
        query = query.filter(MovieComment.parent_id == parent_id)
    else:
        query = query.filter(MovieComment.parent_id == None)

    query = query.order_by(desc(MovieComment.created_at))

    total = query.count()

    offset = (page - 1) * page_size
    comments = query.offset(offset).limit(page_size).all()

    comment_list = []
    for comment in comments:
        comment_dict = _build_comment_response(comment, current_user.id, db)
        comment_list.append(CommentResponse(**comment_dict))

    total_pages = (total + page_size - 1) // page_size

    return PaginatedComments(
        items=comment_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{comment_id}", response_model=CommentWithReplies)
def get_comment(
        movie_id: int,
        comment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get a specific comment with its replies"""
    comment = db.query(MovieComment).filter(
        MovieComment.id == comment_id,
        MovieComment.movie_id == movie_id
    ).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    comment_dict = _build_comment_response(comment, current_user.id, db)

    replies = db.query(MovieComment).filter(
        MovieComment.parent_id == comment_id
    ).order_by(desc(MovieComment.created_at)).all()

    reply_list = []
    for reply in replies:
        reply_dict = _build_comment_response(reply, current_user.id, db)
        reply_list.append(CommentResponse(**reply_dict))

    comment_dict['replies'] = reply_list
    return CommentWithReplies(**comment_dict)


@router.put("/{comment_id}", response_model=CommentResponse)
def update_comment(
        movie_id: int,
        comment_id: int,
        comment_data: CommentUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Update own comment"""
    comment = db.query(MovieComment).filter(
        MovieComment.id == comment_id,
        MovieComment.movie_id == movie_id
    ).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    # Check ownership
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments"
        )

    comment.content = comment_data.content
    db.commit()
    db.refresh(comment)

    comment_dict = _build_comment_response(comment, current_user.id, db)
    return CommentResponse(**comment_dict)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
        movie_id: int,
        comment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Delete own comment"""
    comment = db.query(MovieComment).filter(
        MovieComment.id == comment_id,
        MovieComment.movie_id == movie_id
    ).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )

    db.delete(comment)
    db.commit()


@router.post("/{comment_id}/like", status_code=status.HTTP_201_CREATED)
def like_comment(
        movie_id: int,
        comment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Like a comment"""
    comment = db.query(MovieComment).filter(
        MovieComment.id == comment_id,
        MovieComment.movie_id == movie_id
    ).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    existing = db.query(CommentLike).filter(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment already liked"
        )

    like = CommentLike(
        comment_id=comment_id,
        user_id=current_user.id
    )
    db.add(like)
    db.commit()

    return {"message": "Comment liked successfully"}


@router.delete("/{comment_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def unlike_comment(
        movie_id: int,
        comment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Remove like from a comment"""
    like = db.query(CommentLike).filter(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == current_user.id
    ).first()

    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found"
        )

    db.delete(like)
    db.commit()