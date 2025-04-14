from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from config import Config
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()
DB_NAME = "db.sqlite3"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static')


    db.init_app(app)

    from .routes.routes import routes
    from .routes.auth import auth
    from .routes.accountant import accountant
    from .routes.admin import admin
    from .routes.parent import parent
    from .routes.teacher import teacher

    app.register_blueprint(routes, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(accountant, url_prefix='/accountant')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(teacher, url_prefix='/teacher')
    app.register_blueprint(parent, url_prefix='/parent')

    with app.app_context():
        db.create_all()

    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    return app

@login_manager.user_loader
def load_user(user_id):
    from .models.models import User
    return User.query.get(user_id)
