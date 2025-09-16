# module_3/run.py
from app import create_app

# Create the Flask app using our factory
app = create_app()

if __name__ == "__main__":
    # server: http://127.0.0.1:5000/
    app.run(debug=True)