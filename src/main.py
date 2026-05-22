from flask import Flask, request, session, jsonify, render_template
from flask_login import LoginManager, current_user
from flask_assets import Environment, Bundle

from src.controllers.auth import ldap
from src.config import config_data
from src.utils.languages import languages, get_text, language_dict
from src.models.db import close_db

# Blueprints
from src.controllers.supporting_lists.controller import bp as supporting_lists_blueprint
from src.controllers.auth.controller import bp as auth_blueprint
from src.controllers.projects.controller import bp as projects_blueprint
from src.controllers.home import bp as home_blueprint
from src.controllers.tags import bp as tags_blueprint
from src.controllers.cookies import bp as cookies_blueprint
from src.controllers.profile import bp as profile_blueprint
from src.controllers.mails import bp as mails_blueprint
from src.controllers.careers.controller import bp as careers_blueprint
from src.controllers.calendar import bp as calendar_blueprint

app = Flask(__name__)
app.teardown_appcontext(close_db)
app.secret_key = config_data['secret-key']
app.config.update(config_data)
app.config['TEMPLATES_AUTO_RELOAD'] = True

app.register_blueprint(auth_blueprint)
app.register_blueprint(supporting_lists_blueprint)
app.register_blueprint(projects_blueprint)
app.register_blueprint(home_blueprint)
app.register_blueprint(tags_blueprint)
app.register_blueprint(cookies_blueprint)
app.register_blueprint(profile_blueprint)
app.register_blueprint(mails_blueprint)

app.register_blueprint(careers_blueprint)
app.register_blueprint(calendar_blueprint)

login_manager = LoginManager()
login_manager.init_app(app)

assets = Environment(app)
assets.register('projects', Bundle('js/projects/edit.js',
                                   'js/projects/filter.js',
                                   'js/projects/index.js',
                                   'js/projects/projects_list.js',
                                   'js/projects/url_params.js',
                                   output='gen/packed.js'))

assets.register('internships', Bundle('js/internships/edit.js',
                                      'js/internships/filter.js',
                                      'js/internships/index.js',
                                      'js/internships/url_params.js',
                                      'js/internships/internship_list.js',
                                      output='gen/packed.js'))


# Injects variables and functions, so they can be used in the templates
@app.context_processor
def context_processor():
    # Function to get the current arguments, used in the templates for urls
    def get_args_string():
        string = "?"
        for key in request.args:
            if key not in ['lang', 'theme', 'archive']:
                string += key + "=" + request.args[key] + "&"
        return string

    return {"get_args": get_args_string,
            "current_theme": session['theme'],
            "current_language": session['lang'],
            "get_text": lambda key, lang=session['lang']: get_text(key, lang),
            "archive_active": session['archive'],
            "contact_mail": config_data.get('contact-mail', 'max.vanhoucke@student.uantwerpen.be')
            }


# Handle any url parameters
@app.before_request
def before_request():
    language = request.args.get('lang')
    if language and language in languages:
        session['lang'] = language
    theme = request.args.get('theme')
    if theme and theme in ['light', 'dark']:
        session['theme'] = theme
    archive = request.args.get('archive')
    if archive and archive in ['true', 'false']:
        session['archive'] = archive == 'true'

    # Make sure session variables are set
    session['lang'] = session.get('lang', 'en')
    session['theme'] = session.get('theme', 'light')
    session['archive'] = session.get('archive', False)

    # Only admins and employees can get the archive
    if not current_user.is_authenticated or current_user.role == "student":
        session['archive'] = False


@login_manager.user_loader
def load_user(user_id):
    u = ldap.get_user(user_id)
    if u is None:
        return None
    extra_admins = config_data.get('student-admins', [])
    if user_id in extra_admins:
        u.role = 'admin'
    return u


@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/get-translation-dict')
def get_translation_dict():
    """
    Returns a dictionary with all translations for the current language.
    :return: Dictionary with all translations.
    """
    return jsonify(language_dict)
