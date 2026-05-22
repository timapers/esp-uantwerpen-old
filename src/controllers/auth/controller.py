from src.controllers.auth.login_form import LoginForm
from src.controllers.auth.ldap import check_credentials, get_user
from flask_login import current_user, login_user, logout_user, login_required
from flask import redirect, render_template, Blueprint

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')

    form = LoginForm()
    if form.validate_on_submit():

        user_id = str(form.username.data)
        password = str(form.password.data)

        if not check_credentials(user_id, password):
            return render_template('login.html', form=form, error="Invalid username or password")

        user = get_user(user_id, password)
        if user is None:
            return render_template('login.html', form=form, error="Cannot find user")
        login_user(user)

        if user.is_new:
            url_param = "?new=True"
        else:
            url_param = ""

        return redirect('/' + url_param)

    return render_template('login.html', form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('/')
