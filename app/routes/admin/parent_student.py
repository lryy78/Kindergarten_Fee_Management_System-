from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models.models import ParentStudentRelation, User
from . import admin
from app.routes.routes import role_required, app_name

# Route to view parent student (empty for now)
@admin.route('/parent_student', methods=['GET', 'POST'])
@login_required
@role_required('1')  # Only accessible by Admin
def parent_student():
    # Fetch all students and parents
    parents = User.query.filter_by(role_id=3).all()  # Parents have role_id = 3
    students = User.query.filter_by(role_id=5).all()  # Students have role_id = 5

    # Create a dictionary of student_id to parent_id from ParentStudentRelation
    parent_student_map = {
        relation.student_id: relation.parent_id
        for relation in ParentStudentRelation.query.all()
    }

    if request.method == 'POST':
        # Loop through students and assign the selected parent
        for student in students:
            parent_id = request.form.get(f'parent_id_{student.id}')
            if parent_id:
                # Check if the student already has a parent
                existing_relation = ParentStudentRelation.query.filter_by(student_id=student.id).first()
                if existing_relation:
                    # Update the existing relation
                    existing_relation.parent_id = parent_id
                else:
                    # Create a new relationship
                    new_relation = ParentStudentRelation(parent_id=parent_id, student_id=student.id)
                    db.session.add(new_relation)
                db.session.commit()

        flash("Parent-Student relationships updated successfully!", "success")
        return redirect(url_for('admin.parent_student'))

    # Pass the parent-student mapping to the template
    return render_template(
        'admin/parent_student.html',
        students=students,
        parents=parents,
        parent_student_map=parent_student_map,  # Provide the map for pre-selection
        app_name=app_name()
    )
