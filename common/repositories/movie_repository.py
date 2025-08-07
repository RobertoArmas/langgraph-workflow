from common.db.db import DB
from common.models.movie import Movie


class MovieRepository:

    db: DB

    def __init__(self):
        self.db = DB.instance()

    def all(self):
        session = self.db.get_session()
        movies = session.query(Movie).all()
        session.close()
        return movies