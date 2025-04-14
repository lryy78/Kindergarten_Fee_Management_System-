from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models.models import Class, ClassAssignment, User
from . import admin
from app.routes.routes import role_required, app_name
from sqlalchemy import or_

# Route to manage classes (view page)
@admin.route('/manage_classes', methods=['GET'])
@role_required('1')
@login_required
def manage_classes():
    classes = Class.query.all()
    return render_template('admin/manage_classes.html', classes=classes, app_name=app_name())

# Route to add a new class
@admin.route('/add_class', methods=['GET', 'POST'])
@role_required('1')
@login_required
def add_class():
    if request.method == 'POST':
        class_name = request.form.get('class_name')
        teacher_id = request.form.get('teacher_id')
        student_ids = request.form.getlist('student_ids')

        if not class_name:
            flash("Class name is required!", "danger")
            return redirect(url_for('admin.manage_classes'))

        # Check if the class already exists
        existing_class = Class.query.filter_by(class_name=class_name).first()
        if existing_class:
            flash("Class already exists!", "warning")
        else:
            # Create a new class
            new_class = Class(class_name=class_name)
            db.session.add(new_class)
            db.session.commit()

            # Assign students to the class
            for student_id in student_ids:
                existing_assignment = ClassAssignment.query.filter_by(student_id=student_id).first()
                
                if existing_assignment:
                    flash(f"Student ID {student_id} is already assigned to another class!", "danger")
                else:
                    student_assignment = ClassAssignment(
                        class_id=new_class.class_id,
                        teacher_id=teacher_id,
                        student_id=student_id
                    )
                    db.session.add(student_assignment)

            db.session.commit()
            flash("Class added successfully!", "success")

        return redirect(url_for('admin.manage_classes'))


    # For GET requests, render the add_class template
    teachers = User.query.filter_by(role_id='2').all()  # Assuming 'role' is a field in the User model
    students = User.query.filter_by(role_id='5').all()  # Assuming 'role' is a field in the User model
    return render_template('admin/add_class.html', teachers=teachers, students=students, app_name=app_name())


# Route to edit a class
@admin.route('/edit_class/<string:class_id>', methods=['GET', 'POST'])
@role_required('1')
@login_required
def edit_class_page(class_id):
    # Fetch the class to edit
    class_to_edit = Class.query.get(class_id)
    if not class_to_edit:
        flash("Class not found!", "danger")
        return redirect(url_for('admin.manage_classes'))

    if request.method == 'POST':
        # Get form data
        class_name = request.form.get('class_name')
        teacher_id = request.form.get('teacher_id')
        student_ids = request.form.getlist('student_ids')

        # Validate class name
        if not class_name:
            flash("Class name is required!", "danger")
            return redirect(url_for('admin.edit_class_page', class_id=class_id))

        # Update class name
        class_to_edit.class_name = class_name

        # Update teacher assignment
        # Delete existing teacher assignment for this class
        ClassAssignment.query.filter(
            ClassAssignment.class_id == class_id,
            ClassAssignment.teacher_id.isnot(None)
        ).delete()

        # Update student assignments
        # Delete existing student assignments for this class
        ClassAssignment.query.filter_by(class_id=class_id).filter(ClassAssignment.student_id.isnot(None)).delete()

        for student_id in student_ids:
            # Check if the student is already assigned to another class
            existing_assignment = ClassAssignment.query.filter(
                ClassAssignment.student_id == student_id,
                ClassAssignment.class_id != class_id  # Ensure it's a different class
            ).first()

            if existing_assignment:
                flash(f"Student ID {student_id} is already assigned to another class!", "danger")
            else:
                # Assign the student
                student_assignment = ClassAssignment(
                    class_id=class_id,
                    teacher_id=teacher_id,
                    student_id=student_id
                )
                db.session.add(student_assignment)

        # Commit changes to the database
        db.session.commit()
        flash("Class updated successfully!", "success")
        return redirect(url_for('admin.manage_classes'))

    # Fetch teachers and students
    teachers = User.query.filter_by(role_id='2').all()  # Assuming role_id '2' is for teachers
    students = User.query.filter_by(role_id='5').all()  # Assuming role_id '5' is for students

    # Get the currently assigned teacher
    assigned_teacher = ClassAssignment.query.filter(
        ClassAssignment.class_id == class_id,
        ClassAssignment.teacher_id.isnot(None)  # Ensure it's a teacher
    ).first()

    # Get the currently assigned students
    assigned_students = ClassAssignment.query.filter(
        ClassAssignment.class_id == class_id,
        ClassAssignment.student_id.isnot(None)
    ).all()

    # Extract assigned student IDs for pre-selecting checkboxes in the template
    assigned_student_ids = [assignment.student_id for assignment in assigned_students]

    return render_template('admin/edit_class.html',
                           class_data=class_to_edit,
                           teachers=teachers,
                           students=students,
                           assigned_teacher=assigned_teacher.teacher_id if assigned_teacher else None,
                           assigned_student_ids=assigned_student_ids,
                           app_name=app_name())


# Route to delete a class
@admin.route('/delete_class/<string:class_id>', methods=['GET', 'POST'])
@role_required('1')
@login_required
def delete_class(class_id):
    class_to_delete = Class.query.get(class_id)
    if not class_to_delete:
        flash("Class not found!", "danger")
    else:
        # Delete all assignments related to the class
        ClassAssignment.query.filter_by(class_id=class_id).delete()
        db.session.delete(class_to_delete)
        db.session.commit()
        flash("Class deleted successfully!", "success")

    return redirect(url_for('admin.manage_classes'))