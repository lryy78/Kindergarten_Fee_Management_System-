from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
import datetime
import pytz
from app import db
from app.models.models import User, FeeRecord, StudentFeeAssignment, PaymentStatus, ClassAssignment, Class
from app.models.models import Notification, MessageTemplate
from flask import jsonify
from app.routes.routes import role_required, app_name
from . import teacher

# Fetch students based on class or all assigned to teacher
@teacher.route('/get_students', methods=['POST'])
@login_required
@role_required('2')  # Ensure the user has the teacher role
def get_students():
    data = request.get_json()
    class_name = data.get("class_name")

    # Subquery to get class IDs assigned to the current teacher
    teacher_classes = (
        db.session.query(ClassAssignment.class_id)
        .filter(ClassAssignment.teacher_id == current_user.id)
        .scalar_subquery()
    )

    # Query to get students assigned to the teacher's classes
    query = (
        db.session.query(User.id, User.first_name, User.last_name)
        .join(ClassAssignment, ClassAssignment.student_id == User.id)
        .filter(ClassAssignment.class_id.in_(teacher_classes))
    )

    # Filter by class name if provided and not "all"
    if class_name and class_name != "all":
        query = query.join(Class, Class.class_id == ClassAssignment.class_id).filter(Class.class_name == class_name)

    students = query.all()
    if not students:
        return jsonify({"students": []})

    return jsonify({
        "students": [{"id": student.id, "name": f"{student.first_name} {student.last_name}"} for student in students]
    })


@teacher.route('/send-reminders', methods=['GET', 'POST'])
@login_required
@role_required('2')
def send_reminders():
    if request.method == 'POST':
        message_template_id = request.form.get('messageTemplate')  
        search_student = request.form.get('searchStudent')
        selected_class = request.form.get('class_name')
        custom_message = request.form.get('Message')  
        message_type = request.form.get('messageType')

        template = None
        if message_template_id:
            template = db.session.query(MessageTemplate).filter_by(message_temp_id=message_template_id).first()

        original_message_text = template.template_text if template else custom_message

        students_query = (
            db.session.query(User)
            .join(ClassAssignment, ClassAssignment.student_id == User.id)
            .filter(ClassAssignment.class_id.in_(
                db.session.query(ClassAssignment.class_id)
                .filter(ClassAssignment.teacher_id == current_user.id)
            ))
        )

        if selected_class and selected_class != "all":
            students_query = students_query.filter(Class.class_name == selected_class)

        if search_student and search_student != "all":
            students_query = students_query.filter(User.id == search_student)

        students = students_query.all()

        if not students:
            flash('No students found or selected!', 'danger')
            return redirect(url_for('teacher.send_reminders'))

        last_notification = db.session.query(Notification).order_by(Notification.notification_id.desc()).first()
        last_number = int(last_notification.notification_id.replace('notif', '')) if last_notification else 0  

        batch_size = 5
        notifications = []
        skipped_students = 0  # Counter for students skipped due to missing statuses

        for index, student in enumerate(students, 1):
            last_number += 1  
            notification_id = f'notif{last_number}'  

            while db.session.query(Notification).filter_by(notification_id=notification_id).first():
                last_number += 1
                notification_id = f'notif{last_number}'  

            message_text = original_message_text  

            if message_template_id:  
                fee_record = (
                    db.session.query(FeeRecord)
                    .join(StudentFeeAssignment, StudentFeeAssignment.fee_assignment_id == FeeRecord.fee_assignment_id)
                    .join(PaymentStatus, PaymentStatus.status_id == FeeRecord.status_id)
                    .filter(StudentFeeAssignment.student_id == student.id)
                    .order_by(FeeRecord.due_date.desc())
                    .first()
                )

                if not fee_record:
                    skipped_students += 1
                    continue  

                fee_status = fee_record.status.status_id  

                # ✅ Ensure correct template is used for the respective fee status
                if fee_status == 'status001':  # Unpaid Fees
                    if template.message_temp_id != 'template1':  
                        skipped_students += 1
                        continue  # Skip if wrong template is selected
                    message_text = template.template_text.replace('{amount}', str(fee_record.total_amount))
                    message_text = message_text.replace('{date}', str(fee_record.due_date.strftime('%Y-%m-%d')))
                
                elif fee_status == 'status003':  # Overdue Fees
                    if template.message_temp_id != 'template2':  
                        skipped_students += 1
                        continue  # Skip if wrong template is selected
                    message_text = template.template_text.replace('{amount}', str(fee_record.total_amount))
                    message_text = message_text.replace('{date}', str(fee_record.due_date.strftime('%Y-%m-%d')))
                else:
                    skipped_students += 1
                    continue  # Skip if the status is not relevant

            malaysia_tz = pytz.timezone('Asia/Kuala_Lumpur')
            malaysia_time = datetime.datetime.now(malaysia_tz)

            notification = Notification(
                notification_id=notification_id,
                teacher_id=current_user.id,
                student_id=student.id,
                message_type=message_type,
                message_text=message_text,
                timestamp=malaysia_time
            )

            notifications.append(notification)
            db.session.add(notification)

            if index % batch_size == 0:
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error sending reminders: {e}', 'danger')
                    return redirect(url_for('teacher.send_reminders'))

        try:
            db.session.commit()
            if skipped_students > 0:
                if search_student and search_student != "all" and len(students) == 1:
                    student = students[0]  # Get the single student object
                    flash(f'Student "{student.first_name} {student.last_name}" does not have the required fee status or template mismatch.', 'warning')
                else:
                    flash(f'Some students were skipped due to missing fee statuses or template mismatches.', 'warning')
            else:
                flash('Reminders sent successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error sending reminders: {e}', 'danger')

        return redirect(url_for('teacher.send_reminders'))

    class_names = db.session.query(Class.class_name).join(ClassAssignment).filter(
        ClassAssignment.teacher_id == current_user.id
    ).distinct().all()
    class_names = [class_name[0] for class_name in class_names]

    templates = db.session.query(MessageTemplate).filter(MessageTemplate.message_temp_id != 'template3').all()

    return render_template('teacher/send_reminders.html', class_names=class_names, templates=templates, app_name=app_name())
   