from common.db.db import DB
from common.models.movie import Movie


class MovieRepository:

    db: DB

    def __init__(self):
        self.db = DB.instance()

    def get(self, movie_id: int) -> Movie | None:
        with self.db.get_session() as session:
            movie = session.query(Movie).get(movie_id)
            return movie

    def search_by_text(self, query: str) -> list[Movie]:
        with self.db.get_session() as session:
            # description or name
            movies = session.query(Movie).filter(
                Movie.description.ilike(f"%{query}%") | Movie.name.ilike(f"%{query}%")
            ).all()
            return movies

    def get_by_name(self, name: str) -> Movie | None:
        with self.db.get_session() as session:
            movie = session.query(Movie).filter(Movie.name == name).first()
            return movie

    def all(self):
        with self.db.get_session() as session:
            movies = session.query(Movie).all()
            return movies
    
    def save(self, movie: Movie):
        with self.db.get_session() as session:
            old_movie = session.get(Movie, movie.id)  # Ensure the movie exists
            if old_movie:
                for column in Movie.__table__.columns.keys():
                    if column != "id":
                        setattr(old_movie, column, getattr(movie, column))
            session.commit()

    def create(self, movieData: dict) -> int:
        with self.db.get_session() as session:
            movie = Movie(**movieData)
            session.add(movie)
            session.flush()
            movie_id = movie.id
            session.commit()
            return movie_id

    def delete(self, movie_id: int):
        with self.db.get_session() as session:
            movie = session.query(Movie).get(movie_id)
            if movie:
                session.delete(movie)
                session.commit()
