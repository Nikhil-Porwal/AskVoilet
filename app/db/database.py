import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the path for the SQLite database file
# It will be created in the `storage/` directory
STORAGE_DIR = "storage"
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{STORAGE_DIR}/database.db"

# Create the SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    # `check_same_thread` is needed only for SQLite
    connect_args={"check_same_thread": False} 
)

# Create a SessionLocal class, which will be our database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models to inherit from
Base = declarative_base()

# Dependency to get a DB session in our endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables
def init_db():
    Base.metadata.create_all(bind=engine)