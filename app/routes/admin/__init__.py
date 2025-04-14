from flask import Blueprint

# Initialize Blueprint
admin = Blueprint('admin', __name__)

from .dashboard import *
from .user_management import *
from .settings import *
from .class_assignment import *
from .fee_management import *
from .parent_student import *
