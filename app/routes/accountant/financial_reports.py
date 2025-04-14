from flask import render_template, request, redirect, url_for, send_file
from datetime import datetime
import statistics
from flask_login import login_required
from app.routes.routes import role_required, app_name
from app.models.models import FeeRecord, PaymentHistory, Settings
from weasyprint import HTML
from datetime import datetime, timedelta
from . import accountant
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, '..', '..', 'archives',
                           'reports')


@accountant.route('/financial_reports')
@login_required
@role_required('4')
def financial_reports():
    reports = []

    # Fetch all report files from the archive
    for report_type in ["fee_collection", "financial_health", "overdue_payment"]:
        folder_path = os.path.join(REPORTS_DIR, report_type)

        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                if filename.endswith(".pdf"):
                    report_id = filename.split(".")[0]  # Remove file extension

                    # Extract the full date-time part, including both date and time
                    date_time_part = filename.split(
                        "_")[-2] + "_" + filename.split("_")[-1].replace(".pdf", "")

                    # Convert the date-time part to a datetime object
                    try:
                        # Format: 'YYYY-MM-DD_HH-MM-SS' (e.g., '2025-02-05_21-29-22')
                        report_date = datetime.strptime(
                            date_time_part, '%Y-%m-%d_%H-%M-%S')
                    except ValueError:
                        print(f"Error parsing: {date_time_part}")

                    reports.append({
                        "report_id": report_id,
                        "report_type": report_type,
                        "date": report_date  # Now it's a datetime object with both date and time
                    })

    return render_template("accountant/financial_reports.html", reports=reports, app_name=app_name())


@accountant.route('/view_report/<report_id>')
@login_required
def view_report(report_id):
    # Determine the subdirectory based on report_id prefix
    if report_id.startswith("fc_"):
        report_dir = "fee_collection"
    elif report_id.startswith("fh_"):
        report_dir = "financial_health"
    elif report_id.startswith("op_"):
        report_dir = "overdue_payment"
    else:
        return redirect(url_for("accountant.financial_reports"))

    # Construct file path
    file_path = os.path.join(REPORTS_DIR, report_dir, f"{report_id}.pdf")

    # Check if file exists, then serve it inline (view in browser)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype="application/pdf", as_attachment=False)
    else:
        return redirect(url_for("accountant.financial_reports"))


@accountant.route('/delete_report/<report_id>', methods=["POST"])
@login_required
def delete_report(report_id):
    # Determine the subdirectory based on report_id prefix
    if report_id.startswith("fc_"):
        report_dir = "fee_collection"
    elif report_id.startswith("fh_"):
        report_dir = "financial_health"
    elif report_id.startswith("op_"):
        report_dir = "overdue_payment"
    else:
        return redirect(url_for("accountant.financial_reports"))

    # Construct file path
    file_path = os.path.join(REPORTS_DIR, report_dir, f"{report_id}.pdf")

    # Delete the file if it exists
    if os.path.exists(file_path):
        os.remove(file_path)

    return redirect(url_for("accountant.financial_reports"))


@accountant.route('/financial_reports/generate', methods=['GET', 'POST'])
@login_required
@role_required('4')
def generate_report():
    if request.method == 'POST':
        report_type = request.form.get('reportType')

        if not report_type:
            return redirect(url_for("accountant.financial_reports"))

        if report_type == "fees":
            # Redirect to date selection form
            return generate_fees_report()
        elif report_type == "overdue":
            return generate_overdue_report()
        elif report_type == "financialHealth":
            return generate_financial_health_report()

        return redirect(url_for("accountant.financial_reports"))

    return render_template("accountant/generate_report.html", app_name=app_name())

def get_setting(setting_key):
    setting = Settings.query.filter_by(setting_key=setting_key).first()
    return setting.setting_value if setting else ""

@accountant.route('/financial_reports/generate/fee_collection_report', methods=['GET', 'POST'])
@login_required
@role_required('4')
def generate_fees_report():
    if request.method == 'GET':
        # Default date range: earliest date in FeeRecord and today's date
        earliest_record = FeeRecord.query.order_by(
            FeeRecord.date_assigned.asc()).first()
        today = datetime.today().date()

        # Set default date range values
        start_date = earliest_record.date_assigned if earliest_record else today
        end_date = today

        # Query for fee records based on default date range
        fee_records = FeeRecord.query.filter(
            FeeRecord.status_id == "status002",  # Only include paid fees
            FeeRecord.payment_histories.any(),  # Ensure there is at least one payment
            FeeRecord.date_assigned >= start_date,
            FeeRecord.date_assigned <= end_date
        ).all()

        return render_template("accountant/fee_collection_report.html",
                               start_date=start_date,
                               end_date=end_date,
                               fee_records=fee_records,
                               app_name=app_name(),
                               payment_dates=[payment.payment_date.strftime(
                                   '%Y-%m-%d') for payment in PaymentHistory.query.all()],
                               report_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    elif request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if not start_date or not end_date:
            return redirect(url_for("accountant.generate_fees_report"))

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return redirect(url_for("accountant.generate_fees_report"))

        if start_date > end_date:
            return redirect(url_for("accountant.generate_fees_report"))

        # Query for fee records in the selected date range
        fee_records = FeeRecord.query.filter(
            FeeRecord.status_id == "status002",  # Only include paid fees
            FeeRecord.payment_histories.any(),  # Ensure there is at least one payment
            FeeRecord.date_assigned >= start_date,
            FeeRecord.date_assigned <= end_date
        ).all()

        # If the action is "generate", generate the PDF report
        if request.form.get('action') == 'generate':
            report_html = render_template(
                "accountant/fee_collection_report_pdf.html",
                fee_records=fee_records,
                total_collected=sum(
                    [record.total_amount for record in fee_records]),
                total_penalty=sum(
                    [record.late_fee_amount for record in fee_records]),
                total_discount=sum(
                    [record.discount_amount for record in fee_records]),
                final_total_collected=sum([record.total_amount for record in fee_records]) + sum(
                    [record.late_fee_amount for record in fee_records]) - sum([record.discount_amount for record in fee_records]),
                report_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                app_name=app_name(),
                kindergarten_name=get_setting("school_name"),
                address=get_setting("address"),
                smtp_email=get_setting("contact_email"),
                contact_number=get_setting("contact_number"),
                logo_path=os.path.abspath("app/static/logo.png"),
                start_date=start_date,
                end_date=end_date,
                current_year=datetime.now().year,
                payment_dates=[payment.payment_date.strftime(
                    '%Y-%m-%d') for payment in PaymentHistory.query.all()]
            )
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            report_filename = f"fc_{timestamp}.pdf"
            report_path = os.path.join(
                REPORTS_DIR, "fee_collection", report_filename)
            HTML(string=report_html).write_pdf(report_path)

            # Redirect to the financial reports page after report is generated
            return redirect(url_for('accountant.financial_reports'))

        # Show the date selection page with fee records for the selected range
        return render_template(
            "accountant/fee_collection_report.html",
            start_date=start_date,
            end_date=end_date,
            fee_records=fee_records,
            payment_dates=[payment.payment_date.strftime(
                '%Y-%m-%d') for payment in PaymentHistory.query.all()],
            app_name=app_name()
        )


@accountant.route('/financial_reports/generate/overdue_report', methods=['GET', 'POST'])
@login_required
@role_required('4')  # Assuming only accountants can generate reports
def generate_overdue_report():
    if request.method == 'GET':
        # Default date range: earliest overdue record and today's date
        earliest_overdue = FeeRecord.query.filter(
            FeeRecord.due_date < datetime.today().date(),
            FeeRecord.status_id != "status002"  # Exclude fully paid fees
        ).order_by(FeeRecord.due_date.asc()).first()

        today = datetime.today().date()
        start_date = earliest_overdue.due_date if earliest_overdue else today
        end_date = today

        # Query overdue fee records
        overdue_records = FeeRecord.query.filter(
            FeeRecord.due_date < end_date,
            FeeRecord.status_id == "status003"  # Ensure only overdue records are included
        ).distinct().all()  # Use distinct to avoid duplicates

        return render_template(
            "accountant/overdue_fee_report.html",
            start_date=start_date,
            end_date=end_date,
            overdue_records=overdue_records,
            app_name=app_name()
        )

    elif request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        # Ensure that both dates are provided
        if not start_date or not end_date:
            return redirect(url_for("accountant.generate_overdue_report"))

        try:
            # Convert string to datetime object
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return redirect(url_for("accountant.generate_overdue_report"))

        # Ensure start date is not later than end date
        if start_date > end_date:
            return redirect(url_for("accountant.generate_overdue_report"))

        # Query for overdue fee records in the selected date range
        overdue_records = FeeRecord.query.filter(
            FeeRecord.due_date >= start_date,
            FeeRecord.due_date <= end_date,
            FeeRecord.status_id == "status003"  # Ensure only overdue records are included
        ).distinct().all()  # Use distinct to avoid duplicates

        # If the action is "generate", generate the PDF report
        if request.form.get('action') == 'generate':
            if not overdue_records:
                return redirect(url_for("accountant.generate_overdue_report"))

            report_html = render_template(
                "accountant/overdue_fee_report_pdf.html",
                overdue_records=overdue_records,
                report_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                kindergarten_name=get_setting("school_name"),
                address=get_setting("address"),
                smtp_email=get_setting("contact_email"),
                contact_number=get_setting("contact_number"),
                current_year=datetime.now().year,
                logo_path=os.path.abspath("app/static/logo.png"),
                start_date=start_date,  # Add this line
                end_date=end_date,      # Add this line
                app_name=app_name()
            )

            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            report_filename = f"op_{timestamp}.pdf"
            report_path = os.path.join(
                REPORTS_DIR, "overdue_payment", report_filename)
            HTML(string=report_html).write_pdf(report_path)

            # Redirect to financial reports page after report generation
            return redirect(url_for('accountant.financial_reports'))

        return render_template(
            "accountant/overdue_fee_report.html",
            start_date=start_date,
            end_date=end_date,
            overdue_records=overdue_records,
            app_name=app_name()
        )


@accountant.route('/financial_reports/generate/financial_health_report', methods=['GET', 'POST'])
@login_required
@role_required('4')  # Only accountants can generate reports
def generate_financial_health_report():
    if request.method == 'GET':
        # Default date range: earliest record and today's date
        earliest_record = FeeRecord.query.order_by(
            FeeRecord.date_assigned.asc()).first()
        today = datetime.today().date()
        start_date = earliest_record.date_assigned if earliest_record else today
        end_date = today

        statistics = calculate_financial_statistics(start_date, end_date)

        return render_template("accountant/financial_health_report.html",
                               start_date=start_date, end_date=end_date, statistics=statistics, app_name=app_name())

    elif request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        # Ensure both dates are provided
        if not start_date or not end_date:
            return redirect(url_for("accountant.generate_financial_health_report"))

        try:
            # Convert string to datetime object
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return redirect(url_for("accountant.generate_financial_health_report"))

        # Ensure start date is not later than end date
        if start_date > end_date:
            return redirect(url_for("accountant.generate_financial_health_report"))

        # Calculate financial statistics for the selected date range
        statistics = calculate_financial_statistics(start_date, end_date)

        # If the action is "generate", generate the PDF report
        if request.form.get('action') == 'generate':
            report_html = render_template("accountant/financial_health_report_pdf.html",
                                          statistics=statistics,
                                          report_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                          kindergarten_name=get_setting(
                                              "school_name"),
                                          address=get_setting("address"),
                                          smtp_email=get_setting(
                                              "contact_email"),
                                          contact_number=get_setting(
                                              "contact_number"),
                                          current_year=datetime.now().year,
                                          logo_path=os.path.abspath(
                                              "app/static/logo.png"),
                                          start_date=start_date,  # Add this line
                                          end_date=end_date,      # Add this line
                                          app_name=app_name())

            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            report_filename = f"fh_{timestamp}.pdf"
            report_path = os.path.join(
                REPORTS_DIR, "financial_health", report_filename)
            HTML(string=report_html).write_pdf(report_path)

            # Redirect to financial reports page after report generation
            return redirect(url_for('accountant.financial_reports'))

        return render_template("accountant/financial_health_report.html",
                               start_date=start_date, end_date=end_date, statistics=statistics, app_name=app_name())


def get_past_total_collected(start_date, end_date):
    """
    Retrieves total collected revenue from the previous period (e.g., last year).
    Adjusts the past date range based on the current date selection.
    """
    past_start_date = start_date - timedelta(days=(end_date - start_date).days)
    past_end_date = start_date

    past_fee_records = FeeRecord.query.filter(
        FeeRecord.date_assigned >= past_start_date,
        FeeRecord.date_assigned <= past_end_date
    ).all()

    return float(sum(record.total_amount for record in past_fee_records))


def calculate_financial_statistics(start_date, end_date):
    fee_records = FeeRecord.query.filter(
        FeeRecord.date_assigned >= start_date,
        FeeRecord.date_assigned <= end_date
    ).all()

    # Convert Decimal to float to prevent TypeError
    total_collected = float(sum(record.total_amount for record in fee_records))
    total_outstanding = float(sum(record.amount_due for record in fee_records))
    total_discounts = float(
        sum(record.discount_amount for record in fee_records))
    late_fees_collected = float(
        sum(record.late_fee_amount for record in fee_records))
    net_revenue = total_collected - total_discounts

    # Overdue Analysis
    today = datetime.today().date()
    overdue_30 = float(sum(record.amount_due for record in fee_records if 0 <= (
        today - record.due_date).days <= 30))
    overdue_60 = float(sum(record.amount_due for record in fee_records if 31 <= (
        today - record.due_date).days <= 60))
    overdue_90 = float(sum(record.amount_due for record in fee_records if 61 <= (
        today - record.due_date).days <= 90))
    overdue_90_plus = float(sum(record.amount_due for record in fee_records if (
        today - record.due_date).days > 90))

    # Statistical Analysis
    all_payments = [float(record.total_amount) for record in fee_records]

    if all_payments:
        average_collected = sum(all_payments) / len(all_payments)
        median_collected = statistics.median(all_payments)
        highest_payment = max(all_payments)
        lowest_payment = min(all_payments)
        std_dev = round(statistics.stdev(all_payments),
                        2) if len(all_payments) > 1 else 0
    else:
        average_collected = median_collected = highest_payment = lowest_payment = std_dev = 0

    # Performance Metrics
    collection_efficiency = round((total_collected / (total_collected + total_outstanding)) * 100, 2) \
        if (total_collected + total_outstanding) > 0 else 0

    compliance_rate = round(
        (len([r for r in fee_records if r.status.status_name == "Paid"]
             ) / len(fee_records)) * 100, 2
    ) if fee_records else 0

    previous_period_collected = get_past_total_collected(start_date, end_date)
    if previous_period_collected > 0:
        revenue_growth = round(
            ((total_collected - previous_period_collected) / previous_period_collected) * 100, 2)
    else:
        revenue_growth = 0  # No past data to compare

    # Recommendations
    recommendations = []
    if collection_efficiency < 80:
        recommendations.append(
            "Collection efficiency is below target. Implement stricter follow-ups on overdue payments.")
    if total_outstanding > total_collected * 0.5:
        recommendations.append(
            "Outstanding fees are high. Consider offering installment plans or discounts for early payments.")
    if compliance_rate < 75:
        recommendations.append(
            "Low compliance rate detected. Send payment reminders to increase timely payments.")
    if revenue_growth < 0:
        recommendations.append(
            "Revenue is declining. Evaluate tuition pricing and explore new income sources.")

    recommendations_text = " ".join(
        recommendations) if recommendations else "Financial performance is stable."

    return {
        "total_collected": total_collected,
        "total_outstanding": total_outstanding,
        "total_discounts": total_discounts,
        "late_fees_collected": late_fees_collected,
        "net_revenue": net_revenue,

        # Overdue breakdown
        "overdue_30": overdue_30,
        "overdue_60": overdue_60,
        "overdue_90": overdue_90,
        "overdue_90_plus": overdue_90_plus,

        # Statistical analysis
        "average_collected": round(average_collected, 2),
        "median_collected": round(median_collected, 2),
        "highest_payment": highest_payment,
        "lowest_payment": lowest_payment,
        "std_dev": std_dev,

        # Performance metrics
        "collection_efficiency": collection_efficiency,
        "compliance_rate": compliance_rate,
        "revenue_growth": revenue_growth,

        # Recommendations
        "recommendations": recommendations_text
    }
