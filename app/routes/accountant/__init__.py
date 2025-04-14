from flask import Blueprint

# Create the blueprint
accountant = Blueprint('accountant', __name__)

from . import overdue_records
from . import invoices
from . import financial_reports
from . import fee_records
from . import dashboard