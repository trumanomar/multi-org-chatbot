from app.DB.db import Base, engine
from app.Models import tables  

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")
