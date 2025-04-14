from flask import render_template, request
from flask_login import login_required, current_user
from app import db
from app.models.models import User, FeeRecord, StudentFeeAssignment, PaymentStatus, ClassAssignment, Class
from app.routes.routes import role_required, app_name
from . import teacher

# View Fee Status Route
@teacher.route('/fee-status')
@login_required
@role_required('2')
def fee_status():
    # Get the class name from the query parameters (if it exists)
    selected_class = request.args.get('class_name', None)
    
    # Fetch student fee records with related information
    query = (
        db.session.query(
            User.first_name, 
            User.last_name, 
            Class.class_name, 
            FeeRecord.amount_due, 
            FeeRecord.total_amount, 
            PaymentStatus.status_name,
            FeeRecord.date_assigned  # Use date_assigned here
        )
        .join(ClassAssignment, ClassAssignment.student_id == User.id)  # Join to filter by teacher's classes
        .join(Class, Class.class_id == ClassAssignment.class_id)
        .join(StudentFeeAssignment, StudentFeeAssignment.student_id == User.id)
        .join(FeeRecord, FeeRecord.fee_assignment_id == StudentFeeAssignment.fee_assignment_id)
        .join(PaymentStatus, PaymentStatus.status_id == FeeRecord.status_id)
        .filter(ClassAssignment.class_id.in_(
            db.session.query(ClassAssignment.class_id)
            .filter(ClassAssignment.teacher_id == current_user.id)  # Only classes assigned to the teacher
        ))
    )
    
    # If class_name is provided, filter the records by class
    if selected_class:
        query = query.filter(Class.class_name == selected_class)

    fee_data = query.all()

    # Format data for template, include date_assigned
    payments = [{
        "student_name": f"{record.first_name} {record.last_name}",
        "class_name": record.class_name,
        "amount_due": record.amount_due,
        "paid_amount": record.total_amount,
        "payment_status": record.status_name,
        "date_assigned": record.date_assigned.strftime('%Y-%m-%d')  # Format the date as required
    } for record in fee_data]

    # Calculate the total number of students and percentage for each status
    total_students = len(fee_data)
    paid_count = sum(1 for record in fee_data if record.status_name == 'Paid')
    pending_count = sum(1 for record in fee_data if record.status_name == 'Pending')
    overdue_count = sum(1 for record in fee_data if record.status_name == 'Overdue')

    paid_percentage = (paid_count / total_students * 100) if total_students else 0
    pending_percentage = (pending_count / total_students * 100) if total_students else 0
    overdue_percentage = (overdue_count / total_students * 100) if total_students else 0

    # Fetch available class names for the dropdown, ensuring no duplicates and filtering by teacher's assignments
    class_names = (
        db.session.query(Class.class_name)
        .join(ClassAssignment)
        .filter(ClassAssignment.teacher_id == current_user.id)
        .distinct()
        .all()
    )
    class_names = [class_name[0] for class_name in class_names]  # Extract class names

    return render_template(
        'teacher/fee_status.html', 
        payments=payments, 
        class_names=class_names, 
        selected_class=selected_class,
        total_students=total_students,
        paid_percentage=paid_percentage,
        pending_percentage=pending_percentage,
        overdue_percentage=overdue_percentage, 
        app_name=app_name()
    )
