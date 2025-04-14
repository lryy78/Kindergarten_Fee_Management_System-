from flask import Blueprint

# Initialize Blueprint
teacher = Blueprint('teacher', __name__)

from .dashboard import *
from .fee_status import *
from .generate_total_fee import *
from .send_reminders import *
