from common.db.db import DB
from common.models.movie import Movie



class MovieRepository:
    """
    Repository class for managing Movie entities in the database.
    Provides CRUD operations and search functionality for movies.
    """

    db: DB

    def __init__(self):
        """
        Initializes the MovieRepository with a singleton DB instance.
        """
        self.db = DB.instance()

    def get(self, movie_id: int) -> Movie | None:
        """
        Retrieve a movie by its ID.
    
        Arguments:
            movie_id: The ID of the movie to retrieve.
        Returns:
            Movie object if found, otherwise None.
        """
        with self.db.get_session() as session:
            movie = session.query(Movie).get(movie_id)
            return movie

    def search_by_text(self, query: str) -> list[Movie]:
        """
        Search for movies whose name or description contains the given query string (case-insensitive).

        Arguments:
            query: The text to search for in movie names or descriptions.
        Returns:
            List of matching Movie objects.
        """
        with self.db.get_session() as session:
            # Search by description or name using ILIKE for case-insensitive matching
            movies = session.query(Movie).filter(
                Movie.description.ilike(f"%{query}%") | Movie.name.ilike(f"%{query}%")
            ).all()
            return movies

    def get_by_name(self, name: str) -> Movie | None:
        """
        Retrieve a movie by its exact name.

        Arguments:
            name: The exact name of the movie to retrieve.
        Returns:
            Movie object if found, otherwise None.
        """
        with self.db.get_session() as session:
            movie = session.query(Movie).filter(Movie.name == name).first()
            return movie

    def all(self) -> list[Movie]:
        """
        Retrieve all movies from the database.

        Returns:
            List of all Movie objects in the database.
        """
        with self.db.get_session() as session:
            movies = session.query(Movie).all()
            return movies
    
    def save(self, movie: Movie):
        """
        Update an existing movie in the database with new values.
        Only updates fields other than 'id'.
        Commits the transaction if the movie exists.

        Arguments:
            movie: The Movie object with updated values.
        Returns:
            None
        """
        with self.db.get_session() as session:
            old_movie = session.get(Movie, movie.id)  # Ensure the movie exists
            if old_movie:
                # Update all columns except 'id'
                for column in Movie.__table__.columns.keys():
                    if column != "id":
                        setattr(old_movie, column, getattr(movie, column))
                session.commit()

    def create(self, movieData: dict) -> int:
        """
        Create a new movie in the database using the provided data dictionary.

        Arguments:
            movieData: Dictionary containing movie attributes.
        Returns:
            The ID of the newly created movie.
        """
        with self.db.get_session() as session:
            movie = Movie(**movieData)
            session.add(movie)
            session.flush()  # Assigns an ID to the movie
            movie_id = movie.id
            session.commit()
            return movie_id

    def delete(self, movie_id: int):
        """
        Delete a movie from the database by its ID.
        Commits the transaction if the movie exists.

        Arguments:
            movie_id: The ID of the movie to delete.
        Returns:
            None
        """
        with self.db.get_session() as session:
            movie = session.query(Movie).get(movie_id)
            if movie:
                session.delete(movie)
                session.commit()
