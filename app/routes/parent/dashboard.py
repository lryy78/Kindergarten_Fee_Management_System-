# app/routes/parent/dashboard.py
import random
from flask import render_template, request, redirect, url_for, session
from flask_login import login_required, current_user
from app.routes.routes import role_required, app_name
from app.models.models import User, ParentStudentRelation
from app import db
from . import parent

@parent.route('/')
@login_required
@role_required('3')  # Ensure the user has the parent role
def dashboard():
    try:
        # Fetch children related to the current parent
        children = (
            db.session.query(User)
            .join(ParentStudentRelation, ParentStudentRelation.student_id == User.id)
            .filter(ParentStudentRelation.parent_id == current_user.id)
            .all()
        )

        # If no children are associated, display an error message
        if not children:
            return render_template(
                'parent/parent.html',
                error_message="No children are associated with this parent account."
            )

        # Retrieve selected child ID from the session
        user_specific_key = f'selected_child_id_{current_user.id}'
        selected_child_id = session.get(user_specific_key)

        if not selected_child_id:
            # Randomly select a child if no child is selected
            random_child = random.choice(children)
            session[user_specific_key] = random_child.id
            selected_child = random_child
        else:
            # Fetch the selected child's details
            selected_child = db.session.query(User).filter_by(id=selected_child_id).first()

        return render_template('parent/parent.html', children=children, selected_child=selected_child, app_name=app_name())
    except Exception as e:
        return render_template('error.html', error_message=str(e))


@parent.route('/select_child', methods=['POST'])
@login_required
@role_required('3')
def select_child():
    try:
        # Retrieve child ID from form submission
        child_id = request.form.get('child_id')

        # Validate if the child belongs to the parent
        is_child_valid = (
            db.session.query(ParentStudentRelation)
            .filter_by(parent_id=current_user.id, student_id=child_id)
            .first()
        )

        if is_child_valid:
            # Store selected child ID in session
            user_specific_key = f'selected_child_id_{current_user.id}'
            session[user_specific_key] = child_id  # Store in session with a user-specific key
        else:
            # Clear session if validation fails
            user_specific_key = f'selected_child_id_{current_user.id}'
            session.pop(user_specific_key, None)

        return redirect(url_for('parent.dashboard'))
    except Exception as e:
        return render_template('error.html', error_message=str(e))