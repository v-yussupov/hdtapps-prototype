from flask import Blueprint, jsonify, request, abort
from app.mod_repo import package_manager
from app.mod_repo import file_handler
from app.mod_repo import db_handler
from bson.objectid import ObjectId
from app.mod_tm import deployer
from app.mod_repo.dockerfile_generator import Dockerfile
import traceback

mod_repo = Blueprint('repo', __name__)


# Set the route and accepted methods
@mod_repo.route('/apps')
def find_apps():
    if request_wants_json():
        return jsonify({"text": "TODO: list apps!"})
    return jsonify("TODO: list apps!"), 501


@mod_repo.route('/apps', methods=['POST'])
def publish_app():
    if not request.json:
        abort(400)

    data = request.json
    temp_app_path = file_handler.get_app_archive_from_url(data["name"], data["archiveURL"])

    pkg_spec = package_manager.deserialize_package_specification(temp_app_path)
    package_manager.generate_dockerfile(pkg_spec, temp_app_path)

    try:
        if data["deploy"] is True:
            tag = deployer.generate_image_tag(pkg_spec.app_info.name, pkg_spec.app_info.version)
            provider = deployer.deploy_app(temp_app_path, tag)
            pkg_spec.app_info.providers.append(provider)

            for t in pkg_spec.t_specs:
                t.providers.append(provider)
    except:
        # deployment unsuccessful
        # TODO: rollback everything
        print("deployment error")
        return jsonify("deployment error"), 500

    try:
        app_path = file_handler.store_app_files(temp_app_path, pkg_spec.app_info.id)
        pkg_spec.app_info.path = app_path
    except:
        # storing files went wrong
        print("file system storage error")
        return jsonify("file system storage error"), 500

    try:
        pkg_spec = db_handler.store_app(pkg_spec)

    except Exception:
        # storing app in DB error
        print("DB storage error")
        print(traceback.format_exc())
        return jsonify("DB storage error"), 500

    if data["test"] is True:
        # perform a test run
        pass

    return jsonify(pkg_spec.to_json_str())


@mod_repo.route('/apps/<appID>')
def get_app_by_id(appID):
    doc = db_handler.find_app(appID)
    doc["appInfo"].pop('path', None)

    return jsonify(doc)


@mod_repo.route('/apps/<appID>', methods=['DELETE'])
def delete_app(appID):
    doc = db_handler.find_app(appID)
    path = doc["appInfo"]["path"]
    file_handler.remove_dir_tree(path)
    db_handler.delete_app(appID)

    return jsonify({"status": "OK"})


@mod_repo.route('/transformations/<transformationID>')
def get_transform_by_id(transformationID):
    t = db_handler.find_transformation(transformationID)

    return jsonify(t)


def request_wants_json():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']
