from movie_seed import MovieFactory

def seed_movies(count=10):
    """Seed the database with a specified number of movies."""
    movies = MovieFactory.create_batch(count)

    print(f"Created {len(movies)} movies.")

if __name__ == "__main__":
    seed_movies(10)
    print("Movies seeded successfully.")