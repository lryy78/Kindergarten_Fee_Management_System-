# app/routes/parent/make_payment.py
from flask import render_template, redirect, url_for, session, flash, request
from flask_login import login_required, current_user
from ..routes import role_required, app_name
from app.models.models import User, StudentFeeAssignment, FeeRecord, PaymentHistory, Notification, MessageTemplate, ClassAssignment, Settings
import datetime
import pytz
import os
from weasyprint import HTML
from app import db
from . import parent

@parent.route('/make_payment', methods=['GET', 'POST'])
@login_required
@role_required('3')
def make_payment():
    try:
        user_specific_key = f'selected_child_id_{current_user.id}'
        selected_child_id = session.get(user_specific_key)

        if not selected_child_id:
            return redirect(url_for('parent.dashboard'))

        selected_child = db.session.query(User).filter_by(id=selected_child_id).first()
        if not selected_child:
            return render_template('error.html', error_message="Selected child not found.")

        unpaid_fees = (
            db.session.query(FeeRecord)
            .join(StudentFeeAssignment)
            .filter(
                StudentFeeAssignment.student_id == selected_child.id,
                FeeRecord.status_id.in_(['status001', 'status003'])
            )
            .all()
        )

        no_payment_due = len(unpaid_fees) == 0
        fee_record = unpaid_fees[0] if not no_payment_due else None
        total_penalty = fee_record.late_fee_amount if fee_record else 0

        if request.method == 'POST':
            fee_payment_id = request.form.get('fee_payment')
            payment_method = request.form.get('payment_method')
            message_type = "Payment Confirmation"  # Fixed message type

            selected_fee_record = db.session.query(FeeRecord).filter_by(fee_record_id=fee_payment_id).first()
            if not selected_fee_record:
                flash('Invalid fee selection.', 'danger')
                return redirect(url_for('parent.make_payment'))

            if not payment_method:
                flash('Please select a payment method.', 'danger')
                return redirect(url_for('parent.make_payment'))

            last_payment = db.session.query(PaymentHistory).order_by(PaymentHistory.history_id.desc()).first()
            new_number = int(last_payment.history_id[2:]) + 1 if last_payment else 1
            new_payment_id = f'ph{new_number}'

            # Malaysia Time (UTC+8)
            malaysia_tz = pytz.timezone('Asia/Kuala_Lumpur')
            malaysia_time = datetime.datetime.now(malaysia_tz)

            new_payment = PaymentHistory(
                history_id=new_payment_id,
                fee_record_id=selected_fee_record.fee_record_id,
                amount_paid=selected_fee_record.total_amount,
                payment_method=payment_method,
                payment_date=malaysia_time,  
            )

            selected_fee_record.status_id = 'status002'
            selected_fee_record.last_updated_date = malaysia_time  # Ensure MYT is stored

            db.session.add(new_payment)
            db.session.commit()

            # Generate PDF Receipt
            generate_receipt_pdf(new_payment_id, selected_child, selected_fee_record, payment_method)

            ### Add Notification for the Parent ###
            template = db.session.query(MessageTemplate).filter_by(message_temp_id='template3').first()
            template_text = template.template_text if template else "Payment received successfully."

            # Get Teacher ID and Class Name
            student_class_assignment = db.session.query(ClassAssignment).filter_by(student_id=selected_child.id).first()
            teacher_id = student_class_assignment.teacher_id if student_class_assignment else None
            class_name = student_class_assignment.class_.class_name if student_class_assignment and student_class_assignment.class_ else "Unknown Class"

            # Get Fee Type
            fee_assignment = db.session.query(StudentFeeAssignment).join(FeeRecord).filter(
                StudentFeeAssignment.student_id == selected_child.id,
                FeeRecord.fee_record_id == selected_fee_record.fee_record_id
            ).first()
            fee_type = fee_assignment.structure.description if fee_assignment else "Unknown Fee Type"

            # Replace placeholders in message text
            message_text = template_text.format(
                amount=selected_fee_record.total_amount,
                child_name=f"{selected_child.first_name} {selected_child.last_name}",
                timestamp=malaysia_time.strftime('%Y-%m-%d %I:%M %p'),
                payment_history_id=new_payment_id,
                class_name=class_name,
                fee_type=fee_type,
                amount_paid=selected_fee_record.total_amount,
                payment_method=payment_method
            )

            # Generate Notification ID
            last_notification = db.session.query(Notification).order_by(Notification.notification_id.desc()).first()
            last_number = int(last_notification.notification_id[5:]) if last_notification else 0  
            notification_id = f'notif{last_number + 1}'

            while db.session.query(Notification).filter_by(notification_id=notification_id).first():
                last_number += 1  
                notification_id = f'notif{last_number + 1}'

            # Insert Notification Record
            new_notification = Notification(
                notification_id=notification_id,
                teacher_id=teacher_id,
                student_id=selected_child.id,
                message_type=message_type,
                message_text=message_text,
                timestamp=malaysia_time
            )

            db.session.add(new_notification)
            db.session.commit()

            return redirect(url_for('parent.make_payment', payment_successful=True, payment_history_id=new_payment_id))

        return render_template('parent/make_payment.html',
                               selected_child=selected_child,
                               unpaid_fees=unpaid_fees,
                               fee_record=fee_record,
                               total_penalty=total_penalty,
                               no_payment_due=no_payment_due,
                               payment_successful=request.args.get('payment_successful'), 
                               app_name=app_name())

    except Exception as e:
        db.session.rollback()
        return render_template('error.html', error_message=str(e))
    
    
def generate_receipt_pdf(payment_history_id, selected_child, fee_record, payment_method):
    try:
        # Define the receipt folder path
        receipt_folder = os.path.abspath(os.path.join(os.getcwd(), 'app', 'archives', 'receipts'))

        # Ensure the directory exists
        if not os.path.exists(receipt_folder):
            os.makedirs(receipt_folder, exist_ok=True)
            print(f"Created folder: {receipt_folder}")
        else:
            print(f"Receipt folder exists: {receipt_folder}")

        # Define receipt file path
        receipt_filename = f"receipt_{payment_history_id}.pdf"
        receipt_path = os.path.join(receipt_folder, receipt_filename)

        print(f"Saving receipt at: {receipt_path}")

        # Fetch Payment Date from Database (Ensure it's in MYT)
        payment = db.session.query(PaymentHistory).filter_by(history_id=payment_history_id).first()
        if not payment:
            print("Error: Payment record not found!")
            return

        # Convert payment date to Malaysia Time (MYT)
        malaysia_tz = pytz.timezone('Asia/Kuala_Lumpur')
        payment_date = payment.payment_date.astimezone(malaysia_tz)
        payment_date_str = payment_date.strftime('%Y-%m-%d %H:%M:%S')

        # Fetch school details dynamically
        kindergarten_name = get_setting("school_name")
        address = get_setting("address")
        smtp_email = get_setting("contact_email")
        contact_number = get_setting("contact_number")
        logo_path = os.path.abspath(os.path.join(os.getcwd(), 'app', 'static', 'logo.png'))

        print(f"Using logo path: {logo_path}")

        # Render HTML for the receipt
        rendered_html = render_template(
            "parent/receipt_pdf.html",
            receipt_id=payment_history_id,
            payment_date=payment_date_str,
            child=selected_child,
            fee_record=fee_record,
            payment_method=payment_method,
            kindergarten_name=kindergarten_name,
            address=address,
            smtp_email=smtp_email,
            contact_number=contact_number,
            current_year=datetime.datetime.now().year,
            logo_path=logo_path
        )

        # Save PDF and check if it was created successfully
        HTML(string=rendered_html).write_pdf(receipt_path)

        # Verify if the PDF file was created
        if os.path.exists(receipt_path):
            print(f"PDF saved successfully: {receipt_path}")
        else:
            print(f"Error: PDF file not found after generation! ({receipt_path})")

    except Exception as e:
        print(f"Error generating receipt PDF: {str(e)}")

def get_setting(setting_key):
    setting = Settings.query.filter_by(setting_key=setting_key).first()
    return setting.setting_value if setting else ""