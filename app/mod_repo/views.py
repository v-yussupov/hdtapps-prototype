from flask import Blueprint, jsonify, request, abort
from app.mod_repo import package_manager, file_handler, db_handler
from app.mod_repo.models import Transformation
from app.mod_tm import deployer
import traceback

mod_repo = Blueprint('repo', __name__)


# Set the route and accepted methods
@mod_repo.route('/apps')
def find_apps():
    tags = request.args.getlist('tags[]')
    apps = db_handler.find_apps_by_tags(tags)
    for app in apps:
        app["appInfo"].pop('path', None)

    return jsonify(apps), 200


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


@mod_repo.route('/apps/<app_id>')
def get_app_by_id(app_id):
    doc = db_handler.find_app(app_id)
    doc["appInfo"].pop('path', None)

    return jsonify(doc)


@mod_repo.route('/apps/<app_id>', methods=['DELETE'])
def delete_app(app_id):
    doc = db_handler.find_app(app_id)
    path = doc["appInfo"]["path"]
    file_handler.remove_dir_tree(path)
    db_handler.delete_app(app_id)

    return jsonify({"status": "OK"})


@mod_repo.route('/apps/<app_id>', methods=['PUT'])
def update_app(app_id):

    return jsonify({"TODO": "update the app"}), 501


@mod_repo.route('/apps/<app_id>/transformations')
def get_transfs_by_app_id(app_id):
    doc = db_handler.find_app_transformations(app_id)

    return jsonify(doc)


@mod_repo.route('/transformations')
def find_transformations():
    qname = request.args.get('qname')
    if qname:
        t = db_handler.find_transformation_by_qname(qname)

        return jsonify(t)

    else:
        pnum = int(request.args.get('pnum'))
        infiles = request.args.getlist('infile[]')
        infsets = request.args.getlist('infsets[]')
        outfile = request.args.getlist('outfile[]')
        strict = request.args.getlist('strict')
        
        signature = Transformation.generate_signature(pnum=pnum, infiles=infiles, infilesets=infsets, outfiles=outfile)

        t_list = db_handler.find_transformation_by_signature(signature, strict)

        return jsonify(t_list)


@mod_repo.route('/transformations/<t_id>')
def get_transform_by_id(t_id):
    t = db_handler.find_transformation_by_id(t_id)

    return jsonify(t)


def request_wants_json():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']
