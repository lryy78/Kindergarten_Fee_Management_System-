# app/routes/parent/fee_summary.py
from flask import render_template, redirect, url_for, session
from flask_login import login_required, current_user
from ..routes import role_required, app_name
from ...models.models import User, StudentFeeAssignment, FeeRecord
import datetime
from app import db
from . import parent

@parent.route('/fee_summary')
@login_required
@role_required('3')
def fee_summary():
    try:
        # Get the selected child from the session
        user_specific_key = f'selected_child_id_{current_user.id}'
        selected_child_id = session.get(user_specific_key)

        if not selected_child_id:
            return redirect(url_for('parent.dashboard'))

        # Fetch the selected child's details
        selected_child = db.session.query(User).filter_by(id=selected_child_id).first()

        if not selected_child:
            return render_template('error.html', error_message="Selected child not found.")

        # Fetch fee assignments related to the selected child
        fee_assignments = db.session.query(StudentFeeAssignment).filter_by(student_id=selected_child_id).all()

        # Fetch fee records for all the fee assignments
        fee_records = []
        for assignment in fee_assignments:
            records = db.session.query(FeeRecord).filter_by(fee_assignment_id=assignment.fee_assignment_id).all()
            fee_records.extend(records)

        # Calculate fee summaries
        total_pending_fees = sum(record.total_amount for record in fee_records if record.status_id == "status001")
        total_overdue_fees = sum(record.total_amount for record in fee_records if record.status_id == "status003")
        total_penalty = sum(record.late_fee_amount or 0 for record in fee_records if record.status_id == "status003")
        total_amount = total_pending_fees + total_overdue_fees

        # Ensure current_date is passed to the template
        current_date = datetime.datetime.now().date()

        return render_template(
            'parent/fee_summary.html',
            selected_child=selected_child,
            fee_records=fee_records,
            total_pending_fees=total_pending_fees,
            total_overdue_fees=total_overdue_fees,
            total_penalty=total_penalty,
            total_amount=total_amount,
            current_date=current_date,
            app_name=app_name()
        )
    except Exception as e:
        return render_template('error.html', error_message=str(e))

