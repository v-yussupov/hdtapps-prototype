from flask import Blueprint, jsonify, url_for, render_template
# Define the blueprint: 'tm'
mod_swagger_ui = Blueprint('swagger-ui', __name__)


@mod_swagger_ui.route('/ui')
def deploy():
    return render_template('mod_swagger_ui/index.html')