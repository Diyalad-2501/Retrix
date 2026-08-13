from app import app

if __name__ == '__main__':
    # debug=True is fine for local development
    # For production (Render), gunicorn is used via Procfile
    app.run(debug=True)
