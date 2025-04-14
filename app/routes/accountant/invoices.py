from flask import render_template, request, redirect, url_for, send_file
from datetime import datetime
from flask_login import login_required
from app.routes.routes import role_required, app_name
from app.models.models import FeeRecord, Settings
from datetime import datetime
from weasyprint import HTML
from . import accountant
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INVOICE_DIR = os.path.join(BASE_DIR, '..', '..', 'archives',
                           'invoices')


@accountant.route('/invoices', methods=['GET', 'POST'])
@login_required
@role_required('4')
def generate_invoices():
    invoices = []
    today = datetime.today().date()

    # Find the earliest invoice date based on file modification times
    invoice_files = [
        os.path.join(INVOICE_DIR, f) for f in os.listdir(INVOICE_DIR)
        if f.startswith("invoice_") and f.endswith(".pdf")
    ]

    earliest_invoice_date = min(
        (datetime.fromtimestamp(os.path.getmtime(f)).date()
         for f in invoice_files),
        default=today  # If no invoices exist, default to today
    )

    # Default values
    start_date = earliest_invoice_date
    end_date = today

    if request.method == 'POST':
        try:
            start_date = datetime.strptime(
                request.form.get('start_date'), "%Y-%m-%d").date()
            end_date = datetime.strptime(
                request.form.get('end_date'), "%Y-%m-%d").date()

            if start_date > end_date:
                return redirect(url_for('accountant.generate_invoices'))

        except ValueError:
            return redirect(url_for('accountant.generate_invoices'))

    # Always fetch invoices for the selected/default date range
    # Modify the invoices list to include FeeRecord details
    invoices = []
    for filename in os.listdir(INVOICE_DIR):
        if filename.startswith("invoice_") and filename.endswith(".pdf"):
            file_path = os.path.join(INVOICE_DIR, filename)
            file_time = datetime.fromtimestamp(
                os.path.getmtime(file_path)).date()

            if start_date <= file_time <= end_date:
                # Extract FeeRecordId from filename
                fee_record_id = filename[8:-4]
                fee_record = FeeRecord.query.filter_by(
                    fee_record_id=fee_record_id).first()

                invoices.append({
                    "invoice_id": filename[:-4],  # Remove '.pdf' extension
                    "date": file_time,
                    "fee_record": fee_record  # Add FeeRecord object
                })

    return render_template(
        "accountant/invoices.html",
        invoices=invoices,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        app_name=app_name()
    )


@accountant.route('/view_invoice/<invoice_id>')
@login_required
def view_invoice(invoice_id):
    file_path = os.path.join(INVOICE_DIR, f"{invoice_id}.pdf")

    if os.path.exists(file_path):
        return send_file(file_path, mimetype="application/pdf", as_attachment=False)
    else:
        return redirect(url_for("accountant.generate_invoices"))


@accountant.route('/delete_invoice/<invoice_id>', methods=['POST'])
@login_required
@role_required('4')
def delete_invoice(invoice_id):
    file_path = os.path.join(INVOICE_DIR, f"{invoice_id}.pdf")

    if os.path.exists(file_path):
        os.remove(file_path)

    return redirect(url_for("accountant.generate_invoices"))


def get_setting(setting_key):
    setting = Settings.query.filter_by(setting_key=setting_key).first()
    return setting.setting_value if setting else ""


@accountant.route('/create_invoice', methods=['GET', 'POST'])
@login_required
@role_required('4')
def create_invoice():
    if request.method == 'POST':
        fee_record_id = request.form.get('fee_record_id')
        fee_record = FeeRecord.query.get(fee_record_id)

        if not fee_record:
            return redirect(url_for('accountant.create_invoice'))

        # Fetch required data
        student = fee_record.assignment.student
        parents = [relation.parent for relation in student.student_relations]
        invoice_date = datetime.now()
        due_date = fee_record.due_date
        fee_structure = fee_record.assignment.structure
        total_fee = fee_record.amount_due
        discounts = fee_record.discount_amount
        penalty = fee_record.late_fee_amount
        final_amount_due = fee_record.total_amount
        # Overdue months calculation
        overdue_months = max(0, (invoice_date.date() - due_date).days // 30)
        logo_path = os.path.abspath("app/static/logo.png")

        # Fetch school details dynamically
        kindergarten_name = get_setting("school_name")
        address = get_setting("address")
        smtp_email = get_setting("contact_email")
        contact_number = get_setting("contact_number")
        late_fee_amount = float(get_setting("late_fee_amount"))

        # Render HTML for the invoice
        rendered_html = render_template("accountant/invoice_pdf.html",
                                        invoice_id=fee_record_id,
                                        invoice_date=invoice_date,
                                        due_date=due_date,
                                        student=student,
                                        parents=parents,
                                        fee_structure=fee_structure,
                                        total_fee=total_fee,
                                        discounts=discounts,
                                        penalty=penalty,
                                        final_amount_due=final_amount_due,
                                        overdue_months=overdue_months,
                                        kindergarten_name=kindergarten_name,
                                        address=address,
                                        smtp_email=smtp_email,
                                        contact_number=contact_number,
                                        current_year=datetime.now().year,
                                        logo_path=logo_path,
                                        late_fee_amount=late_fee_amount,  # Pass penalty to template
                                        app_name=app_name())

        # Save PDF without opening it
        pdf_path = os.path.join(INVOICE_DIR, f"invoice_{fee_record_id}.pdf")
        HTML(string=rendered_html).write_pdf(pdf_path)

        # Redirect back to the invoice list
        return redirect(url_for('accountant.generate_invoices'))

    return render_template("accountant/create_invoice.html", fee_records=FeeRecord.query.all(), app_name=app_name())
