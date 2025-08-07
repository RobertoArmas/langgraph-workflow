from sqlalchemy import create_engine
import os
import dotenv
dotenv.load_dotenv()

connection = f"mssql+pyodbc://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

engine = create_engine(connection)
engine.connect()

print("Connection successful!")

from common.db import DB

db = DB.instance()  # Ensure DB singleton is initialized

db.get_session()  # Test session creation
print("Session created successfully.")