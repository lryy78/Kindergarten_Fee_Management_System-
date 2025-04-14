from decimal import Decimal
import os
from app import db
from flask import render_template, request, redirect, url_for
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, request
from flask_login import login_required
from app.routes.routes import role_required, app_name
from . import accountant
from app.models.models import User, StudentFeeAssignment, FeeRecord, PaymentStatus, Settings, FeeStructure
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INVOICE_DIR = os.path.join(BASE_DIR, '..', '..', 'archives',
                           'invoices')


@accountant.route('/fee_records')
@login_required
@role_required('4')
def fee_records():
    today = datetime.today().date()

    # Fetch all fee records with related data
    fee_records = (
        db.session.query(FeeRecord, StudentFeeAssignment,
                         User, FeeStructure, PaymentStatus)
        .join(StudentFeeAssignment, FeeRecord.fee_assignment_id == StudentFeeAssignment.fee_assignment_id)
        .join(User, StudentFeeAssignment.student_id == User.id)
        .join(FeeStructure, StudentFeeAssignment.structure_id == FeeStructure.structure_id)
        .join(PaymentStatus, FeeRecord.status_id == PaymentStatus.status_id, isouter=True)
        .all()
    )

    # Check and update overdue statuses
    for fee, _, _, _, _ in fee_records:
        # Calculate the difference in days between today and the due date
        overdue_days = (today - fee.due_date).days

        if overdue_days > 30 and fee.status_id != "status002":  # Only mark overdue if more than 30 days
            fee.status_id = "status003"  # Mark as overdue
            db.session.commit()
        elif overdue_days <= 30 and fee.status_id != "status002":
            fee.status_id = "status001"  # Mark as unpaid
            db.session.commit()

    return render_template("accountant/fee_records.html", fee_records=fee_records, app_name=app_name())


@accountant.route('/fee_records/delete/<fee_record_id>', methods=['POST'])
@login_required
@role_required('4')
def delete_fee_record(fee_record_id):
    fee_record = FeeRecord.query.get(fee_record_id)

    if not fee_record:
        return redirect(url_for('accountant.fee_records'))

    try:
        # Delete related fee assignment
        StudentFeeAssignment.query.filter_by(
            fee_assignment_id=fee_record.fee_assignment_id).delete()

        # Delete related invoice PDF file
        invoice_filename = f"invoice_{fee_record_id}.pdf"
        invoice_path = os.path.join(INVOICE_DIR, invoice_filename)
        if os.path.exists(invoice_path):
            os.remove(invoice_path)

        # Delete the fee record itself
        db.session.delete(fee_record)
        db.session.commit()

    except Exception as e:
        db.session.rollback()

    return redirect(url_for('accountant.fee_records'))


@accountant.route('/fee_records/add', methods=['GET', 'POST'])
@login_required
@role_required('4')
def add_fee_records():
    today = datetime.today().date()

    # Fetch students and fee structures
    students = User.query.filter_by(role_id="5").all()
    fee_structures = FeeStructure.query.all()

    # Fetch settings
    late_fee_setting = Settings.query.filter_by(
        setting_key='late_fee_amount').first()
    discount_setting = Settings.query.filter_by(
        setting_key='discount_amount').first()

    late_fee_increment = float(
        late_fee_setting.setting_value) if late_fee_setting and late_fee_setting.setting_value else 100.0
    discount_increment = float(
        discount_setting.setting_value) if discount_setting and discount_setting.setting_value else 10.0

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        structure_id = request.form.get('structure_id')
        penalty = float(request.form.get('penalty', 0))
        discount = float(request.form.get('discount', 0))
        due_date = datetime.strptime(
            request.form.get('due_date'), '%Y-%m-%d').date()

        # Generate a new Fee Record ID
        last_fee_record = FeeRecord.query.order_by(
            FeeRecord.fee_record_id.desc()).first()
        new_fee_record_id = f"fr{(int(last_fee_record.fee_record_id.replace('fr', '')) + 1) if last_fee_record else 1}"

        # Generate the corresponding Fee Assignment ID
        new_fee_assignment_id = new_fee_record_id.replace("fr", "fa")

        # Check if a StudentFeeAssignment with this ID already exists
        assignment = StudentFeeAssignment.query.filter_by(
            fee_assignment_id=new_fee_assignment_id).first()

        if not assignment:
            assignment = StudentFeeAssignment(
                fee_assignment_id=new_fee_assignment_id,
                student_id=student_id,
                structure_id=structure_id
            )
            db.session.add(assignment)
            db.session.flush()  # Flush to get the ID before creating FeeRecord

        # Fetch the tuition fee from the Fee Structure
        fee_structure = FeeStructure.query.get(structure_id)
        if not fee_structure:
            return redirect(url_for('accountant.add_fee_records'))

        tuition_fee = float(fee_structure.total_fee)
        total_amount = max(tuition_fee + penalty - discount, 0)

        # Determine initial status (Overdue or Not)
        today = datetime.today().date()
        initial_status = "status003" if due_date < today + timedelta(days=30) else "status001"

        # Create the Fee Record
        fee_record = FeeRecord(
            fee_record_id=new_fee_record_id,
            fee_assignment_id=assignment.fee_assignment_id,  # Use the same ID
            status_id=initial_status,
            date_assigned=today,
            due_date=due_date,
            amount_due=tuition_fee,
            late_fee_amount=penalty,
            discount_amount=discount,
            total_amount=total_amount,
            last_updated_date=today
        )

        db.session.add(fee_record)
        db.session.commit()

        return redirect(url_for('accountant.fee_records'))

    return render_template(
        'accountant/add_fee_record.html',
        students=students,
        fee_structures=fee_structures,
        app_name=app_name(),
        late_fee_increment=late_fee_increment,
        discount_increment=discount_increment
    )


@accountant.route('/fee_records/edit/<fee_record_id>', methods=['GET', 'POST'])
@login_required
@role_required('4')
def edit_fee_record(fee_record_id):
    fee_record = FeeRecord.query.filter_by(fee_record_id=fee_record_id).first()

    if not fee_record:
        return redirect(url_for('accountant.fee_records'))

    # Fetch assigned Fee Assignment
    assignment = StudentFeeAssignment.query.filter_by(
        fee_assignment_id=fee_record.fee_assignment_id).first()

    students = User.query.filter_by(role_id='5').all()
    fee_structures = FeeStructure.query.all()

    # Fetch settings values
    late_fee_setting = Settings.query.filter_by(
        setting_key='late_fee_amount').first()
    discount_setting = Settings.query.filter_by(
        setting_key='discount_amount').first()

    late_fee_increment = Decimal(
        late_fee_setting.setting_value) if late_fee_setting else Decimal(100.0)
    discount_increment = Decimal(
        discount_setting.setting_value) if discount_setting else Decimal(10.0)

    if request.method == 'POST':
        try:
            student_id = request.form.get("student_id")
            structure_id = request.form.get("structure_id")

            if student_id and structure_id:
                # Find the existing assignment by fee_assignment_id
                assignment = StudentFeeAssignment.query.filter_by(
                    fee_assignment_id=fee_record.fee_assignment_id  # Use existing ID
                ).first()

                if assignment:
                    # Update existing assignment details
                    assignment.student_id = student_id
                    assignment.structure_id = structure_id
                else:
                    # This should never happen unless the DB was modified manually
                    return redirect(url_for('accountant.fee_records'))

                fee_record.fee_assignment_id = assignment.fee_assignment_id  # Keep the same ID

                # Fetch total fee from structure
                fee_structure = FeeStructure.query.get(structure_id)
                fee_record.amount_due = fee_structure.total_fee if fee_structure else fee_record.amount_due

            # Update other fields
            fee_record.late_fee_amount = Decimal(
                request.form.get("penalty", fee_record.late_fee_amount))
            fee_record.discount_amount = Decimal(
                request.form.get("discount", fee_record.discount_amount))
            fee_record.total_amount = max(
                Decimal(fee_record.amount_due) + fee_record.late_fee_amount -
                fee_record.discount_amount, Decimal(0)
            )
            fee_record.due_date = datetime.strptime(
                request.form.get("due_date"), '%Y-%m-%d').date()
            fee_record.last_updated_date = datetime.today().date()

            db.session.commit()
            return redirect(url_for("accountant.fee_records"))

        except Exception as e:
            db.session.rollback()
            print(f"Error updating fee record: {e}")  # Debugging

    return render_template(
        "accountant/edit_fee_record.html",
        fee_record=fee_record,
        students=students,
        fee_structures=fee_structures,
        late_fee_increment=late_fee_increment,
        discount_increment=discount_increment
    )
