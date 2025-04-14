# app/routes/parent/fee_record.py
from flask import render_template, redirect, url_for, session
from flask_login import login_required, current_user
from app.routes.routes import role_required, app_name
from app.models.models import User, StudentFeeAssignment, FeeRecord
import os
from flask import send_from_directory
from app import db
from . import parent

@parent.route('/fee_record')
@login_required
@role_required('3')
def fee_record():
    try:
        # Get selected child
        user_specific_key = f'selected_child_id_{current_user.id}'
        selected_child_id = session.get(user_specific_key)

        if not selected_child_id:
            return redirect(url_for('parent.dashboard'))

        selected_child = db.session.query(User).filter_by(id=selected_child_id).first()
        if not selected_child:
            return render_template('error.html', error_message="Selected child not found.", app_name=app_name())

        # Fetch fee assignments
        fee_assignments = db.session.query(StudentFeeAssignment).filter_by(student_id=selected_child_id).all()
        
        # Fetch fee records and check for invoice existence
        fee_records = []
        invoice_dir = os.path.join(os.getcwd(), 'app', 'archives', 'invoices')

        for assignment in fee_assignments:
            records = db.session.query(FeeRecord).filter_by(fee_assignment_id=assignment.fee_assignment_id).all()
            for record in records:
                invoice_filename = f'invoice_{record.fee_record_id}.pdf'
                record.invoice_exists = os.path.exists(os.path.join(invoice_dir, invoice_filename))
                fee_records.append(record)

        # Calculate totals
        total_amount_due = sum(record.amount_due for record in fee_records if record.status_id != "status002")
        total_penalty = sum(record.late_fee_amount for record in fee_records if record.status_id != "status002")
        total_amount_with_penalty = total_amount_due + total_penalty

        return render_template(
            'parent/fee_record.html',
            selected_child=selected_child,
            fee_records=fee_records,
            total_amount_due=total_amount_due,
            total_penalty=total_penalty,
            total_amount_with_penalty=total_amount_with_penalty,
            app_name=app_name()
        )
    except Exception as e:
        return render_template('error.html', error_message=str(e))


@parent.route('/download_invoice/<fee_record_id>')
@login_required
@role_required('3')
def download_invoice(fee_record_id):
    try:
        # Define the invoice directory
        invoice_dir = os.path.join(os.getcwd(), 'app','archives', 'invoices')

        # Construct the expected invoice filename
        invoice_filename = f'invoice_{fee_record_id}.pdf'
        invoice_path = os.path.join(invoice_dir, invoice_filename)

        # Check if the file exists
        if not os.path.exists(invoice_path):
            return render_template('error.html', error_message="Invoice not found.")

        # Send the file for download
        return send_from_directory(invoice_dir, invoice_filename, as_attachment=False)

    except Exception as e:
        return render_template('error.html', error_message=str(e))
