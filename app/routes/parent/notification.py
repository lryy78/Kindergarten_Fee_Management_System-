# app/routes/parent/notification.py
from flask import jsonify, session
from flask_login import login_required, current_user
from app.models.models import Notification
from app import db
from . import parent

@parent.route('/ajax_notifications', methods=['GET'])
@login_required
def ajax_notifications():
    selected_child_id = session.get(f'selected_child_id_{current_user.id}')
    
    # If no child is selected, return an error message
    if not selected_child_id:
        return jsonify({"error": "No child selected"}), 400

    # Fetch the notifications for the selected child
    notifications = (
        db.session.query(Notification)
        .filter(Notification.student_id == selected_child_id)
        .order_by(Notification.timestamp.desc())
        .all()
    )

    # Prepare the notifications HTML in the desired format
    notifications_html = ""
    if notifications:
        for notification in notifications:
            # Get the teacher's name
            teacher_name = f"{notification.teacher.first_name} {notification.teacher.last_name}"

            # Format timestamp
            timestamp = notification.timestamp
            date = timestamp.strftime('%Y-%m-%d')  # Format as Date
            time = timestamp.strftime('%I:%M %p')  # Format as Time

            # Prepare message text, handle "Payment Confirmation" differently
            message_text = notification.message_text
            if notification.message_type == "Payment Confirmation":
                # Split message into lines and take only the first two
                message_lines = [line.strip() for line in message_text.split("\n") if line.strip()]
                message_text = "\n".join(message_lines[:2])  # Ensure line breaks work in HTML

            # Prepare HTML for the notification
            notifications_html += f"""
                <li class='list-group-item' style='background-color: #f0f8ff;'>
                    <p style='text-align:center; text-transform: uppercase; font-size: 17px; margin-bottom: 10px;'>
                        <strong>{notification.message_type}</strong>
                    </p>
                    <div style='display: flex; justify-content: space-between; font-size: 13px;'>
                        <span><strong>Date:</strong> {date}</span>
                        <span><strong>Time:</strong> {time}</span>
                        <span><strong>Sent by:</strong> Teacher {teacher_name}</span>
                    </div>
                    <p style='margin-top: 10px; font-size: 15px;'>{message_text}</p>
                </li>
            """
    else:
        notifications_html = """
            <div class="alert alert-warning text-center shadow-sm">
                <i class="bi bi-exclamation-circle"></i> No notifications available.
            </div>
        """
    return jsonify({"notifications_html": notifications_html})
