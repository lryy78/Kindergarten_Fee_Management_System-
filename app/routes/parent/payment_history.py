# app/routes/parent/payment_history.py
from flask import render_template, redirect, url_for, session
from flask_login import login_required, current_user
from app.routes.routes import role_required, app_name
from app.models.models import User, StudentFeeAssignment, FeeRecord, PaymentHistory
import logging
from . import parent
import os
from flask import send_from_directory
from app import db

@parent.route('/payment_history')
@login_required
@role_required('3')
def payment_history():
    try:
        # Get selected child from session
        user_specific_key = f'selected_child_id_{current_user.id}'
        selected_child_id = session.get(user_specific_key)

        if not selected_child_id:
            return redirect(url_for('parent.dashboard'))

        # Fetch the selected child's details
        selected_child = db.session.query(User).filter_by(id=selected_child_id).first()

        if not selected_child:
            return render_template('error.html', error_message="Selected child not found.")

        # Fetch all fee assignments for the selected child
        fee_assignments = db.session.query(StudentFeeAssignment).filter_by(student_id=selected_child.id).all()
        fee_assignment_ids = [assignment.fee_assignment_id for assignment in fee_assignments]

        if not fee_assignment_ids:
            return render_template('parent/payment_history.html', selected_child=selected_child, payment_history=[], app_name=app_name())

        # Fetch all fee records linked to those assignments
        fee_records = db.session.query(FeeRecord).filter(FeeRecord.fee_assignment_id.in_(fee_assignment_ids)).all()
        fee_record_ids = [record.fee_record_id for record in fee_records]

        if not fee_record_ids:
            return render_template('parent/payment_history.html', selected_child=selected_child, payment_history=[], app_name=app_name())

        # Fetch payment history for the selected child's fee records
        payment_history = (
            db.session.query(PaymentHistory)
            .filter(PaymentHistory.fee_record_id.in_(fee_record_ids))
            .order_by(PaymentHistory.payment_date.desc())
            .all()
        )

        # Pass the payment history to the template
        return render_template(
            'parent/payment_history.html',
            selected_child=selected_child,
            payment_history=payment_history, 
            app_name=app_name()
        )

    except Exception as e:
        logging.error(f"Error in fetching payment history: {e}")
        return render_template('error.html', error_message="An error occurred while fetching payment history.")


@parent.route('/download_receipt/<payment_history_id>')
@login_required
@role_required('3')
def download_receipt(payment_history_id):
    try:
        # Define the receipt directory
        receipt_dir = os.path.join(os.getcwd(), 'app', 'archives', 'receipts')

        # Construct the expected receipt filename
        receipt_filename = f'receipt_{payment_history_id}.pdf'
        receipt_path = os.path.join(receipt_dir, receipt_filename)


        # Check if the file exists
        if not os.path.exists(receipt_path):
            return render_template('error.html', error_message="Receipt not found.")

        # Send the file for download
        return send_from_directory(receipt_dir, receipt_filename, as_attachment=False)

    except Exception as e:
        return render_template('error.html', error_message=str(e))

