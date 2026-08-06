import sqlite3
import pandas as pd
import os

def main():
    db_path = "local_data.db"
    csv_path = "titles.csv"

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    print("Reading CSV...")
    df = pd.read_csv(csv_path)

    print(f"Connecting to database {db_path}...")
    conn = sqlite3.connect(db_path)

    print("Saving 'titles' table...")
    df.to_sql("titles", conn, if_exists="replace", index=False)

    print("Creating/replacing view 'netflix_movies'...")
    cursor = conn.cursor()
    cursor.execute("DROP VIEW IF EXISTS netflix_movies;")
    create_view_sql = """
    CREATE VIEW netflix_movies AS 
    SELECT 
        id AS show_id,
        type,
        title,
        NULL AS director,
        NULL AS cast,
        production_countries AS country,
        NULL AS date_added,
        release_year,
        age_certification AS rating,
        runtime AS duration,
        genres AS listed_in,
        description,
        -- Include original columns for compatibility
        id,
        age_certification,
        runtime,
        genres,
        production_countries,
        seasons,
        imdb_id,
        imdb_score,
        imdb_votes,
        tmdb_popularity,
        tmdb_score
    FROM titles;
    """
    cursor.execute(create_view_sql)
    conn.commit()

    # Verify
    cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view')")
    print("Tables and Views in SQLite:", cursor.fetchall())

    cursor.execute("SELECT COUNT(*) FROM netflix_movies")
    print("Total rows in netflix_movies view:", cursor.fetchone()[0])

    cursor.execute("SELECT COUNT(*) FROM titles")
    print("Total rows in titles table:", cursor.fetchone()[0])

    conn.close()
    print("Ingestion complete!")

if __name__ == "__main__":
    main()
