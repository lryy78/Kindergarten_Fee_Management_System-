from flask import Blueprint, render_template
from flask_login import login_required
from app.routes.routes import role_required, app_name
from . import teacher

# Teacher Dashboard
@teacher.route('/')
@login_required
@role_required('2')
def dashboard():
    return render_template('teacher/dashboard.html', app_name=app_name())
