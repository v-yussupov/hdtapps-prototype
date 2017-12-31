import os, uuid, mimetypes, requests
from app.mod_repo import db_handler
from config import BASE_DIR
from pyunpack import Archive


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


class TransformationTask:
    def __init__(self, request_body, task_id):

        self.app = db_handler.find_app(request_body["appID"])
        self.transform = db_handler.find_transformation_by_id(request_body["transformationID"])
        self.task_id = task_id
        self.task_folder_path = self.__create_task_folder()
        self.input_params_map = self.__generate_parameter_mappings(request_body)
        self.input_files_map = self.__generate_ifile_mappings(request_body)
        self.input_filesets_map = self.__generate_ifileset_mappings(request_body)
        self.provider = self.__choose_provider(request_body)
        self.result_endpoint = request_body["resultsEndpoint"]

        self.__materialize_input_files()
        self.__materialize_input_filesets()

        self.invocation_cmd = self.build_inv_cmd()

    def __create_task_folder(self):
        path = os.path.join(get_root_repo_folder(), self.task_id)
        create_folder_if_not_exists(path)
        return path

    def __generate_parameter_mappings(self, request_body) -> dict:
        if "inputParams" in request_body:
            req_params = request_body["inputParams"]
            t_params = self.transform["inputParams"]
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

        else:
            # no input params
            return {}

    def __generate_ifile_mappings(self, request_body) -> dict:
        if "inputFiles" in request_body:
            req_files_dict = {}
            for f in request_body["inputFiles"]:
                if f["format"] not in req_files_dict:
                    req_files_dict[f["format"]] = []
                req_files_dict[f["format"]].append(f["link"])
            files_map = {}
            for file in self.transform["inputFiles"]:
                files_map[file["alias"]] = file
                files_map[file["alias"]]["link"] = req_files_dict[file["format"]].pop()

            return files_map

        else:
            return {}

    def __generate_ifileset_mappings(self, request_body) -> dict:
        if "inputFileSets" in request_body:
            req_file_sets_dict = {}
            for fs in request_body["inputFileSets"]:
                if fs["format"] not in req_file_sets_dict:
                    req_file_sets_dict[fs["format"]] = []
                req_file_sets_dict[fs["format"]].append(fs["linkToArchive"])
            filesets_map = {}
            for fileset in self.transform["inputFileSets"]:
                link = req_file_sets_dict[fileset["format"]].pop()
                filesets_map[fileset["alias"]] = fileset
                filesets_map[fileset["alias"]]["linkToArchive"] = link

            return filesets_map

        else:
            return {}

    def __materialize_input_files(self):
        pass

    def __materialize_input_filesets(self):
        for a in self.input_filesets_map:
            response = requests.get(self.input_filesets_map[a]["linkToArchive"], stream=True)
            content_type = response.headers['content-type']
            extension = mimetypes.guess_extension(content_type)
            temp_file = "archive" + extension
            temp_dir = os.path.join(self.task_folder_path, a.replace("$", ""))
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            temp_path = os.path.join(temp_dir, temp_file)

            with open(temp_path, 'wb') as f:
                for chunk in response:
                    f.write(chunk)

            Archive(temp_path).extractall(temp_dir)
            os.remove(temp_path)
            self.input_filesets_map[a]["linkToArchive"] = temp_dir

    def __choose_invocation(self):
        return self.app["invocations"][0]

    def build_inv_cmd(self):
        invocation = self.__choose_invocation()
        aliases = {}
        for word in invocation["command"].split():
            if word.startswith('$'):
                aliases[word] = True

        if "inputParams" in self.transform:
            for p in self.transform["inputParams"]:
                if p["alias"] in aliases:
                    invocation["command"] = invocation["command"].replace(p["alias"], self.input_params_map[p["alias"]]["value"])
                    aliases.pop(p["alias"], None)

        if "inputFiles" in self.transform:
            for f in self.transform["inputFiles"]:
                if f["alias"] in aliases:
                    aliases.pop(f["alias"], None)
                    # TODO: process input files
                    pass

        if "inputFileSets" in self.transform:
            for f in self.transform["inputFileSets"]:
                if f["alias"] in aliases:
                    aliases.pop(f["alias"], None)
                    # TODO: process input filesets
                    pass

        if not bool(aliases):
            # TODO: exception: not all aliases in the command were mapped
            pass

        return invocation["command"]

    def __choose_provider(self, request_body):
        return request_body["providers"][0]

