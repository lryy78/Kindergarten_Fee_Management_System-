# app/routes/parent/notification_dashboard.py
from flask import flash, render_template, redirect, url_for, session
from flask_login import login_required, current_user
from app.routes.routes import role_required, app_name
from app.models.models import User, Notification
from app import db
from . import parent

@parent.route('/notification_dashboard', methods=['GET'])
@login_required
def notification_dashboard():
    # Get the selected child's ID from the session
    selected_child_id = session.get(f'selected_child_id_{current_user.id}')
    
    if not selected_child_id:
        flash('No child selected.', 'danger')
        return redirect(url_for('parent.dashboard'))

    # Fetch the selected child's details
    selected_child = db.session.query(User).filter(User.id == selected_child_id).first()

    if not selected_child:
        flash('Selected child not found.', 'danger')
        return redirect(url_for('parent.dashboard'))

    # Fetch notifications for the selected child
    notifications = (
        db.session.query(Notification)
        .filter(Notification.student_id == selected_child_id)
        .order_by(Notification.timestamp.desc())
        .all()
    )

    # Format notifications
    formatted_notifications = []
    for notification in notifications:
        # Get the teacher's name
        teacher_name = f"{notification.teacher.first_name} {notification.teacher.last_name}"

        # Get the student's name
        student_name = f"{notification.student.first_name} {notification.student.last_name}"

        # Format the timestamp into date and time
        timestamp = notification.timestamp
        date = timestamp.strftime('%Y-%m-%d')  # Format as Date
        time = timestamp.strftime('%I:%M %p')  # Format as Time

        # Process message_text for Payment Confirmation
        if notification.message_type == "Payment Confirmation":
            # Split the message into lines and remove empty lines
            message_lines = [line.strip() for line in notification.message_text.strip().split("\n") if line.strip()]
            
            # First two lines
            first_two_lines = "\n".join(message_lines[:2])
            
            # Lines after the first two
            remaining_lines = message_lines[2:]
        else:
            # For other message types, keep the entire message
            first_two_lines = notification.message_text
            remaining_lines = []

        # Append the formatted notification to the list
        formatted_notifications.append({
            "message_type": notification.message_type,
            "first_two_lines": first_two_lines,
            "remaining_lines": remaining_lines,
            "date": date,
            "time": time,
            "teacher_name": teacher_name,
            "student_name": student_name,
        })

    # Pass the formatted notifications and selected child to the template
    return render_template(
        'parent/notification_dashboard.html',
        notifications=formatted_notifications,
        selected_child=selected_child, 
        app_name=app_name()
    )