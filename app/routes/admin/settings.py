from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from app import db
from app.models.models import Settings
from . import admin
from app.routes.routes import role_required, app_name
from app.models.models import User, Role, Settings, Class, ClassAssignment, ParentStudentRelation, FeeStructure
from app.utilities.utils import allowed_file, compress_image, convert_to_favicon
import os


@admin.route('/system-settings', methods=['GET', 'POST'])
@login_required
@role_required('1')
def system_settings():
    # Retrieve all settings from the database
    settings = {
        setting.setting_key: setting.setting_value for setting in Settings.query.all()}

    # Pass settings to the template
    return render_template('admin/system_settings.html', settings=settings, app_name=app_name())

# Route to update the logo
@admin.route('/admin/update_logo', methods=['GET', 'POST'])
@login_required
@role_required('1')
def update_logo():
    print("Received request to update logo.")  # Debugging line

    if 'app_logo' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('system_settings'))

    file = request.files['app_logo']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('system_settings'))

    if file and allowed_file(file.filename):
        filename = 'logo.png'
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        try:
            print(f"Saving file to {filepath}")  # Debugging line
            file.save(filepath)

            # Compress the image after saving
            compress_image(filepath)

            # Optionally, create a favicon from the logo
            convert_to_favicon(filepath)

            flash('Logo updated successfully!', 'success')
        except Exception as e:
            print(f"Error saving file: {str(e)}")  # Debugging line
            flash(f'Error saving file: {str(e)}', 'danger')
    else:
        flash('Invalid file type or size!', 'danger')

    return redirect(url_for('admin.system_settings'))


@admin.route('/update_settings', methods=['GET', 'POST'])
@login_required
@role_required('1')
def update_settings():
    if request.method == 'POST':
        try:
            settings = Settings.query.all()
            for setting in settings:
                form_value = request.form.get(setting.setting_key)

                if form_value is not None:
                    setting.setting_value = form_value

            db.session.commit()
            return redirect(url_for('admin.dashboard'))

        except Exception as e:
            flash(f'An error occurred while updating the settings: {str(e)}', 'danger')

    return render_template('admin/system_settings.html', settings={s.setting_key: s.setting_value for s in Settings.query.all()}, app_name=app_name())
