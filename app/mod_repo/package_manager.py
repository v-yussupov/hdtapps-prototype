import json
import os
from app.mod_repo.models import *
from app.mod_repo.dockerfile_generator import Dockerfile


def read_package_specification(temp_app_dir):
    try:
        pkg_spec_path = os.path.join(temp_app_dir, "app-spec.json")
        with open(pkg_spec_path) as data_file:
            data = json.load(data_file)
        return data

    except Exception as e:
        pass


def deserialize_package_specification(temp_app_dir):
    try:
        pkg_spec_path = os.path.join(temp_app_dir, "app-spec.json")
        with open(pkg_spec_path, 'r') as pkg_spec_file:
            data = json.load(pkg_spec_file)
        obj = dict_to_app_pkg_spec_object(data)

        return obj
    except Exception as e:
        print(e)


def generate_dockerfile(pkg_spec: ApplicationSpecification, path) -> bool:
    try:
        d = Dockerfile(pkg_spec)
        d.save(path)

        return True
    except:
        # TODO: handle exception

        return False

