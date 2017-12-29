import json
import traceback
from itertools import starmap
from typing import List


class ApplicationSpecification:
    def __init__(self, desc_entity, transformations, dependencies, configurations, invocations, test_runs):

        self.app_info = desc_entity         # type: Description
        self.t_specs = transformations      # type: List[Transformation]
        self.dep_specs = dependencies       # type: DependencySpec
        self.config_specs = configurations  # type: List[Configuration]
        self.invocations = invocations  # type: List[InvocationCLI]
        self.test_run_specs = test_runs     # type: List[TestRun]

        for t in self.t_specs:
            t.app_id = self.app_info.id

        self.app_info.transformations_count = len(self.t_specs)
        self.app_info.env_deps_count = len(self.dep_specs.env_deps)
        self.app_info.soft_deps_count = len(self.dep_specs.soft_deps)
        self.app_info.file_deps_count = len(self.dep_specs.file_deps)

        self.app_info.total_deps_count = self.app_info.env_deps_count + self.app_info.soft_deps_count + self.app_info.file_deps_count

    def to_json_str(self):
        return json.dumps(self, cls=ApplicationSpecJsonEncoder)

    def to_dict(self):
        return json.loads(json.dumps(self, cls=ApplicationSpecJsonEncoder))


class Description:
    def __init__(self, app_info):
        if "appName" in app_info:
            if is_not_blank(app_info["appName"]):
                self.name = app_info["appName"]
            else:
                raise EmptyProperty("appInfo.appName")
        else:
            raise PropertyNotSpecified("appInfo.appName")

        if "appDevelopers" in app_info:
            if len(app_info["appDevelopers"]) > 0:
                self.developers = app_info["appDevelopers"]
            else:
                raise EmptyProperty("appInfo.appDevelopers")
        else:
            raise PropertyNotSpecified("appInfo.appDevelopers")

        if "appPublisher"in app_info:
            if is_not_blank(app_info["appPublisher"]):
                self.publisher = app_info["appPublisher"]
            else:
                raise EmptyProperty("appInfo.appPublisher")
        else:
            raise PropertyNotSpecified("appInfo.appPublisher")

        if "appVersion" in app_info:
            if is_not_blank(app_info["appVersion"]):
                self.version = app_info["appVersion"]
            else:
                raise EmptyProperty("appInfo.appVersion")
        else:
            raise PropertyNotSpecified("appInfo.appVersion")

        if "appDesc" in app_info:
            self.desc = app_info["appDesc"]
        else:
            self.desc = ""

        if "appLicense" in app_info:
            self.license = app_info["appLicense"]
        else:
            self.license = ""

        if "tags" in app_info:
            self.tags = app_info["tags"]
        else:
            self.tags = []

        self.id = self.__generate_app_id()
        self.providers = []
        self.is_validated = False
        self.path = ""
        self.transformations_count = 0
        self.total_deps_count = 0
        self.env_deps_count = 0
        self.soft_deps_count = 0
        self.file_deps_count = 0

    def __generate_app_id(self):
        pub = self.publisher.lower().replace(" ", "")
        name = self.name.lower().replace(" ", "")
        ver = self.version.lower().replace(" ", "")
        dev_str = ""
        for dev in self.developers:
            shortened_dev_string = ""
            parts = dev.split()
            for part in parts:
                shortened_dev_string += part[0]
                shortened_dev_string += part[-1]
            dev_str += shortened_dev_string.lower()

        return pub + "_" + dev_str + "_" + name + "_" + ver


class Transformation:
    def __init__(self, t_obj):
        if "name" in t_obj:
            if is_not_blank(t_obj["name"]):
                self.name = t_obj["name"]
            else:
                raise EmptyProperty("transformation.name")
        else:
            raise PropertyNotSpecified("transformation.name")

        if "qname" in t_obj:
            self.qname = t_obj["qname"]
        else:
            self.qname = ""
        self.id = ""
        self.app_id = ""
        self.relaxed_signature = ""
        self.strict_signature = ""
        self.providers = []
        self.i_str_param_count = 0
        self.i_num_param_count = 0
        self.i_opt_param_count = 0
        self.i_params = []  # type: List[InputParameter]
        if "inputParams" in t_obj:
            for p in t_obj["inputParams"]:
                try:
                    input_param = InputParameter(p)
                    self.i_params.append(input_param)
                    if input_param.type == "string" or input_param.type == "string":
                        self.i_str_param_count += 1
                    else:
                        self.i_num_param_count += 1

                    if input_param.is_optional:
                        self.i_opt_param_count += 1
                except EmptyProperty as e:
                    print('EmptyProperty exception:', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception:', er.msg)
        self.i_params_count = len(self.i_params)

        self.i_files = []   # type: List[InputFile]
        if "inputFiles" in t_obj:
            for f in t_obj["inputFiles"]:
                try:
                    input_file = InputFile(f)
                    self.i_files.append(input_file)
                except EmptyProperty as e:
                    print('EmptyProperty exception:', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception:', er.msg)
        self.i_files_count = len(self.i_files)

        self.i_filesets = []    # type: List[InputFileSet]
        if "inputFileSets" in t_obj:
            for f in t_obj["inputFileSets"]:
                try:
                    input_fileset = InputFileSet(f)
                    self.i_filesets.append(input_fileset)
                except EmptyProperty as e:
                    print('EmptyProperty exception:', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception:', er.msg)
        self.i_filesets_count = len(self.i_filesets)

        if self.i_params_count + self.i_files_count + self.i_filesets_count == 0:
            raise EmptyProperty("transformation.inputs")

        self.o_files = []   # type: List[OutputFile]
        if "outputFiles" in t_obj:
            for f in t_obj["outputFiles"]:
                try:
                    output_file = OutputFile(f)
                    self.o_files.append(output_file)
                except EmptyProperty as e:
                    print('EmptyProperty exception:', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception:', er.msg)
        self.o_files_count = len(self.o_files)

        if self.o_files_count == 0:
            raise EmptyProperty("transformation.outputs")

        # Generate transformation's signatures
        self.__generate_signatures()

    def __generate_signatures(self):
        relaxed_signature = ""
        strict_signature = ""

        relaxed_param_number = self.i_params_count - self.i_opt_param_count
        relaxed_param_signature = "[pi:" + str(relaxed_param_number) + "]"
        relaxed_signature += relaxed_param_signature
        strict_signature += "[pi:" + str(self.i_params_count) + "]"

        ifile_formats = {}
        for f in self.i_files:
            if f.format not in ifile_formats:
                ifile_formats[f.format] = {"strict": 0, "relaxed": 0}

            ifile_formats[f.format]["strict"] += 1
            if not f.is_optional:
                ifile_formats[f.format]["relaxed"] += 1
        for f in sorted(ifile_formats):
            strict_signature += "[fi:" + str(ifile_formats[f]["strict"]) + ":" + f + "]"
            relaxed_signature += "[fi:" + str(ifile_formats[f]["relaxed"]) + ":" + f + "]"

        ifilesets_formats = {}
        for fs in self.i_filesets:
            if fs.format not in ifile_formats:
                ifilesets_formats[fs.format] = {"strict": 0, "relaxed": 0}

                ifilesets_formats[fs.format]["strict"] += 1
            if not fs.is_optional:
                ifilesets_formats[fs.format]["relaxed"] += 1
        for fs in ifilesets_formats:
            strict_signature += "[fsi:" + str(ifilesets_formats[fs]["strict"]) + ":" + fs + "]"
            relaxed_signature += "[fsi:" + str(ifilesets_formats[fs]["relaxed"]) + ":" + fs + "]"

        ofiles_formats = {}
        for ofile in self.o_files:
            if ofile.format not in ofiles_formats:
                ofiles_formats[ofile.format] = 0

                ofiles_formats[ofile.format] += 1
        for o in ofiles_formats:
            relaxed_signature += "[fo:" + str(ofiles_formats[o]) + ":" + o + "]"
            strict_signature += "[fo:" + str(ofiles_formats[o]) + ":" + o + "]"

        self.strict_signature = strict_signature
        self.relaxed_signature = relaxed_signature

    @staticmethod
    def generate_signature(pnum: int, infiles: List[str], infilesets: List[str], outfiles: List[str]) -> str:
        signature = "[pi:" + str(pnum) + "]"

        infiles_dict = {}
        for f in infiles:
            if f not in infiles_dict:
                infiles_dict[f] = 0
            infiles_dict[f] += 1
        for prop in infiles_dict:
            signature += "[fi:" + str(infiles_dict[prop]) + ":" + prop + "]"

        infilesets_dict = {}
        for f in infilesets:
            if f not in infilesets_dict:
                infilesets_dict[f] = 0
            infilesets_dict[f] += 1
        for prop in infilesets_dict:
            signature += "[fsi:" + str(infilesets_dict[prop]) + ":" + prop + "]"

        outfiles_dict = {}
        for f in outfiles:
            if f not in outfiles_dict:
                outfiles_dict[f] = 0
            outfiles_dict[f] += 1
        for prop in outfiles_dict:
            signature += "[fo:" + str(outfiles_dict[prop]) + ":" + prop + "]"

        return signature

    def to_json_str(self):
        return json.dumps(self, cls=ApplicationSpecJsonEncoder)

    def to_dict(self):
        return json.loads(json.dumps(self, cls=ApplicationSpecJsonEncoder))


class InputParameter:
    def __init__(self, param):
        if "inputName" in param:
            if is_not_blank(param["inputName"]):
                self.name = param["inputName"]
            else:
                raise EmptyProperty("inputParam.inputName")
        else:
            raise PropertyNotSpecified("inputParam.inputName")

        if "alias" in param:
            if is_not_blank(param["alias"]):
                self.alias = param["alias"]
            else:
                raise EmptyProperty("inputParam.alias")
        else:
            raise PropertyNotSpecified("inputParam.alias")

        if "type" in param:
            if is_not_blank(param["type"]):
                self.type = param["type"]
            else:
                raise EmptyProperty("inputParam.type")
        else:
            raise PropertyNotSpecified("inputParam.type")

        if "isOptional" in param:
            self.is_optional = param["isOptional"]
        else:
            self.is_optional = True

        if "value" in param:
            self.value = param["value"]
        else:
            self.value = ""


class InputFile:
    def __init__(self, file):
        if "inputName" in file:
            if is_not_blank(file["inputName"]):
                self.name = file["inputName"]
            else:
                raise EmptyProperty("inputFile.inputName")
        else:
            raise PropertyNotSpecified("inputFile.inputName")

        if "alias" in file:
            if is_not_blank(file["alias"]):
                self.alias = file["alias"]
            else:
                raise EmptyProperty("inputFile.alias")
        else:
            raise PropertyNotSpecified("inputFile.alias")

        if "format" in file:
            if is_not_blank(file["format"]):
                self.format = file["format"]
            else:
                raise EmptyProperty("inputFile.format")
        else:
            raise PropertyNotSpecified("inputFile.format")

        if "isOptional" in file:
            self.is_optional = file["isOptional"]
        else:
            self.is_optional = True

        if "schema" in file:
            self.schema = file["schema"]
        else:
            self.schema = ""

        if "requiredPath" in file:
            self.req_path = file["requiredPath"]
        else:
            self.req_path = ""


class InputFileSet:
    def __init__(self, fileset):
        if "inputName" in fileset:
            if is_not_blank(fileset["inputName"]):
                self.name = fileset["inputName"]
            else:
                raise EmptyProperty("inputFileSet.inputName")
        else:
            raise PropertyNotSpecified("inputFileSet.inputName")

        if "alias" in fileset:
            if is_not_blank(fileset["alias"]):
                self.alias = fileset["alias"]
            else:
                raise EmptyProperty("inputFileSet.alias")
        else:
            raise PropertyNotSpecified("inputFileSet.alias")

        if "format" in fileset:
            if is_not_blank(fileset["format"]):
                self.format = fileset["format"]
            else:
                raise EmptyProperty("inputFileSet.format")
        else:
            raise PropertyNotSpecified("inputFileSet.format")

        if "requiredPath" in fileset:
            if is_not_blank(fileset["requiredPath"]):
                self.req_path = fileset["requiredPath"]
            else:
                raise EmptyProperty("inputFileSet.requiredPath")
        else:
            raise PropertyNotSpecified("inputFileSet.requiredPath")

        if "isOptional" in fileset:
            self.is_optional = fileset["isOptional"]
        else:
            self.is_optional = True

        if "schema" in fileset:
            self.schema = fileset["schema"]
        else:
            self.schema = ""

        if "fileSetSize" in fileset:
            self.size = fileset["fileSetSize"]
        else:
            self.size = -1


class OutputFile:
    def __init__(self, file):
        if "outputName" in file:
            if is_not_blank(file["outputName"]):
                self.name = file["outputName"]
            else:
                raise EmptyProperty("outputFile.outputName")
        else:
            raise PropertyNotSpecified("outputFile.outputName")

        if "alias" in file:
            if is_not_blank(file["alias"]):
                self.alias = file["alias"]
            else:
                raise EmptyProperty("outputFile.alias")
        else:
            raise PropertyNotSpecified("outputFile.alias")

        if "format" in file:
            if is_not_blank(file["format"]):
                self.format = file["format"]
            else:
                raise EmptyProperty("outputFile.format")
        else:
            raise PropertyNotSpecified("outputFile.format")

        if "accessPath" in file:
            if is_not_blank(file["accessPath"]):
                self.access_path = file["accessPath"]
            else:
                raise EmptyProperty("outputFile.accessPath")
        else:
            raise PropertyNotSpecified("outputFile.accessPath")

        if "schema"in file:
            self.schema = file["schema"]
        else:
            self.schema = ""


class DependencySpec:
    def __init__(self, dep_obj):
        self.env_deps = []      # type: List[EnvironmentDependency]
        if "envDeps" in dep_obj:
            for ed in dep_obj["envDeps"]:
                try:
                    env_dep = EnvironmentDependency(ed)
                    self.env_deps.append(env_dep)
                except EmptyProperty as e:
                    print('EmptyProperty exception:', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception:', er.msg)

        self.soft_deps = []     # type: List[SoftwareDependency]
        if "softDeps" in dep_obj:
            for sd in dep_obj["softDeps"]:
                try:
                    soft_dep = SoftwareDependency(sd)
                    self.soft_deps.append(soft_dep)
                except EmptyProperty as e:
                    print('EmptyProperty exception:', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception:', er.msg)

        self.file_deps = []     # type: List[FileDependency]
        if "fileDeps" in dep_obj:
            for fd in dep_obj["fileDeps"]:
                try:
                    file_dep = FileDependency(fd)
                    self.file_deps.append(file_dep)
                except EmptyProperty as e:
                    print('EmptyProperty exception: ', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception: ', er.msg)


class EnvironmentDependency:
    def __init__(self, env_dep_obj):
        if "depName" in env_dep_obj:
            if is_not_blank(env_dep_obj["depName"]):
                self.name = env_dep_obj["depName"]
            else:
                raise EmptyProperty("envDep.depName")
        else:
            raise PropertyNotSpecified("envDep.depName")

        if "alias" in env_dep_obj:
            if is_not_blank(env_dep_obj["alias"]):
                self.alias = env_dep_obj["alias"]
            else:
                raise EmptyProperty("envDep.alias")
        else:
            raise PropertyNotSpecified("envDep.alias")

        if "value" in env_dep_obj:
            if is_not_blank(env_dep_obj["value"]):
                self.value = env_dep_obj["value"]
            else:
                raise EmptyProperty("envDep.value")
        else:
            raise PropertyNotSpecified("envDep.value")

        if "depDesc" in env_dep_obj:
            self.desc = env_dep_obj["depDesc"]
        else:
            self.desc = ""


class SoftwareDependency:
    def __init__(self, soft_dep_obj):
        if "depName" in soft_dep_obj:
            if is_not_blank(soft_dep_obj["depName"]):
                self.name = soft_dep_obj["depName"]
            else:
                raise EmptyProperty("softDep.depName")
        else:
            raise PropertyNotSpecified("softDep.depName")

        if "alias" in soft_dep_obj:
            if is_not_blank(soft_dep_obj["alias"]):
                self.alias = soft_dep_obj["alias"]
            else:
                raise EmptyProperty("softDep.alias")
        else:
            raise PropertyNotSpecified("softDep.alias")

        if "commands" in soft_dep_obj:
            if len(soft_dep_obj["commands"]) > 0:
                self.commands = soft_dep_obj["commands"]
            else:
                raise EmptyProperty("softDep.commands")
        else:
            raise PropertyNotSpecified("softDep.commands")

        if "depDesc" in soft_dep_obj:
            self.desc = soft_dep_obj["depDesc"]
        else:
            self.desc = ""

        if "depVersion" in soft_dep_obj:
            self.version = soft_dep_obj["depVersion"]
        else:
            self.version = ""

        if "depPath" in soft_dep_obj:
            self.path = soft_dep_obj["depPath"]
        else:
            self.path = ""


class FileDependency:
    def __init__(self, file_dep_obj):
        if "depName" in file_dep_obj:
            if is_not_blank(file_dep_obj["depName"]):
                self.name = file_dep_obj["depName"]
            else:
                raise EmptyProperty("fileDep.depName")
        else:
            raise PropertyNotSpecified("fileDep.depName")

        if "alias" in file_dep_obj:
            if is_not_blank(file_dep_obj["alias"]):
                self.alias = file_dep_obj["alias"]
            else:
                raise EmptyProperty("fileDep.alias")
        else:
            raise PropertyNotSpecified("fileDep.alias")

        if "filePath" in file_dep_obj:
            if is_not_blank(file_dep_obj["filePath"]):
                self.path = file_dep_obj["filePath"]
            else:
                raise EmptyProperty("fileDep.filePath")
        else:
            raise PropertyNotSpecified("fileDep.filePath")

        if "depDesc" in file_dep_obj:
            self.desc = file_dep_obj["depDesc"]
        else:
            self.desc = ""


class Configuration:
    def __init__(self, conf_obj):
        if "confName" in conf_obj:
            self.name = conf_obj["confName"]
        else:
            self.name = ""

        if "commands" in conf_obj:
            self.commands = conf_obj["commands"]
        else:
            self.commands = []

        if len(self.commands) == 0:
            raise EmptyProperty("config.commands")


class InvocationCLI:
    def __init__(self, inv_obj):
        if "invName" in inv_obj:
            if is_not_blank(inv_obj["invName"]):
                self.name = inv_obj["invName"]
            else:
                raise EmptyProperty("invocation.invName")
        else:
            raise PropertyNotSpecified("invocation.invName")

        if "command" in inv_obj:
            if is_not_blank(inv_obj["command"]):
                self.command = inv_obj["command"]
            else:
                raise EmptyProperty("invocation.command")
        else:
            raise PropertyNotSpecified("invocation.command")

        if "invDesc" in inv_obj:
            self.desc = inv_obj["invDesc"]
        else:
            self.desc = ""


class TestRun:
    def __init__(self, testrun_obj):
        if "name" in testrun_obj:
            if is_not_blank(testrun_obj["name"]):
                self.name = testrun_obj["name"]
            else:
                raise EmptyProperty("testrun.name")
        else:
            raise PropertyNotSpecified("testrun.name")

        if "transformation" in testrun_obj:
            if is_not_blank(testrun_obj["transformation"]):
                self.transformation_name = testrun_obj["transformation"]
            else:
                raise EmptyProperty("testrun.transformation")
        else:
            raise PropertyNotSpecified("testrun.transformation")

        self.sample_input_params = []
        if "sampleInputParams" in testrun_obj:
            for sip in testrun_obj["sampleInputParams"]:
                try:
                    sample_input_param = SampleInputParameter(sip)
                    self.sample_input_params.append(sample_input_param)
                except EmptyProperty as e:
                    print('EmptyProperty exception: ', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception: ', er.msg)

        self.sample_input_files = []
        if "sampleInputFiles" in testrun_obj:
            for sif in testrun_obj["sampleInputFiles"]:
                try:
                    sample_input_file = SampleInputFile(sif)
                    self.sample_input_files.append(sample_input_file)
                except EmptyProperty as e:
                    print('EmptyProperty exception: ', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception: ', er.msg)

        self.sample_input_filesets = []
        if "sampleInputFileSets" in testrun_obj:
            for sample_ifs in testrun_obj["sampleInputFileSets"]:
                try:
                    sample_input_fileset = SampleInputFileSet(sample_ifs)
                    self.sample_input_filesets.append(sample_input_fileset)
                except EmptyProperty as e:
                    print('EmptyProperty exception: ', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception: ', er.msg)

        if len(self.sample_input_params) + len(self.sample_input_files) + len(self.sample_input_filesets) == 0:
            raise EmptyProperty("testrun.inputs")

        self.sample_output_files = []
        if "resultingOutputFiles" in testrun_obj:
            for sample_of in testrun_obj["resultingOutputFiles"]:
                try:
                    sample_output_file = SampleOutputFile(sample_of)
                    self.sample_output_files.append(sample_output_file)
                except EmptyProperty as e:
                    print('EmptyProperty exception: ', e.msg)
                except PropertyNotSpecified as er:
                    print('PropertyNotSpecified exception: ', er.msg)

        if len(self.sample_output_files) == 0:
            raise EmptyProperty("testrun.outputs")

        if "description" in testrun_obj:
            self.desc = testrun_obj["description"]
        else:
            self.desc = ""


class SampleInputParameter:
    def __init__(self, param):
        if "alias" in param:
            if is_not_blank(param["alias"]):
                self.alias = param["alias"]
            else:
                raise EmptyProperty("sampleInputParam.alias")
        else:
            raise PropertyNotSpecified("sampleInputParam.alias")

        if "value" in param:
            if is_not_blank(param["value"]):
                self.value = param["value"]
            else:
                raise EmptyProperty("sampleInputParam.value")
        else:
            raise PropertyNotSpecified("sampleInputParam.value")


class SampleInputFile:
    def __init__(self, file):
        if "alias" in file:
            if is_not_blank(file["alias"]):
                self.alias = file["alias"]
            else:
                raise EmptyProperty("sampleInputFile.alias")
        else:
            raise PropertyNotSpecified("sampleInputFile.alias")

        if "accessPath" in file:
            if is_not_blank(file["accessPath"]):
                self.access_path = file["accessPath"]
            else:
                raise EmptyProperty("sampleInputFile.accessPath")
        else:
            raise PropertyNotSpecified("sampleInputFile.accessPath")


class SampleInputFileSet:
    def __init__(self, fileset):
        if "alias" in fileset:
            if is_not_blank(fileset["alias"]):
                self.alias = fileset["alias"]
            else:
                raise EmptyProperty("sampleInputFileSet.alias")
        else:
            raise PropertyNotSpecified("sampleInputFileSet.alias")

        if "accessPath" in fileset:
            if is_not_blank(fileset["accessPath"]):
                self.access_path = fileset["accessPath"]
            else:
                raise EmptyProperty("sampleInputFileSet.accessPath")
        else:
            raise PropertyNotSpecified("sampleInputFileSet.accessPath")


class SampleOutputFile:
    def __init__(self, file):
        if "alias" in file:
            if is_not_blank(file["alias"]):
                self.alias = file["alias"]
            else:
                raise EmptyProperty("sampleOutputFile.alias")
        else:
            raise PropertyNotSpecified("sampleOutputFile.alias")

        if "outputPath" in file:
            if is_not_blank(file["outputPath"]):
                self.output_path = file["outputPath"]
            else:
                raise EmptyProperty("sampleOutputFile.outputPath")
        else:
            raise PropertyNotSpecified("sampleOutputFile.outputPath")


class Error(Exception):
    # Error is derived class for Exception, but
    # Base class for exceptions in this module
    pass


class EmptyProperty(Error):
    """Raised when the property is not provided in the package specification"""
    def __init__(self, prop):
        self.prop_name = prop
        # Error message thrown is saved in msg
        self.msg = "Error when creating property " + prop + ", the value cannot be empty"


class PropertyNotSpecified(Error):
    """Raised when the property is not provided in the package specification"""
    def __init__(self, prop):
        self.prop_name = prop
        # Error message thrown is saved in msg
        self.msg = "Property " + prop + " is missing"


def dict_to_app_pkg_spec_object(json_dict) -> ApplicationSpecification:
    try:
        desc_entity = None
        if "appInfo" in json_dict:
            desc_entity = Description(json_dict["appInfo"])

        transformations = []
        if "transformations" in json_dict:
            for t in json_dict["transformations"]:
                transformation = Transformation(t)
                transformations.append(transformation)
        dep_spec = None
        if "dependencies" in json_dict:
            dep_spec = DependencySpec(json_dict["dependencies"])

        configurations = []
        if "configs" in json_dict:
            for c in json_dict["configs"]:
                config = Configuration(c)
                configurations.append(config)

        invocations = []
        if "invocations" in json_dict and "invocationsCLI" in json_dict["invocations"]:
            for i in json_dict["invocations"]["invocationsCLI"]:
                invocation = InvocationCLI(i)
                invocations.append(invocation)

        testruns = []
        if "testRuns" in json_dict:
            for tr in json_dict["testRuns"]:
                testrun = TestRun(tr)
                testruns.append(testrun)

        result = ApplicationSpecification(
            desc_entity,
            transformations,
            dep_spec,
            configurations,
            invocations,
            testruns
        )

        return result

    except EmptyProperty as e:
        print('EmptyProperty exception:', e.msg)
    except PropertyNotSpecified as er:
        print('PropertyNotSpecified exception:', er.msg)
    except Exception:
        print(traceback.format_exc())


def is_not_blank(str_arg):
    return bool(str_arg and str_arg.strip())


class ApplicationSpecJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ApplicationSpecification):
            return {
                "appInfo": o.app_info,
                "transformations": o.t_specs,
                "dependencies": o.dep_specs,
                "configs": o.config_specs,
                "invocations": o.invocations,
                "testRuns": o.test_run_specs
            }

        if isinstance(o, Description):
            return {
                "appID": o.id,
                "appName": o.name,
                "appVersion": o.version,
                "appPublisher": o.publisher,
                "appDesc": o.desc,
                "appDevelopers": o.developers,
                "appLicense": o.license,
                "tags": o.tags,
                "providers": o.providers,
                "isValidated": o.is_validated,
                "path": o.path,
                "transformationsCount": o.transformations_count,
                "totalDepsCount": o.total_deps_count,
                "envDepsCount": o.env_deps_count,
                "softDepsCount": o.soft_deps_count,
                "fileDepsCount": o.file_deps_count
            }

        if isinstance(o, InputParameter):
            return {
                "inputName": o.name,
                "alias": o.alias,
                "isOptional": o.is_optional,
                "value": o.value,
                "type": o.type
            }

        if isinstance(o, InputFile):
            return {
                "inputName": o.name,
                "alias": o.alias,
                "isOptional": o.is_optional,
                "format": o.format,
                "schema": o.schema,
                "requiredPath": o.req_path
            }

        if isinstance(o, InputFileSet):
            return {
                "inputName": o.name,
                "alias": o.alias,
                "isOptional": o.is_optional,
                "format": o.format,
                "schema": o.schema,
                "requiredPath": o.req_path,
                "fileSetSize": o.size
            }

        if isinstance(o, OutputFile):
            return {
                "outputName": o.name,
                "alias": o.alias,
                "format": o.format,
                "schema": o.schema,
                "accessPath": o.access_path
            }

        if isinstance(o, Transformation):
            return {
                "transformationID": o.id,
                "appID": o.app_id,
                "name": o.name,
                "qname": o.qname,
                "strictSignature": o.strict_signature,
                "relaxedSignature": o.relaxed_signature,
                "providers": o.providers,
                "inputParams": o.i_params,
                "inputFiles": o.i_files,
                "inputFileSets": o.i_filesets,
                "outputFiles": o.o_files,
                "inputParamCount": o.i_params_count,
                "inputStrParamCount": o.i_str_param_count,
                "inputNumParamCount": o.i_num_param_count,
                "inputOptParamCount": o.i_opt_param_count,
                "inputFilesCount": o.i_files_count,
                "inputFileSetsCount": o.i_filesets_count,
                "outputFilesCount": o.o_files_count
            }

        if isinstance(o, DependencySpec):
            return {
                "envDeps": o.env_deps,
                "softDeps": o.soft_deps,
                "fileDeps": o.file_deps
            }

        if isinstance(o, EnvironmentDependency):
            return {
                "depName": o.name,
                "alias": o.alias,
                "depDesc": o.desc,
                "value": o.value
            }

        if isinstance(o, SoftwareDependency):
            return {
                "depName": o.name,
                "alias": o.alias,
                "depDesc": o.desc,
                "depVersion": o.version,
                "depPath": o.path,
                "commands": o.commands
            }

        if isinstance(o, FileDependency):
            return {
                "depName": o.name,
                "alias": o.alias,
                "depDesc": o.desc,
                "filePath": o.path
            }

        if isinstance(o, Configuration):
            return {
                "confName": o.name,
                "commands": o.commands
            }

        if isinstance(o, InvocationCLI):
            return {
                "invName": o.name,
                "invDesc": o.desc,
                "command": o.command
            }

        if isinstance(o, TestRun):
            return {
                "name": o.name,
                "description": o.desc,
                "transformation": o.transformation_name,
                "sampleInputParams": o.sample_input_params,
                "sampleInputFiles": o.sample_input_files,
                "sampleInputFileSets": o.sample_input_filesets,
                "resultingOutputFiles": o.sample_output_files
            }

        if isinstance(o, SampleInputParameter):
            return {
                "alias": o.alias,
                "value": o.value
            }

        if isinstance(o, SampleInputFile):
            return {
                "alias": o.alias,
                "accessPath": o.access_path
            }

        if isinstance(o, SampleInputFileSet):
            return {
                "alias": o.alias,
                "accessPath": o.access_path
            }

        if isinstance(o, SampleOutputFile):
            return {
                "alias": o.alias,
                "outputPath": o.output_path
            }

        else:
            raise TypeError("Type not serializable")

