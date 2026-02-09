from app import app, db
import sqlite3

# Add profile_icon and profile_photo columns to sellers table
with app.app_context():
    conn = sqlite3.connect('instance/retrix.db')
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(sellers)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    if 'profile_icon' not in column_names:
        cursor.execute("ALTER TABLE sellers ADD COLUMN profile_icon VARCHAR(50) DEFAULT 'fa-user'")
        print("Added profile_icon column to sellers table")
    else:
        print("profile_icon column already exists")
    
    if 'profile_photo' not in column_names:
        cursor.execute("ALTER TABLE sellers ADD COLUMN profile_photo VARCHAR(200)")
        print("Added profile_photo column to sellers table")
    else:
        print("profile_photo column already exists")
    
    conn.commit()
    conn.close()
    print("Database migration completed successfully")
