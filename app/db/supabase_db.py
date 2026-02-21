import os
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Use environment variables for Supabase connection (Standard Supabase credentials)
# Expected variables: DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "db_host")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

def get_connection():
    """Establishes a connection to the Supabase PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error connecting to database: {error}")
        return None

def add_recipe(name, ingredients, time, steps):
    """Inserts a new recipe into the recipes table."""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        
        # SQL for creating the table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                ingredients JSONB,
                time INTEGER,
                steps JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Execute the INSERT statement
        # Note: ingredients and steps should be passed as JSON-compatible objects (e.g., lists)
        import json
        cur.execute(
            "INSERT INTO recipes (name, ingredients, time, steps) VALUES (%s, %s, %s, %s) RETURNING id",
            (name, json.dumps(ingredients), time, json.dumps(steps))
        )
        recipe_id = cur.fetchone()[0]

        # Commit the changes to the database
        conn.commit()
        print(f"Recipe '{name}' inserted successfully with ID: {recipe_id}")
        return recipe_id

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        conn.rollback()
        return None

    finally:
        if conn is not None:
            cur.close()
            conn.close()

if __name__ == "__main__":
    # Test script for local verification
    test_recipe = {
        "name": "Supabase Test Recipe",
        "ingredients": ["1 cup knowledge", "2 tbsp effort"],
        "time": 10,
        "steps": ["Step 1: Prep the DB", "Step 2: Win the hackathon"]
    }
    add_recipe(**test_recipe)
