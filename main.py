from app import create_app, db
from app.utilities.email import send_email

app = create_app()

if __name__ == "__main__":
    # Run Flask in production mode
    app.run(host="0.0.0.0", port=10000, debug=False)
