from app import db
from flask_login import UserMixin
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import uuid

# Role model
class Role(db.Model):
    __tablename__ = 'Role'
    id = db.Column('RoleId', db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    role_name = db.Column('RoleName', db.String, nullable=False)

    # Relationships
    users = relationship('User', back_populates='role')

# User model
from sqlalchemy.sql import func

class User(UserMixin, db.Model):
    __tablename__ = 'User'
    
    id = db.Column('Id', db.String, primary_key=True)
    password = db.Column('Password', db.String, nullable=True)
    role_id = db.Column('RoleId', db.String, ForeignKey('Role.RoleId', ondelete='SET NULL'))
    email = db.Column('Email', db.String, nullable=False)
    first_name = db.Column('FirstName', db.String, nullable=False)
    last_name = db.Column('LastName', db.String, nullable=False)
    date_of_birth = db.Column('DateOfBirth', db.Date, nullable=False)

    # Relationships
    role = relationship('Role', back_populates='users')
    parent_relations = relationship('ParentStudentRelation', back_populates='parent', foreign_keys='ParentStudentRelation.parent_id')
    student_relations = relationship('ParentStudentRelation', back_populates='student', foreign_keys='ParentStudentRelation.student_id')
    student_fees = relationship('StudentFeeAssignment', back_populates='student')
    class_assignments_teacher = relationship('ClassAssignment', back_populates='teacher', foreign_keys='ClassAssignment.teacher_id')
    class_assignments_student = relationship('ClassAssignment', back_populates='student', foreign_keys='ClassAssignment.student_id')
    messages_sent = relationship('Notification', back_populates='teacher', foreign_keys='Notification.teacher_id')
    messages_received = relationship('Notification', back_populates='student', foreign_keys='Notification.student_id')

    @staticmethod
    def generate_user_id():
        """Generate the next user_id as 'user1', 'user2', etc."""
        latest_user = db.session.query(User).filter(
            User.id.like('user%')
        ).order_by(
            db.cast(func.substring(User.id, 5), db.Integer).desc()
        ).first()
        
        if latest_user:
            next_number = int(latest_user.id[4:]) + 1  # Extract number and increment
        else:
            next_number = 1  # Start from user1 if no existing records

        return f"user{next_number}"

    def __init__(self, first_name, last_name, email, password=None, role_id=None, date_of_birth=None):
        self.id = self.generate_user_id()
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password
        self.role_id = role_id
        self.date_of_birth = date_of_birth


# Class model
class Class(db.Model):
    __tablename__ = 'Class'
    class_id = db.Column('ClassId', db.String, primary_key=True)
    class_name = db.Column('ClassName', db.String, nullable=False)
    description = db.Column('Description', db.String, nullable=True)

    # Relationships
    assignments = relationship('ClassAssignment', back_populates='class_')

    # Auto-generate class_id as "class1", "class2", "class3", etc.
    @staticmethod
    def generate_class_id():
        last_class = db.session.query(Class).order_by(db.desc(Class.class_id)).first()
        if last_class and last_class.class_id.startswith("class"):
            last_number = int(last_class.class_id.replace("class", ""))
            return f"class{last_number + 1}"
        return "class1"

    def __init__(self, class_name, description=None):
        self.class_id = self.generate_class_id()
        self.class_name = class_name
        self.description = description

# ClassAssignment model
class ClassAssignment(db.Model):
    __tablename__ = 'ClassAssignment'
    assignment_id = db.Column('AssignmentId', db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    class_id = db.Column('ClassId', db.String, ForeignKey('Class.ClassId', ondelete='CASCADE'))
    teacher_id = db.Column('TeacherId', db.String, ForeignKey('User.Id', ondelete='SET NULL'))
    student_id = db.Column('StudentId', db.String, ForeignKey('User.Id', ondelete='SET NULL'))

    # Relationships
    class_ = relationship('Class', back_populates='assignments')
    teacher = relationship('User', back_populates='class_assignments_teacher', foreign_keys=[teacher_id])
    student = relationship('User', back_populates='class_assignments_student', foreign_keys=[student_id])

class FeeStructure(db.Model):
    __tablename__ = 'FeeStructure'

    structure_id = db.Column('StructureId', db.String, primary_key=True)
    description = db.Column('Description', db.String, nullable=False)
    total_fee = db.Column('TotalFee', db.Numeric(10, 2), nullable=False)

    # Relationships
    student_assignments = relationship('StudentFeeAssignment', back_populates='structure')

    @staticmethod
    def generate_structure_id():
        latest_structure = db.session.query(FeeStructure).filter(
            FeeStructure.structure_id.like('structure%')
        ).order_by(
            db.cast(func.substring(FeeStructure.structure_id, 10), db.Integer).desc()
        ).first()
        
        if latest_structure:
            next_number = int(latest_structure.structure_id[9:]) + 1
        else:
            next_number = 1  # Start from structure1 if no existing records

        return f"structure{next_number}"

    def __init__(self, description, total_fee):
        self.structure_id = self.generate_structure_id()
        self.description = description
        self.total_fee = total_fee

# StudentFeeAssignment model
class StudentFeeAssignment(db.Model):
    __tablename__ = 'StudentFeeAssignment'
    
    fee_assignment_id = db.Column('FeeAssignmentId', db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column('StudentId', db.String, ForeignKey('User.Id', ondelete='CASCADE'))
    structure_id = db.Column('StructureId', db.String, ForeignKey('FeeStructure.StructureId', ondelete='SET NULL'))
    
    # Relationships
    student = relationship('User', back_populates='student_fees')
    structure = relationship('FeeStructure', back_populates='student_assignments')
    fee_records = relationship('FeeRecord', back_populates='assignment')

# FeeRecord model
class FeeRecord(db.Model):
    __tablename__ = 'FeeRecord'
    fee_record_id = db.Column('FeeRecordId', db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    fee_assignment_id = db.Column('FeeAssignmentId', db.String, ForeignKey('StudentFeeAssignment.FeeAssignmentId', ondelete='CASCADE'))
    status_id = db.Column('StatusId', db.String, ForeignKey('PaymentStatus.StatusId', ondelete='SET NULL'))
    flagged_for_followup = db.Column('FlaggedForFollowUp', db.Integer, nullable=False, default=0)  # 0 = Not Flagged, 1 = Flagged
    date_assigned = db.Column('DateAssigned', db.Date, nullable=False)
    due_date = db.Column('DueDate', db.Date, nullable=False)
    amount_due = db.Column('AmountDue', db.Numeric(10, 2), nullable=False)
    late_fee_amount = db.Column('LateFeeAmount', db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column('DiscountAmount', db.Numeric(10, 2), nullable=False)
    total_amount = db.Column('TotalAmount', db.Numeric(10, 2), nullable=False)
    last_updated_date = db.Column('LastUpdatedDate', db.Date, nullable=False)

    # Relationships
    assignment = relationship('StudentFeeAssignment', back_populates='fee_records')
    status = relationship('PaymentStatus', back_populates='fee_records')
    payment_histories = relationship('PaymentHistory', back_populates='fee_record')

# ParentStudentRelation model
from sqlalchemy.sql import func

class ParentStudentRelation(db.Model):
    __tablename__ = 'ParentStudentRelation'
    
    relation_id = db.Column('RelationId', db.String, primary_key=True)
    parent_id = db.Column('ParentId', db.String, ForeignKey('User.Id', ondelete='CASCADE'))
    student_id = db.Column('StudentId', db.String, ForeignKey('User.Id', ondelete='CASCADE'))

    # Relationships
    parent = relationship('User', back_populates='parent_relations', foreign_keys=[parent_id])
    student = relationship('User', back_populates='student_relations', foreign_keys=[student_id])

    @staticmethod
    def generate_relation_id():
        """Generate the next relation_id as 'relation1', 'relation2', etc."""
        latest_relation = db.session.query(ParentStudentRelation).filter(
            ParentStudentRelation.relation_id.like('relation%')
        ).order_by(
            db.cast(func.substring(ParentStudentRelation.relation_id, 9), db.Integer).desc()
        ).first()
        
        if latest_relation:
            next_number = int(latest_relation.relation_id[8:]) + 1  # Extract number and increment
        else:
            next_number = 1  # Start from relation1 if no existing records

        return f"relation{next_number}"

    def __init__(self, parent_id, student_id):
        self.relation_id = self.generate_relation_id()
        self.parent_id = parent_id
        self.student_id = student_id


# PaymentHistory model
class PaymentHistory(db.Model):
    __tablename__ = 'PaymentHistory'
    history_id = db.Column('PaymentHistoryId', db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    fee_record_id = db.Column('FeeRecordId', db.String, ForeignKey('FeeRecord.FeeRecordId', ondelete='CASCADE'))
    amount_paid = db.Column('AmountPaid', db.Numeric(10, 2), nullable=False)
    payment_method = db.Column('PaymentMethod', db.String, nullable=False)
    payment_date = db.Column('PaymentDate', db.DateTime, nullable=False)

    # Relationships
    fee_record = relationship('FeeRecord', back_populates='payment_histories')

# PaymentStatus model
class PaymentStatus(db.Model):
    __tablename__ = 'PaymentStatus'
    status_id = db.Column('StatusId', db.String, primary_key=True)
    status_name = db.Column('StatusName', db.String, nullable=False)

    # Relationships
    fee_records = relationship('FeeRecord', back_populates='status')

# Notification model
class Notification(db.Model):
    __tablename__ = 'Notification'
    notification_id = db.Column('NotificationId', db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_id = db.Column('TeacherId', db.String, ForeignKey('User.Id'))
    student_id = db.Column('StudentId', db.String, ForeignKey('User.Id'))
    message_type = db.Column('MessageType', db.String, nullable=False)
    message_text = db.Column('MessageText', db.String, nullable=False)
    timestamp = db.Column('Timestamp', db.DateTime, nullable=False)

    # Relationships
    teacher = db.relationship('User', back_populates='messages_sent', foreign_keys=[teacher_id], single_parent=True)
    student = db.relationship('User', back_populates='messages_received', foreign_keys=[student_id])

# MessageTemplate model
class MessageTemplate(db.Model):
    __tablename__ = 'MessageTemplate'
    message_temp_id = db.Column('TemplateId', db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category = db.Column('Category', db.String, nullable=False)
    template_text = db.Column('TemplateText', db.String, nullable=False)

# Settings model
class Settings(db.Model):
    __tablename__ = 'Settings'
    setting_key = db.Column('SettingKey', db.String, primary_key=True)
    setting_value = db.Column('SettingValue', db.String, nullable=False)
    description = db.Column('Description', db.String, nullable=False)
    category = db.Column('Category', db.String, nullable=False)
