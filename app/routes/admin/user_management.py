from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models.models import User, Role, Settings, ParentStudentRelation
from . import admin
from app.routes.routes import role_required, app_name
import uuid
import re
from datetime import datetime

# Route to manage users
@admin.route('/manage_users')
@login_required
@role_required('1')
def manage_users():
    # Query the database to get all users
    users = User.query.all()  # Retrieve all users from the User table
    return render_template('admin/manage_users.html', users=users, app_name=app_name())

# Route to add a new user
@admin.route('/add_user', methods=['GET', 'POST'])
@login_required
@role_required('1')
def add_user():
    roles = Role.query.all()
    password_policy_setting = Settings.query.filter_by(setting_key='password_policy').first()
    password_policy = password_policy_setting.setting_value if password_policy_setting else 'simple'  # Default to 'simple' if not set

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form.get('email')
        password = request.form.get('password')  # Password is optional for students
        role_id = request.form.get('role')
        date_of_birth_str = request.form.get('date_of_birth')  # Fetch date of birth as string

        # Check if the user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('User with this email already exists!', 'danger')
            return redirect(url_for('admin.add_user'))

        # Convert date_of_birth from string to date
        date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date() if date_of_birth_str else None

        # Skip password validation if the role is 5 (student)
        if role_id != '5':
            # Password validation (backend)
            if password_policy == 'strong':
                strong_password_regex = r'^(?=.*[0-9])(?=.*[\W_]).{8,}$'
                if not re.match(strong_password_regex, password):
                    flash('Password must be at least 8 characters long and contain at least one number and one special character.', 'danger')
                    return redirect(url_for('admin.add_user'))
            else:
                if len(password) < 6:
                    flash('Password must be at least 6 characters long.', 'danger')
                    return redirect(url_for('admin.add_user'))
        else:
            # For students, set password to None
            password = None

        # Generate user ID and create a new user
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,  # Password is None for students
            role_id=role_id,
            date_of_birth=date_of_birth  # Pass the date object to the database
        )

        # Add and commit the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('User added successfully!', 'success')
        return redirect(url_for('admin.manage_users'))

    return render_template('admin/add_user.html', roles=roles, password_policy=password_policy, app_name=app_name())


@admin.route('/edit_user/<string:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('1')
def edit_user(user_id):
    user = User.query.filter_by(id=user_id).first_or_404()
    roles = Role.query.all()
    password_policy_setting = Settings.query.filter_by(setting_key='password_policy').first()
    password_policy = password_policy_setting.setting_value if password_policy_setting else 'simple'  # Default to 'simple' if not set

    if request.method == 'POST':
        old_role_id = user.role_id

        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        user.email = request.form['email']
        user.role_id = request.form['role_id']

        # Convert date_of_birth from string to date
        date_of_birth_str = request.form['date_of_birth']
        user.date_of_birth = datetime.strptime(
            date_of_birth_str, '%Y-%m-%d').date()

        new_password = request.form['password']

        if new_password:
            if password_policy == 'strong':
                strong_password_regex = r'^(?=.*[0-9])(?=.*[\W_]).{8,}$'
                if not re.match(strong_password_regex, new_password):
                    flash('Password must be at least 8 characters long, contain at least one number and one special character.', 'danger')
                    return redirect(url_for('admin.edit_user', user_id=user.id))
            else:  # Simple policy
                if len(new_password) < 6:
                    flash('Password must be at least 6 characters long.', 'danger')
                    return redirect(url_for('admin.edit_user', user_id=user.id))

            user.password = new_password  # Update the password if valid

        if user.role_id == '5':
            user.password = None

        existing_user = User.query.filter_by(email=user.email).first()
        if existing_user and existing_user.id != user.id:
            flash('User with this email already exists!', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user.id))

        # If user was a student and is now NOT a student, remove their parent-student relation
        if old_role_id == '5' and user.role_id != '5':
            ParentStudentRelation.query.filter_by(student_id=user.id).delete()
        
        # If user was assigned as a student to another parent but is now a parent, remove their parent assignment
        if old_role_id == '5' and user.role_id == '3':
            ParentStudentRelation.query.filter_by(student_id=user.id).delete()

        if old_role_id == '3' and user.role_id != '3':
            ParentStudentRelation.query.filter_by(parent_id=user.id).delete()

        db.session.commit()
        return redirect(url_for('admin.manage_users'))

    return render_template('admin/edit_user.html', user=user, roles=roles, password_policy=password_policy, app_name=app_name())


@admin.route('/delete_user/<string:user_id>', methods=['POST'])
@login_required
@role_required('1')
def delete_user(user_id):
    # Fetch the user by id
    user = User.query.filter_by(id=user_id).first_or_404()

    # Delete the user
    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('admin.manage_users'))
