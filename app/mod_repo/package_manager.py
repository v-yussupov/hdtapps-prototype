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



def generate_app_id(publisher, app_name, devs, version):
    pub = publisher.lower().replace(" ", "")
    name = app_name.lower().replace(" ", "")
    ver = version.lower().replace(" ", "")
    dev_str = ""
    for dev in devs:
        shortened_dev_string = ""
        parts = dev.split()
        for part in parts:
            shortened_dev_string += part[0]
            shortened_dev_string += part[-1]
        dev_str += shortened_dev_string.lower()

    return pub + "_" + dev_str + "_" + name + "_" + ver


def populate_application_model(temp_app_dir):
    data = read_package_specification(temp_app_dir)
    app = {
        "appInfo": None,
        "transformations": None,
        "dependencies": None,
        "configurations": None,
        "invocations": None,
        "testRuns": None
    }

    app["appInfo"] = populate_app_info(data)
    app["transformations"] = populate_transformations(data, app["appInfo"]["appID"])
    app["dependencies"] = populate_dependencies(data)
    app["invocations"] = populate_invocations(data)

    #app.configurations = populate_configurations(data)
    #app.test_runs = populate_testruns(data)

    return app


def populate_app_info(pkg_spec):
    app_info = {}
    app_info["appID"] = generate_app_id(
        pkg_spec["appInfo"]["appPublisher"],
        pkg_spec["appInfo"]["appName"],
        pkg_spec["appInfo"]["appDevelopers"],
        pkg_spec["appInfo"]["appVersion"]
    )
    app_info["appName"] = pkg_spec["appInfo"]["appName"]
    app_info["appDesc"] = pkg_spec["appInfo"]["appDesc"]
    app_info["appDevelopers"] = pkg_spec["appInfo"]["appDevelopers"]
    app_info["appLicense"] = pkg_spec["appInfo"]["appLicense"]
    app_info["appPublisher"] = pkg_spec["appInfo"]["appPublisher"]
    app_info["appVersion"] = pkg_spec["appInfo"]["appVersion"]
    app_info["tags"] = pkg_spec["appInfo"]["tags"]

    if "dependencies" in pkg_spec and "envDeps" in pkg_spec["dependencies"]:
        app_info["envDepsCount"] = len(pkg_spec["dependencies"]["envDeps"])
    else:
        app_info["envDepsCount"] = 0

    if "dependencies" in pkg_spec and "fileDeps" in pkg_spec["dependencies"]:
        app_info["fileDepsCount"] = len(pkg_spec["dependencies"]["fileDeps"])
    else:
        app_info["fileDepsCount"] = 0

    if "dependencies" in pkg_spec and "softDeps" in pkg_spec["dependencies"]:
        app_info["softDeps"] = len(pkg_spec["dependencies"]["softDeps"])
    else:
        app_info["softDeps"] = 0

    if "transformations" in pkg_spec:
        app_info["transformationsCount"] = len(pkg_spec["transformations"])
    else:
        # exception!
        app_info["transformationsCount"] = 0

    app_info["validated"] = False
    app_info["path"] = ""
    app_info["providers"] = []

    return app_info


def populate_transformations(pkg_spec, app_id):
    transformations = []
    for t in pkg_spec["transformations"]:
        transform = {}
        transform["name"] = t["name"]
        transform["qname"] = t["qname"]
        transform["appID"] = app_id

        transform["providers"] = []
        transform["inputParams"] = []

        strict_signature = ""
        relaxed_signature = ""

        if "inputParams" in t:
            input_num = 0
            input_str = 0
            optional_count = 0
            input_total = 0
            for p in t["inputParams"]:
                param = {}
                param["name"] = p["inputName"]
                param["alias"] = p["alias"]
                if "isOptional" in p and p["isOptional"] is False:
                    param["isOptional"] = False
                else:
                    param["isOptional"] = True
                    optional_count += 1
                if "value" in p:
                    param["value"] = p["value"]
                else:
                    param["value"] = None

                param["type"] = p["type"]

                if p["type"] == "string":
                    input_str += 1
                else:
                    input_num += 1
                input_total += 1
                transform["inputParams"].append(param)
            if input_total > 0:
                strict_signature += "p:" + str(input_total)
            if input_total - optional_count > 0:
                relaxed_signature += "p:" + str(input_total - optional_count)

            transform["inputNumericParamCount"] = input_num
            transform["inputStringParamCount"] = input_str
            transform["inputTotalParamCount"] = input_total
        else:
            transform["inputNumericParamCount"] = 0
            transform["inputStringParamCount"] = 0
            transform["inputTotalParamCount"] = 0


        transform["inputFiles"] = []
        if "inputFiles" in t:
            file_formats = []
            for fs in t["inputFiles"]:
                i_fileset = {}
                i_fileset["name"] = fs["inputName"]
                i_fileset["alias"] = fs["alias"]
                if "isOptional" in fs:
                    i_fileset["isOptional"] = fs["isOptional"]
                else:
                    i_fileset["isOptional"] = True
                i_fileset["format"] = fs["format"]
                file_formats.append(fs["format"])
                if "schema" in fs:
                    i_fileset["schemaPath"] = fs["schemaPath"]
                else:
                    i_fileset["schemaPath"] = ""

                if "requiredPath" in fs:
                    i_fileset["requiredPath"] = fs["requiredPath"]
                else:
                    i_fileset["requiredPath"] = ""
                    transform["inputFiles"].append(i_fileset)
            transform["inputFileCount"] = len(t["inputFiles"])
            file_formats.sort()
            format_str = "_fi:"
            for item in list(set(file_formats)):
                format_str += item
            strict_signature += format_str
            relaxed_signature += format_str
        else:
            transform["inputFileCount"] = 0

        transform["inputFileSets"] = []
        if "inputFileSets" in t:
            file_formats = []
            for fs in t["inputFileSets"]:
                i_fileset = {}
                i_fileset["name"] = fs["inputName"]
                i_fileset["alias"] = fs["alias"]
                if "isOptional" in fs:
                    i_fileset["isOptional"] = fs["isOptional"]
                else:
                    i_fileset["isOptional"] = True
                i_fileset["format"] = fs["format"]
                file_formats.append(fs["format"])
                if "schema" in fs:
                    i_fileset["schemaPath"] = fs["schemaPath"]
                else:
                    i_fileset["schemaPath"] = ""

                if "requiredPath" in fs:
                    i_fileset["requiredPath"] = fs["requiredPath"]
                else:
                    i_fileset["requiredPath"] = ""

                if "fileSetSize" in fs:
                    i_fileset["fileSetSize"] = fs["fileSetSize"]
                else:
                    i_fileset["fileSetSize"] = 0

                transform["inputFileSets"].append(i_fileset)

            transform["inputFileSetCount"] = len(t["inputFileSets"])

            file_formats.sort()
            format_str = "_fsi:"
            for item in list(set(file_formats)):
                format_str += item
            strict_signature += format_str
            relaxed_signature += format_str

        else:
            transform["inputFileSetCount"] = 0

        transform["outputFiles"] = []
        if "outputFiles" in t:
            file_formats = []
            for o in t["outputFiles"]:
                o_file = {}
                o_file["name"] = o["outputName"]
                o_file["alias"] = o["alias"]
                o_file["format"] = o["format"]
                file_formats.append(o["format"])
                if "schemaPath" in o:
                    o_file["schemaPath"] = o["schemaPath"]
                else:
                    o_file["schemaPath"] = ""
                if "accessPath" in o:
                    o_file["accessPath"] = o["accessPath"]
                else:
                    o_file["accessPath"] = ""

                transform["outputFiles"].append(o_file)

            transform["outputFileCount"] = len(t["outputFiles"])

            file_formats.sort()
            format_str = "_fo:"
            for item in list(set(file_formats)):
                format_str += item
            strict_signature += format_str
            relaxed_signature += format_str

        else:
            # exception: no output specified!
            transform["outputFileCount"] = 0
            pass

        transform["strictSignature"] = strict_signature
        transform["relaxedSignature"] = relaxed_signature
        transform["strictMIMESignature"] = ""
        transform["relaxedMIMESignature"] = ""

        transformations.append(transform)


    return transformations


def populate_dependencies(pkg_spec):
    deps = {
        "envDeps": [],
        "softDeps": [],
        "fileDeps": []
    }
    if "dependencies" in pkg_spec:
        if "envDeps" in pkg_spec["dependencies"]:
            for e in pkg_spec["dependencies"]["envDeps"]:
                env = {}
                env["name"] = e["depName"]
                env["alias"] = e["alias"]
                env["desc"] = e["depDesc"]
                env["value"] = e["value"]
                deps["envDeps"].append(env)


        if "softDeps" in pkg_spec["dependencies"]:
            for s in pkg_spec["dependencies"]["softDeps"]:
                sw = {}
                sw["name"] = s["depName"]
                sw["alias"] = s["alias"]
                sw["desc"] = s["depDesc"]
                sw["version"] = s["depVersion"]
                if "depPath" in s:
                    sw["path"] = s["depPath"]
                else:
                    sw["path"] = ""
                sw["commands"] = s["commands"]
                deps["softDeps"].append(sw)

        if "fileDeps" in pkg_spec["dependencies"]:
            for s in pkg_spec["dependencies"]["fileDeps"]:
                fd = {}
                fd["name"] = s["depName"]
                fd["alias"] = s["alias"]
                fd["desc"] = s["depDesc"]
                if "filePath" in s:
                    fd["path"] = s["filePath"]
                else:
                    fd["path"] = ""
                deps["fileDeps"].append(fd)

    return deps


def populate_invocations(pkg_spec):
    invocations = []
    if "invocations" in pkg_spec and "invocationsCLI" in pkg_spec["invocations"]:
        for i in pkg_spec["invocations"]["invocationsCLI"]:
            inv = {}
            inv["name"] = i["invName"]
            inv["description"] = i["invDesc"]
            inv["command"] = i["command"]
            invocations.append(inv)
    else:
        # exception!
        pass

    return invocations