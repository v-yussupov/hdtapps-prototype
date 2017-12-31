from flask import Blueprint, request, abort, jsonify
from app.mod_tm import task_processor

# Define the blueprint: 'tm'
mod_tm = Blueprint('tm', __name__)


@mod_tm.route('/tasks', methods=['POST'])
def deploy():
    if not request.json:
        abort(400)
    req_body = request.json

    task = task_processor.run_transformation_task.apply_async(args=[req_body])

    return jsonify(
        {
            "taskID": task.id,
            "state": task.state
        }
    )


@mod_tm.route('/tasks/<task_id>')
def get_task_by_id(task_id):
    task = task_processor.run_transformation_task.AsyncResult(task_id)
    if task.info is not None:
        response = {
            'state': task.state,
            'container_id': task.info.get('container_id', ''),
            'container_status': task.info.get('container_status', '')
        }
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'container_id': '',
            'container_status': '',
            'status': str(task.info),  # this is the exception raised
        }

    return jsonify(response)

