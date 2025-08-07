
from common.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Identity, Integer
from sqlalchemy.sql import func

class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(45))
    description: Mapped[str] = mapped_column(String(255))
    release_year: Mapped[int] = mapped_column()
    rating: Mapped[float] = mapped_column()
    is_imax: Mapped[bool] = mapped_column()
    price: Mapped[float] = mapped_column()
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"Movie(id={self.id!r}, name={self.name}, release_year={self.release_year}, rating={self.rating})"