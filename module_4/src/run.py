"""Entrypoint for running the Flask application."""

from app import create_app

# Create Flask app via factory
app = create_app()

if __name__ == "__main__":
    # Server: http://127.0.0.1:5000/
    app.run(debug=True)