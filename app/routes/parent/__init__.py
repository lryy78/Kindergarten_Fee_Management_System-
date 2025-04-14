# app/routes/parent/__init__.py
from flask import Blueprint

parent = Blueprint('parent', __name__)

from .dashboard import *
from .fee_summary import *
from .fee_record import *
from .make_payment import *
from .notification_dashboard import *
from .payment_history import *
from .notification import *