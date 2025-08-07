from common.db.db import DB
from common.models.movie import Movie


class MovieRepository:

    db: DB

    def __init__(self):
        self.db = DB.instance()

    def get(self, movie_id: int) -> Movie | None:
        session = self.db.get_session()
        movie = session.query(Movie).get(movie_id)
        session.close()
        return movie

    def search_by_text(self, query: str) -> list[Movie]:
        session = self.db.get_session()
        # description or name
        movies = session.query(Movie).filter(
            Movie.description.ilike(f"%{query}%") | Movie.name.ilike(f"%{query}%")
        ).all()
        session.close()
        return movies

    def get_by_name(self, name: str) -> Movie | None:
        session = self.db.get_session()
        movie = session.query(Movie).filter(Movie.name == name).first()
        session.close()
        return movie

    def all(self):
        session = self.db.get_session()
        movies = session.query(Movie).all()
        session.close()
        return movies
    
    def save(self, movie: Movie):
        session = self.db.get_session()
        old_movie = session.get(Movie, movie.id)  # Ensure the movie exists
        if old_movie:
            for column in Movie.__table__.columns.keys():
                if column != "id":
                    setattr(old_movie, column, getattr(movie, column))
        session.commit()
        session.close()

    def create(self, movie: Movie):
        session = self.db.get_session()
        session.add(movie)
        session.commit()
        session.close()

    def delete(self, movie_id: int):
        session = self.db.get_session()
        movie = session.query(Movie).get(movie_id)
        if movie:
            session.delete(movie)
            session.commit()
        session.close()
