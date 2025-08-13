from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

def get_db():
      db = SessionLocal()
      try:
         yield db
      finally:
        db.close()
DATABASE_URL = "mysql+pymysql://root@localhost:3306/chatbot_rag"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
