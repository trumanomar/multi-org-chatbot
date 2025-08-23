#!/usr/bin/env python3
"""
Setup script for chat history functionality
This script ensures all necessary database tables are created.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.DB.db import Base, engine
from app.Models import tables

def setup_chat_history():
    """Create all database tables including chat history tables"""
    print("Setting up chat history database tables...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # Verify specific tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        required_tables = ['chat_sessions', 'chat_messages', 'users', 'domains']
        existing_tables = inspector.get_table_names()
        
        print("\nVerifying required tables:")
        for table in required_tables:
            if table in existing_tables:
                print(f"✅ {table} table exists")
            else:
                print(f"❌ {table} table missing")
                return False
        
        print("\n🎉 Chat history setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up chat history: {e}")
        return False

if __name__ == "__main__":
    success = setup_chat_history()
    if not success:
        sys.exit(1)
