from config import BASE_DIR
import docker
import uuid
import os
import requests
import mimetypes
from pyunpack import Archive
from io import BytesIO
import tarfile
import time


def map_input_params(req_body, transformation):

    if "inputParams" in req_body:
        req_params = req_body["inputParams"]
        t_params = transformation["inputParams"]

        num_params = []
        str_params = []
        for p in req_params:
            if p["paramType"] == "int" or p["paramType"] == "integer":
                num_params.append(p)
            else:
                str_params.append(p)

        params_map = {}
        for param in t_params:
            if param["type"] == "string" or param["type"] == "str":
                params_map[param["alias"]] = str_params.pop()
            else:
                params_map[param["alias"]] = num_params.pop()

        return params_map

    return None


def map_input_files(req_files, t_files):
    req_files_dict = {}
    for f in req_files:
        if f["format"] not in req_files_dict:
            req_files_dict[f["format"]] = []
        req_files_dict[f["format"]].append(f["link"])
    files_map = {}
    for file in t_files:
        files_map[file["alias"]] = file
        files_map[file["alias"]]["link"] = req_files_dict[file["format"]].pop()

    return files_map


def map_input_filesets(req_file_sets, t_file_sets):
    req_file_sets_dict = {}
    for fs in req_file_sets:
        if fs["format"] not in req_file_sets_dict:
            req_file_sets_dict[fs["format"]] = []
        req_file_sets_dict[fs["format"]].append(fs["linkToArchive"])
    filesets_map = {}
    for fileset in t_file_sets:
        link = req_file_sets_dict[fileset["format"]].pop()
        filesets_map[fileset["alias"]] = fileset
        filesets_map[fileset["alias"]]["linkToArchive"] = link

    return filesets_map


def prepare_input_files(task_id, req_body, transformation):

    if "inputFiles" in req_body:
        m = map_input_files(req_body["inputFiles"], transformation["inputFiles"])
        for a in m:
            f = m[a]

        return m

    return None


def prepare_input_filesets(task_files_path, req_body, transformation):

    if "inputFileSets" in req_body:
        m = map_input_filesets(req_body["inputFileSets"], transformation["inputFileSets"])
        for a in m:
            fs = m[a]
            response = requests.get(fs["linkToArchive"], stream=True)
            content_type = response.headers['content-type']
            extension = mimetypes.guess_extension(content_type)
            temp_file = "archive" + extension
            temp_dir = os.path.join(task_files_path, a.replace("$", ""))
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            temp_path = os.path.join(temp_dir, temp_file)

            with open(temp_path, 'wb') as f:
                for chunk in response:
                    f.write(chunk)

            Archive(temp_path).extractall(temp_dir)
            os.remove(temp_path)
            fs["linkToArchive"] = temp_dir
        return m

    return None


def build_inv_cmd(app, transformation, p_map, f_map, fs_map):
    result = []
    invocation = choose_invocation(app["invocations"])
    aliases = {}
    for word in invocation["command"].split():
        if word.startswith('$'):
            aliases[word] = True

    if "inputParams" in transformation:
        for p in transformation["inputParams"]:
            if p["alias"] in aliases:
                invocation["command"] = invocation["command"].replace(p["alias"], p_map[p["alias"]]["value"])
                aliases.pop(p["alias"], None)

    if "inputFiles" in transformation:
        for f in transformation["inputFiles"]:
            if f["alias"] in aliases:
                aliases.pop(f["alias"], None)
                # process input files
                pass

    if "inputFileSets" in transformation:
        for f in transformation["inputFileSets"]:
            if f["alias"] in aliases:
                aliases.pop(f["alias"], None)
                # process input filesets
                pass

    if not bool(aliases):
        # exception: not all aliases in the command were mapped
        pass

    return invocation["command"]


def choose_invocation(invocations_list):
    return invocations_list[0]


def choose_provider(providers_list):
    return providers_list[0]


def generate_task_id(app_name):
    app_str = app_name[0] + app_name[-1]
    return app_str + "_" + uuid.uuid4().hex


def get_root_repo_folder():
    root_repo_path = os.path.join(BASE_DIR, "data", "tasks")
    create_folder_if_not_exists(root_repo_path)

    return root_repo_path


def create_folder_if_not_exists(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except Exception as e:
        print(e)
        pass


def generate_task_folder(task_id):
    path = os.path.join(get_root_repo_folder(), task_id)
    create_folder_if_not_exists(path)

    return path


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
