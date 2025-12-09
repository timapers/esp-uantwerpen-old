import ssl
from ldap3 import *
from src.controllers.auth.user import User
from src.controllers.auth.config import config_data
from flask import g
from src.models import StudentDataAccess, Student, EmployeeDataAccess, Employee
from src.models.db import get_db
from src.controllers.profile import get_random_picture_location


def get_server():
    """
    :return: ldap3 Server object
    """
    try:
        if 'ldap' not in g:
            tls = Tls(validate=ssl.CERT_REQUIRED, version=ssl.PROTOCOL_TLSv1_2)
            g.ldap = Server(config_data['server'], use_ssl=False, tls=tls, port=389)
        return g.ldap
    except Exception as e:
        print(str(e))
        return Server(config_data['server'], use_ssl=False)


def check_credentials(user_id, password):
    """
    :param user_id: student number or employee identification
    :param password: the user password
    :return: Boolean indicating if the credentials are correct
    """
    if config_data.get('dev', False):
        return True

    server = get_server()
    try:
        conn = Connection(server, user=user_id + config_data['suffix'], password=password, auto_bind=AUTO_BIND_TLS_BEFORE_BIND)
        conn.start_tls()
        conn.bind()
        return True
    except:
        return False


def get_user(user_id: str, password: str = None):
    """
    Returns the User with the given user_id
    First it's checked in the DB (doesn't check the password)
    If not found there, a query to the ldap is used to gather the information.
    If the password is correct, the data will be retrieved and added to the DB.
    :param user_id: student number or employee identification
    :param password: the user password
    :return: User object
    """

    # Check if it's an employee
    employee_access = EmployeeDataAccess(get_db())
    try:
        employee = employee_access.get_employee(user_id)
        return User(user_id, employee.name, 'admin' if employee.is_admin else 'employee', False)
    except:
        pass

    # Check if it's a student
    student_access = StudentDataAccess(get_db())
    try:
        student = student_access.get_student(user_id)
        return User(user_id, student.name, 'student', False)
    except:
        pass

    if password is None:
        return None

    return new_person(user_id, password)


def new_person(user_id, password):
    """
    Person is added to the DB with the data retrieved from LDAP
    :param user_id: student number or employee identification
    :param password: the user password
    :return: None if nothing found, else the new User
    """
    # Make a search request to LDAP
    person = search_person(user_id, password)

    if person is None:
        return None

    if 'student' in person['distinguishedName'].value.lower():
        # Make new student
        name = person['displayName'].value
        student = Student(name, user_id)
        StudentDataAccess(get_db()).add_student(student)
        return User(user_id, name, 'student', False)

    else:
        # Make new employee
        name = person['displayName'].value
        email = person['mail'].value
        office = person['physicalDeliveryOfficeName'].value
        picture = get_random_picture_location()

        employee = Employee(user_id, name, email, office, None, picture, None, None, False, False, True, False)
        EmployeeDataAccess(get_db()).add_employee(employee)
        return User(user_id, name, 'employee', True)


def search_person(user_id, password):
    """
    Searches a person in LDAP
    :param user_id: student number or employee identification
    :param password: the user password
    :return: ldap3 object of the person, None if not found
    """
    # Connect
    server = get_server()
    connection = Connection(server, user=user_id + config_data['suffix'], password=password, auto_bind=True)

    # Search (with Reader so injection attack cannot happen)
    definition = ObjectDef(['organizationalPerson', 'person'], connection)
    reader = Reader(connection, object_def=definition, base='ou=UA-Users,dc=ad,dc=ua,dc=ac,dc=be',
                    query='(sAMAccountName={})'.format(user_id))
    entries = reader.search()

    if len(entries) == 0:
        return None

    return entries[0]


if __name__ == '__main__':
    pass
