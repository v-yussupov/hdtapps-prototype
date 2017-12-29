from flask import Blueprint, request, abort, jsonify
from app.mod_repo import db_handler
from app.mod_tm import task_processor

# Define the blueprint: 'tm'
mod_tm = Blueprint('tm', __name__)


@mod_tm.route('/tasks', methods=['POST'])
def deploy():
    if not request.json:
        abort(400)
    req_body = request.json

    app = db_handler.find_app(req_body["appID"])
    t = db_handler.find_transformation_by_id(req_body["transformationID"])

    task_id = task_processor.generate_task_id(app["appInfo"]["appName"])
    task_path = task_processor.generate_task_folder(task_id)

    mapped_params = task_processor.map_input_params(req_body, t)
    mapped_files = task_processor.prepare_input_files(task_path, req_body, t)
    mapped_filesets = task_processor.prepare_input_filesets(task_path, req_body, t)

    inv_cmd = task_processor.build_inv_cmd(app, t, mapped_params, mapped_files, mapped_filesets)

    provider = task_processor.choose_provider(req_body["providers"])
    app_image = task_processor.get_docker_image(provider["pkgID"])
    app_container = task_processor.create_docker_container(app_image, inv_cmd)

    if mapped_files is not None:
        # copy input files to container
        pass

    if mapped_filesets is not None:
        # copy input filesets to container
        print(mapped_filesets)
        for a in mapped_filesets:
            fs = mapped_filesets[a]
            req_input_path = task_processor.get_required_path(fs["requiredPath"])
            task_processor.copy_dir_to_container(app_container, fs["linkToArchive"], req_input_path)

    task_processor.start_container(app_container)

    if task_processor.wait_for_container_finish(app_container) == 0:
        for o in t["outputFiles"]:
            output_dir = task_processor.get_required_path(o["accessPath"])
            filename = o["outputName"] + "." + o["format"]
            output_path = output_dir + filename
            task_processor.copy_output_from_container(app_container, output_path, task_path)

            # task_processor.post_output_to_consumer(task_path, filename, req_body["resultsEndpoint"])

        task_processor.remove_container(app_container)

        # TODO: clean up and make proper responses

        return jsonify("OK"), 200

    else:
        return jsonify("error"), 500