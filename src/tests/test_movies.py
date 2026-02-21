import pytest
from fastapi import status
from decimal import Decimal


class TestMovieBrowsing:
    """Test movie browsing and filtering"""

    def test_get_movies_success(self, client, auth_headers, sample_movie_data):
        """Test getting movies list"""
        response = client.get("/movies", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) > 0

    def test_get_movies_pagination(self, client, auth_headers, sample_movie_data):
        """Test movies pagination"""
        response = client.get(
            "/movies?page=1&page_size=10",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_get_movies_filter_by_genre(self, client, auth_headers, sample_movie_data):
        """Test filtering movies by genre"""
        genre_id = sample_movie_data["genre"].id
        response = client.get(
            f"/movies?genre_ids={genre_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) > 0

    def test_get_movies_search(self, client, auth_headers, sample_movie_data):
        """Test searching movies"""
        response = client.get(
            "/movies?search=Test",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) > 0

    def test_get_movies_sort_by_price(self, client, auth_headers, sample_movie_data):
        """Test sorting movies by price"""
        response = client.get(
            "/movies?sort_by=price_asc",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_movies_unauthorized(self, client):
        """Test getting movies without authentication"""
        response = client.get("/movies")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMovieDetails:
    """Test movie detail endpoints"""

    def test_get_movie_details(self, client, auth_headers, sample_movie_data):
        """Test getting movie details"""
        movie_id = sample_movie_data["movie"].id
        response = client.get(f"/movies/{movie_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == movie_id
        assert "name" in data
        assert "genres" in data
        assert "directors" in data

    def test_get_nonexistent_movie(self, client, auth_headers):
        """Test getting non-existent movie"""
        response = client.get("/movies/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMovieLikes:
    """Test movie like/dislike functionality"""

    def test_like_movie(self, client, auth_headers, sample_movie_data):
        """Test liking a movie"""
        movie_id = sample_movie_data["movie"].id
        response = client.post(
            f"/movies/{movie_id}/like",
            headers=auth_headers,
            json={"is_like": True}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_like"] is True

    def test_dislike_movie(self, client, auth_headers, sample_movie_data):
        """Test disliking a movie"""
        movie_id = sample_movie_data["movie"].id
        response = client.post(
            f"/movies/{movie_id}/like",
            headers=auth_headers,
            json={"is_like": False}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_like"] is False

    def test_remove_like(self, client, auth_headers, sample_movie_data):
        """Test removing like from movie"""
        movie_id = sample_movie_data["movie"].id

        # First like the movie
        client.post(
            f"/movies/{movie_id}/like",
            headers=auth_headers,
            json={"is_like": True}
        )

        # Then remove like
        response = client.delete(
            f"/movies/{movie_id}/like",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestMovieRatings:
    """Test movie rating functionality"""

    @pytest.mark.parametrize("rating", [1, 5, 10])
    def test_rate_movie_valid(self, client, auth_headers, sample_movie_data, rating):
        """Test rating movie with valid values"""
        movie_id = sample_movie_data["movie"].id
        response = client.post(
            f"/movies/{movie_id}/rate",
            headers=auth_headers,
            json={"rating": rating}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["rating"] == rating

    @pytest.mark.parametrize("rating", [0, 11, -1])
    def test_rate_movie_invalid(self, client, auth_headers, sample_movie_data, rating):
        """Test rating movie with invalid values"""
        movie_id = sample_movie_data["movie"].id
        response = client.post(
            f"/movies/{movie_id}/rate",
            headers=auth_headers,
            json={"rating": rating}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_rating(self, client, auth_headers, sample_movie_data):
        """Test updating existing rating"""
        movie_id = sample_movie_data["movie"].id

        # First rating
        client.post(
            f"/movies/{movie_id}/rate",
            headers=auth_headers,
            json={"rating": 5}
        )

        # Update rating
        response = client.post(
            f"/movies/{movie_id}/rate",
            headers=auth_headers,
            json={"rating": 8}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["rating"] == 8


class TestMovieFavorites:
    """Test movie favorites functionality"""

    def test_add_to_favorites(self, client, auth_headers, sample_movie_data):
        """Test adding movie to favorites"""
        movie_id = sample_movie_data["movie"].id
        response = client.post(
            f"/movies/{movie_id}/favorite",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_add_duplicate_favorite(self, client, auth_headers, sample_movie_data):
        """Test adding already favorited movie"""
        movie_id = sample_movie_data["movie"].id

        # Add to favorites
        client.post(f"/movies/{movie_id}/favorite", headers=auth_headers)

        # Try to add again
        response = client.post(
            f"/movies/{movie_id}/favorite",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_favorites_list(self, client, auth_headers, sample_movie_data):
        """Test getting favorites list"""
        movie_id = sample_movie_data["movie"].id

        # Add to favorites
        client.post(f"/movies/{movie_id}/favorite", headers=auth_headers)

        # Get favorites
        response = client.get("/movies/favorites/list", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) > 0

    def test_remove_from_favorites(self, client, auth_headers, sample_movie_data):
        """Test removing from favorites"""
        movie_id = sample_movie_data["movie"].id

        # Add to favorites
        client.post(f"/movies/{movie_id}/favorite", headers=auth_headers)

        # Remove from favorites
        response = client.delete(
            f"/movies/{movie_id}/favorite",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestMovieComments:
    """Test movie comments functionality"""

    def test_create_comment(self, client, auth_headers, sample_movie_data):
        """Test creating a comment"""
        movie_id = sample_movie_data["movie"].id
        response = client.post(
            f"/movies/{movie_id}/comments",
            headers=auth_headers,
            json={"content": "Great movie!"}
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"] == "Great movie!"

    def test_create_reply(self, client, auth_headers, sample_movie_data):
        """Test creating a reply to comment"""
        movie_id = sample_movie_data["movie"].id

        # Create parent comment
        comment_response = client.post(
            f"/movies/{movie_id}/comments",
            headers=auth_headers,
            json={"content": "Parent comment"}
        )
        comment_id = comment_response.json()["id"]

        # Create reply
        response = client.post(
            f"/movies/{movie_id}/comments",
            headers=auth_headers,
            json={
                "content": "Reply to comment",
                "parent_id": comment_id
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["parent_id"] == comment_id

    def test_get_comments(self, client, auth_headers, sample_movie_data):
        """Test getting movie comments"""
        movie_id = sample_movie_data["movie"].id

        # Create comment
        client.post(
            f"/movies/{movie_id}/comments",
            headers=auth_headers,
            json={"content": "Test comment"}
        )

        # Get comments
        response = client.get(
            f"/movies/{movie_id}/comments",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) > 0

    def test_update_own_comment(self, client, auth_headers, sample_movie_data):
        """Test updating own comment"""
        movie_id = sample_movie_data["movie"].id

        # Create comment
        comment_response = client.post(
            f"/movies/{movie_id}/comments",
            headers=auth_headers,
            json={"content": "Original content"}
        )
        comment_id = comment_response.json()["id"]

        # Update comment
        response = client.put(
            f"/movies/{movie_id}/comments/{comment_id}",
            headers=auth_headers,
            json={"content": "Updated content"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content"] == "Updated content"

    def test_delete_own_comment(self, client, auth_headers, sample_movie_data):
        """Test deleting own comment"""
        movie_id = sample_movie_data["movie"].id

        # Create comment
        comment_response = client.post(
            f"/movies/{movie_id}/comments",
            headers=auth_headers,
            json={"content": "To be deleted"}
        )
        comment_id = comment_response.json()["id"]

        # Delete comment
        response = client.delete(
            f"/movies/{movie_id}/comments/{comment_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestModeratorMovieManagement:
    """Test moderator movie CRUD operations"""

    def test_create_movie(self, client, moderator_headers, sample_movie_data):
        """Test creating movie as moderator"""
        response = client.post(
            "/moderator/movies",
            headers=moderator_headers,
            json={
                "name": "New Movie",
                "year": 2024,
                "time": 130,
                "imdb": 7.5,
                "votes": 5000,
                "description": "A new test movie",
                "price": 14.99,
                "certification_id": sample_movie_data["certification"].id,
                "genre_ids": [sample_movie_data["genre"].id],
                "director_ids": [sample_movie_data["director"].id],
                "star_ids": [sample_movie_data["star"].id]
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Movie"

    def test_create_movie_as_user(self, client, auth_headers, sample_movie_data):
        """Test creating movie as regular user (should fail)"""
        response = client.post(
            "/moderator/movies",
            headers=auth_headers,
            json={
                "name": "New Movie",
                "year": 2024,
                "time": 130,
                "imdb": 7.5,
                "votes": 5000,
                "description": "A new test movie",
                "price": 14.99,
                "certification_id": sample_movie_data["certification"].id
            }
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_movie(self, client, moderator_headers, sample_movie_data):
        """Test updating movie"""
        movie_id = sample_movie_data["movie"].id
        response = client.put(
            f"/moderator/movies/{movie_id}",
            headers=moderator_headers,
            json={"name": "Updated Movie Name"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Movie Name"

    def test_delete_movie(self, client, moderator_headers, sample_movie_data):
        """Test deleting movie"""
        movie_id = sample_movie_data["movie"].id
        response = client.delete(
            f"/moderator/movies/{movie_id}",
            headers=moderator_headers
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
