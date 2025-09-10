# run.py
# -------
# Entry point for the Flask application.
# Creates the app using create_app() and runs it on port 8080.

from app import create_app
app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
