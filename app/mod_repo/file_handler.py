from config import BASE_DIR
import uuid
import requests
import mimetypes
import os
from pyunpack import Archive
import glob
import shutil


def get_app_archive_from_url(app_name, url_string) -> str:
    try:
        temp_name = generate_temp_folder_name(app_name)
        root_temp_folder = get_temp_app_directory_path()
        temp_app_folder = os.path.join(root_temp_folder, temp_name)
        create_folder_if_not_exists(temp_app_folder)

        response = requests.get(url_string, stream=True)
        content_type = response.headers['content-type']
        extension = mimetypes.guess_extension(content_type)
        temp_file = "archive" + extension
        temp_path = os.path.join(temp_app_folder, temp_file)

        with open(temp_path, 'wb') as f:
            for chunk in response:
                f.write(chunk)

        Archive(temp_path).extractall(temp_app_folder)
        os.remove(temp_path)

        return temp_app_folder

    except Exception as e:
        print(e)
        # TODO: handle exceptions
        pass


def generate_temp_id():
    return uuid.uuid4().hex


def get_root_repo_folder():
    root_repo_path = os.path.join(BASE_DIR, "data", "repo")
    create_folder_if_not_exists(root_repo_path)

    return root_repo_path


def get_temp_app_directory_path():
    root_repo_path = get_root_repo_folder()
    temp_dir = os.path.join(root_repo_path, "temp")
    create_folder_if_not_exists(temp_dir)
    return temp_dir


def get_pub_app_directory_path():
    root_repo_path = get_root_repo_folder()
    app_dir = os.path.join(root_repo_path, "applications")
    create_folder_if_not_exists(app_dir)
    return app_dir


def generate_temp_folder_name(app_name):
    return app_name + "_" + generate_temp_id()


def store_app_files(temp_app_path, app_id):
    apps_folder = get_pub_app_directory_path()
    destination_folder = os.path.join(apps_folder, app_id)
    recursive_copy_files(temp_app_path, destination_folder)
    shutil.make_archive(os.path.join(destination_folder, "prov-pkg"), 'gztar', temp_app_path)
    remove_dir_tree(temp_app_path)

    return destination_folder


def recursive_copy_files(source_path, destination_path, override=False):
    files_count = 0
    if not os.path.exists(destination_path):
        os.mkdir(destination_path)
    items = glob.glob(source_path + '/*')
    for item in items:
        if os.path.isdir(item):
            path = os.path.join(destination_path, item.split('/')[-1])
            files_count += recursive_copy_files(source_path=item, destination_path=path, override=override)
        else:
            file = os.path.join(destination_path, item.split('/')[-1])
            if not os.path.exists(file) or override:
                shutil.copyfile(item, file)
                files_count += 1
    return files_count


def remove_dir_tree(app_path):
    shutil.rmtree(app_path)
    return True


def create_folder_if_not_exists(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except Exception as e:
        print(e)
        pass