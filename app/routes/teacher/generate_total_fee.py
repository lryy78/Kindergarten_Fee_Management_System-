from flask import render_template, request
from flask_login import login_required, current_user
from app import db
from app.models.models import User, FeeRecord, StudentFeeAssignment, PaymentStatus, ClassAssignment, Class
from app.routes.routes import role_required, app_name
from . import teacher

@teacher.route('/generate-total-fee')
@login_required
@role_required('2')
def generate_total_fee():
    selected_class = request.args.get('class_name', None)

    # Query to fetch fee details for students
    query = (
        db.session.query(
            User.first_name,
            User.last_name,
            Class.class_name,
            FeeRecord.total_amount,
            FeeRecord.status_id,
            PaymentStatus.status_name
        )
        .join(ClassAssignment, ClassAssignment.student_id == User.id)
        .join(Class, Class.class_id == ClassAssignment.class_id)
        .join(StudentFeeAssignment, StudentFeeAssignment.student_id == User.id)
        .join(FeeRecord, FeeRecord.fee_assignment_id == StudentFeeAssignment.fee_assignment_id)
        .join(PaymentStatus, PaymentStatus.status_id == FeeRecord.status_id)
        .filter(ClassAssignment.class_id.in_(
            db.session.query(ClassAssignment.class_id)
            .filter(ClassAssignment.teacher_id == current_user.id)
        ))
    )

    # Filter by selected class if provided
    if selected_class:
        query = query.filter(Class.class_name == selected_class)

    # Fetch all matching records
    fee_records = query.all()

    # Compute total collected amount and total fee recorded based on class selection
    filtered_fee_records = fee_records if not selected_class else [record for record in fee_records if record.class_name == selected_class]

    total_collected_fee = sum(record.total_amount for record in filtered_fee_records if record.status_name == 'Paid')
    total_fee_recorded = sum(record.total_amount for record in filtered_fee_records)

    # Prepare student fee data
    students = {}
    for record in filtered_fee_records:
        student_name = f"{record.first_name} {record.last_name}"
        if student_name not in students:
            students[student_name] = {
                "class_name": record.class_name,
                "total_fee": 0.0,
                "collected_fee": 0.0
            }

        students[student_name]["total_fee"] += float(record.total_amount) if record.total_amount else 0.0
        if record.status_name == "Paid":
            students[student_name]["collected_fee"] += float(record.total_amount)

    # Convert dictionary to list
    student_list = [{"name": name, **data} for name, data in students.items()]

    # Fetch available class names for dropdown
    class_names = (
        db.session.query(Class.class_name)
        .join(ClassAssignment, ClassAssignment.class_id == Class.class_id)
        .filter(ClassAssignment.teacher_id == current_user.id)
        .distinct()
        .all()
    )
    class_names = [class_name[0] for class_name in class_names]

    # Set the title dynamically based on selection
    fee_summary_title = f"Total Fee for Class {selected_class}" if selected_class else "Total Fee for All Classes"

    return render_template(
        'teacher/total_fee.html',
        students=student_list,
        total_collected_fee=total_collected_fee,
        total_fee_recorded=total_fee_recorded,
        class_names=class_names,
        selected_class=selected_class,
        fee_summary_title=fee_summary_title,
        app_name=app_name()
    )
