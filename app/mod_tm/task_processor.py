from config import BASE_DIR
import docker, os, uuid, requests, mimetypes, tarfile, time
from pyunpack import Archive
from io import BytesIO
import celery
from app.mod_repo import db_handler
from app.mod_tm.models import TransformationTask


def get_docker_client():
    return docker.from_env()


def get_docker_image(image_id):
    client = get_docker_client()
    return client.images.get(image_id)


def get_docker_container(container_id):
    client = get_docker_client()
    return client.containers.get(container_id)


def create_docker_container(image_obj, inv_cmd):
    client = get_docker_client()
    return client.containers.create(image_obj, inv_cmd)


def start_container(container_obj):
    container_obj.start()


def remove_container(container_obj):
    container_obj.remove(v=True)


def get_container_status(container_id):
    container = get_docker_container(container_id)
    return container.status


def wait_for_container_finish(container_obj):
    exit_code = container_obj.wait()
    return exit_code


def get_required_path(path_str):
    if path_str.startswith("{r}"):
        # process path relative to app's folder
        path_str = path_str.replace("{r}", "/app")
        return path_str
    else:
        # process absolute container path
        return None


def create_file_tarball(artifact_file):
    pw_tarstream = BytesIO()
    pw_tar = tarfile.TarFile(fileobj=pw_tarstream, mode='w')
    file_data = open(artifact_file, 'r').read()
    tarinfo = tarfile.TarInfo(name=artifact_file)
    tarinfo.size = len(file_data)
    tarinfo.mtime = time.time()
    # tarinfo.mode = 0600
    pw_tar.addfile(tarinfo, BytesIO(file_data))
    pw_tar.close()
    pw_tarstream.seek(0)
    return pw_tarstream


def create_fileset_tarball(fileset_dir):
    tar_stream = BytesIO()
    tar = tarfile.TarFile(fileobj=tar_stream, mode='w')
    tar.add(fileset_dir, arcname=os.path.sep)
    tar.close()
    tar_stream.seek(0)
    return tar_stream


def copy_dir_to_container(container_obj, fileset_dir, req_path):
    with create_fileset_tarball(fileset_dir) as archive:
        container_obj.put_archive(req_path, archive)
    return True


def copy_file_to_container(container_obj, artifact_file, req_path):
    with create_file_tarball(artifact_file) as archive:
        container_obj.put_archive(req_path, archive)
    return True


def copy_output_from_container(container_obj, output_path, destination):
    stream, stat = container_obj.get_archive(output_path)
    raw_data = stream.read()
    output_dir = os.path.join(destination, "output")
    temp_tar = os.path.join(output_dir, "archive.tar")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    f = open(temp_tar, 'wb')
    f.write(raw_data)
    Archive(temp_tar).extractall(destination)
    os.remove(temp_tar)
    return True


def post_output_to_consumer(task_path, filename, endpoint):
    output_path = os.path.join(task_path, filename)
    data = open(output_path, 'rb').read()
    res = requests.post(url=endpoint,
                        data=data,
                        headers={'Content-Type': 'application/octet-stream'})


@celery.task(bind=True)
def run_transformation_task(self, request_body):

    task_obj = TransformationTask(request_body, self.request.id)
    app_image = get_docker_image(task_obj.provider["pkgID"])
    app_container = create_docker_container(app_image, task_obj.invocation_cmd)

    self.update_state(state="PROGRESS", meta=populate_meta_info(app_container.id))

    if task_obj.input_files_map is not None:
        # copy input files to container
        pass

    if task_obj.input_filesets_map is not None:
        # copy input filesets to container
        for a in task_obj.input_filesets_map:
            fs = task_obj.input_filesets_map[a]
            req_input_path = get_required_path(fs["requiredPath"])
            copy_dir_to_container(app_container, fs["linkToArchive"], req_input_path)

    start_container(app_container)

    self.update_state(state="PROGRESS", meta=populate_meta_info(app_container.id))
    if wait_for_container_finish(app_container) == 0:
        for o in task_obj.transform["outputFiles"]:
            output_dir = get_required_path(o["accessPath"])
            filename = o["outputName"] + "." + o["format"]
            output_path = output_dir + filename
            copy_output_from_container(app_container, output_path, task_obj.task_folder_path)

            # task_processor.post_output_to_consumer(task_path, filename, req_body["resultsEndpoint"])


        remove_container(app_container)
        self.update_state(state="SUCCESS", meta=populate_meta_info(None))
    else:
        self.update_state(state="FAILURE", meta=populate_meta_info(app_container.id))


        # TODO: clean up and make proper status updates


def populate_meta_info(container_id):
    if not container_id is None:
        c = get_docker_container(container_id)

        return {
            "container_id": c.id,
            "container_status": c.status
        }
    else:
        return {
            "container_id": "",
            "container_status": "REMOVED"
        }