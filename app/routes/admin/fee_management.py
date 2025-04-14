from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models.models import FeeStructure, Settings
from . import admin
from app.routes.routes import role_required, app_name

# Route to view fee management (empty for now)
@admin.route('/fee_management')
@login_required
@role_required('1')
def fee_management():
    # Fetch all fee structures from the database
    fee_structures = FeeStructure.query.all()

    # Fetch specific settings related to fees
    fee_settings = {
        'late_fee_amount': Settings.query.filter_by(setting_key='late_fee_amount').first(),
        'due_date_reminder': Settings.query.filter_by(setting_key='due_date_reminder').first(),
        'discount_amount': Settings.query.filter_by(setting_key='discount_amount').first()
    }

    # Convert settings to a dictionary for easier access in the template
    settings = {
        key: setting.setting_value if setting else None
        for key, setting in fee_settings.items()
    }

    return render_template(
        'admin/fee_management.html',
        fee_structures=fee_structures,
        settings=settings,
        app_name=app_name()
    )

@admin.route('/add_fee_structure', methods=['GET', 'POST'])
@login_required
@role_required('1')
def add_fee_structure():
    if request.method == 'POST':
        # Handle form submission (creating a new fee structure)
        description = request.form['description']
        total_fee = request.form['total_fee']
        new_fee_structure = FeeStructure(description=description, total_fee=total_fee)
        db.session.add(new_fee_structure)
        db.session.commit()
        flash('Fee Structure Added Successfully!', 'success')
        return redirect(url_for('admin.fee_management'))
    return render_template('admin/add_fee_structure.html', app_name=app_name())

@admin.route('/edit_fee_structure/<id>', methods=['GET', 'POST'])
@login_required
@role_required('1')
def edit_fee_structure(id):
    fee_structure = FeeStructure.query.get(id)
    
    if not fee_structure:
        flash('Fee Structure not found!', 'danger')
        return redirect(url_for('admin.fee_management'))
    
    # Handle the form submission
    if request.method == 'POST':
        fee_structure.description = request.form['description']
        fee_structure.total_fee = request.form['total_fee']

        db.session.commit()
        flash('Fee Structure updated successfully!', 'success')
        return redirect(url_for('admin.fee_management'))

    return render_template('admin/edit_fee_structure.html', fee_structure=fee_structure, app_name=app_name())

@admin.route('/update_fee_structure/<id>', methods=['POST'])
@login_required
@role_required('1')
def update_fee_structure(id):
    # Retrieve the FeeStructure object from the database
    fee_structure = FeeStructure.query.get(id)

    if fee_structure:
        # Update the fields with the new values from the form
        fee_structure.description = request.form['description']
        fee_structure.total_fee = request.form['total_fee']

        # Commit the changes to the database
        db.session.commit()

        # Flash a success message
        flash('Fee Structure Updated Successfully!', 'success')
    else:
        flash('Fee Structure not found.', 'danger')

    # Redirect to the fee management page after updating
    return redirect(url_for('admin.fee_management'))

# Fee Structure: Delete
@admin.route('/delete_fee_structure/<id>')
@login_required
@role_required('1')
def delete_fee_structure(id):
    fee_structure = FeeStructure.query.get(id)
    db.session.delete(fee_structure)
    db.session.commit()
    flash('Fee Structure Deleted Successfully!', 'success')
    return redirect(url_for('admin.fee_management'))

@admin.route('/update_fee_settings', methods=['GET', 'POST'])
@login_required
@role_required('1')
def update_fee_settings():
    if request.method == 'POST':
        try:
            # Retrieve specific fee settings keys
            late_fee_amount = request.form.get('late_fee_amount')
            due_date_reminder = request.form.get('due_date_reminder')
            discount_amount = request.form.get('discount_amount')

            # Validate and update each setting individually
            if late_fee_amount is not None:
                # Convert to float, round to 2 decimal places, and update in the database
                late_fee_setting = Settings.query.filter_by(setting_key='late_fee_amount').first()
                late_fee_setting.setting_value = str(round(float(late_fee_amount), 2))

            if due_date_reminder is not None:
                # Ensure the value is an integer
                due_date_setting = Settings.query.filter_by(setting_key='due_date_reminder').first()
                due_date_setting.setting_value = str(int(due_date_reminder))

            if discount_amount is not None:
                # Convert to float, round to 2 decimal places, and update in the database
                discount_setting = Settings.query.filter_by(setting_key='discount_amount').first()
                discount_setting.setting_value = str(round(float(discount_amount), 2))

            # Commit the changes to the database
            db.session.commit()

            # Flash success message and redirect
            flash('Fee settings updated successfully.', 'success')
            return redirect(url_for('admin.fee_management'))

        except Exception as e:
            # Flash error message in case of an exception
            flash(f'An error occurred while updating the fee settings: {str(e)}', 'danger')

    # For GET requests or error scenarios, render the settings page
    fee_settings = {
    'late_fee_amount': Settings.query.filter_by(setting_key='late_fee_amount').first(),
    'due_date_reminder': Settings.query.filter_by(setting_key='due_date_reminder').first(),
    'discount_amount': Settings.query.filter_by(setting_key='discount_amount').first()
}
    return render_template('admin/fee_management.html', settings=fee_settings, app_name=app_name())


