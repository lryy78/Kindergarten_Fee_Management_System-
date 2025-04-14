from datetime import datetime
from app import db
from flask import redirect, render_template, request, url_for
from flask_login import login_required
from app.models.models import FeeRecord
from app.routes.routes import app_name, role_required
from . import accountant


@accountant.route('/overdue_records', methods=['GET', 'POST'])
@login_required
@role_required('4')
def overdue_records():
    today = datetime.today().date()

    # Fetch overdue fee records (where due date has passed and not paid)
    overdue_fees = FeeRecord.query.filter(
        FeeRecord.due_date < today,  # Due date has passed
        FeeRecord.status_id == "status003"  # Not marked as "Paid"
    ).all()

    if request.method == 'POST':
        fee_record_id = request.form.get('fee_record_id')
        fee_record = FeeRecord.query.get(fee_record_id)

        if fee_record:
            fee_record.flagged_for_followup = 1  # Mark as flagged
            db.session.commit()

        return redirect(url_for('accountant.overdue_records'))

    return render_template("accountant/overdue_records.html", overdue_fees=overdue_fees, app_name=app_name())
