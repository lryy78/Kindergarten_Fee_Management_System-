from flask import render_template
from flask_login import login_required
from app import db
from . import admin
from app.models.models import User
from app.routes.routes import role_required, app_name

@admin.route('/')
@login_required
@role_required('1')
def dashboard():
    return render_template('admin/admin.html', app_name=app_name())
