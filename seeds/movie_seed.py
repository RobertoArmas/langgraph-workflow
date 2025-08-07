import factory
from factory.helpers import lazy_attribute
from faker import Faker
from common.models.movie import Movie
from common.db import DB

fake = Faker()

class MovieFactory(factory.alchemy.SQLAlchemyModelFactory):

    class Meta:
        model = Movie
        sqlalchemy_session = DB.instance().get_session()
        sqlalchemy_session_persistence = 'commit'


    @lazy_attribute
    def name(self):
        s = fake.sentence(nb_words=3)
        return s.rstrip(".")[:45]   # also enforces your 45-char limit
    
    description = factory.faker.Faker('text', max_nb_chars=200)
    release_year = factory.faker.Faker('year')
    rating = factory.faker.Faker('pyfloat', left_digits=1, right_digits=1, positive=True, min_value=1, max_value=10)
    is_imax = factory.faker.Faker('boolean')
    price = factory.faker.Faker('pydecimal', left_digits=2, right_digits=2, positive=True, min_value=5.00, max_value=20.00)