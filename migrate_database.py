from app import app, db
import sqlite3

# Add new columns to sellers table
with app.app_context():
    conn = sqlite3.connect('instance/retrix.db')
    cursor = conn.cursor()
    
    # Check if store_name column exists
    cursor.execute("PRAGMA table_info(sellers)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    if 'store_name' not in column_names:
        cursor.execute("ALTER TABLE sellers ADD COLUMN store_name VARCHAR(100) NOT NULL DEFAULT ''")
        print("Added store_name column")
    
    if 'unique_code' not in column_names:
        cursor.execute("ALTER TABLE sellers ADD COLUMN unique_code VARCHAR(6)")
        print("Added unique_code column")
        # Create unique index separately
        cursor.execute("CREATE UNIQUE INDEX idx_sellers_unique_code ON sellers(unique_code)")
        print("Created unique index for unique_code")
    
    conn.commit()
    conn.close()
    print("Database migration completed successfully!")
