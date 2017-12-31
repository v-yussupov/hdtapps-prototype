from flask import Flask, render_template, redirect, request
from config import config, Config
from celery import Celery

celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)


def create_app(config_name):
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.config.from_object(config[config_name])
    # config[config_name].init_app(app)

    celery.conf.update(app.config)

    @app.before_request
    def clear_trailing():
        rp = request.path
        if rp != '/' and rp.endswith('/'):
            return redirect(rp[:-1])

    # attach routes and custom error pages here

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error_templates/404.html'), 404

    @app.errorhandler(405)
    def page_not_found(e):
        return render_template('error_templates/405.html'), 405

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('error_templates/500.html'), 500



    # repository blueprint
    from app.mod_repo.views import mod_repo as repository_module
    app.register_blueprint(repository_module)

    # task manager blueprint
    from app.mod_tm.views import mod_tm as task_manager_module
    app.register_blueprint(task_manager_module)

    # swagger-ui blueprint
    from app.mod_swagger_ui.views import mod_swagger_ui
    app.register_blueprint(mod_swagger_ui)

    # app.register_blueprint(xyz_module)

    return app
