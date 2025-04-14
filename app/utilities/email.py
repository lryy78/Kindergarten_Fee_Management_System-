from app.models.models import Settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app import create_app  # Import db and create_app from your app package

# Create the app context to work with the database
app = create_app()

def get_setting_value(key: str):
    """Fetches the setting value for a given key from the database."""
    with app.app_context():  # Access the app context to query the database
        setting = Settings.query.filter_by(setting_key=key).first()
        if setting:
            return setting.setting_value
        raise ValueError(f"Setting with key '{key}' not found.")

def send_email(subject: str, body: str, receiver_email: str):
    """Sends an email using the SMTP settings from the database."""
    try:
        smtp_server = get_setting_value('smtp_server')
        smtp_port = int(get_setting_value('smtp_port'))
        sender_email = get_setting_value('contact_email')
        password = get_setting_value('smtp_email_password')

        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            print(f"Email sent successfully to {receiver_email}!")

    except Exception as e:
        print(f"Failed to send email: {e}")

