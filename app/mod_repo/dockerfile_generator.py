import os
from app.mod_repo.models import ApplicationSpecification, EnvironmentDependency, SoftwareDependency
from typing import List


def write_instructions_to_dockerfile(data, file):
    if isinstance(data, str):
        file.write("%s\n" % data)
    elif isinstance(data, list):
        for item in data:
            file.write("%s\n" % item)
    else:
        # data type is not supported
        pass


class Dockerfile:
    def __init__(self, pkg_spec: ApplicationSpecification):

        self.os_instruction = self.__generate_os()
        self.maintainer_instruction = self.__generate_maintainer(pkg_spec.app_info.publisher)
        self.app_env_vars_instructions = self.__app_folder_env_vars()
        self.app_data_copy_instructions = self.__copy_app_files_instructions()
        self.env_dep_instructions = self.__generate_env_deps(pkg_spec.dep_specs.env_deps)
        self.soft_dep_instructions = self.__generate_soft_deps(pkg_spec.dep_specs.soft_deps)
        self.default_cmd_instructions = self.__generate_default_cmd()

    def __generate_os(self):
        return "FROM ubuntu:14.04"

    def __generate_maintainer(self, publisher_name):
        return 'LABEL maintainer="' + publisher_name + '"'

    def __app_folder_env_vars(self):
        return [
            "\n#Application Package Environment Variables",
            "ENV APPHOME /app",
            "ENV DEPHOME /dep",
            "ENV SCHEMAS /schemas",
            "ENV TESTRUNS /testruns",
            "ENV INPUT /input"
        ]

    def __copy_app_files_instructions(self):
        return [
            "\n#Copy application files",
            "COPY app ${APPHOME}",
            "WORKDIR ${APPHOME}",
            "RUN chmod -R a+x *"
        ]

    def __generate_env_deps(self, env_dependencies: List[EnvironmentDependency]):
        results = []
        for dep in env_dependencies:
            results.append("#EnvDep: " + dep.name)
            results.append("ENV " + dep.name + " " + dep.value)
        return results

    def __generate_soft_deps(self, soft_dependencies: List[SoftwareDependency]):
        results = ["\n#Software dependencies"]
        for dep in soft_dependencies:
            results.append("#SoftDep: " + dep.name)
            if dep.path:
                pass
            cmd_string = "RUN "
            for cmd in dep.commands[:-1]:
                cmd_string += cmd
                cmd_string += ";"
            cmd_string += dep.commands[-1]
            results.append(cmd_string)
        return results

    def __generate_default_cmd(self):
        results = [
            "\n#Set workdir and default cmd",
            "WORKDIR ${APPHOME}",
            "CMD [\"/sbin/init\"]"
        ]
        return results

    def save(self, path: str):
        try:
            dockerfile_path = os.path.join(path, "Dockerfile")
            with open(dockerfile_path, 'w') as dockerfile:
                write_instructions_to_dockerfile(self.os_instruction, dockerfile)
                write_instructions_to_dockerfile(self.maintainer_instruction, dockerfile)
                write_instructions_to_dockerfile(self.app_env_vars_instructions, dockerfile)
                write_instructions_to_dockerfile(self.app_data_copy_instructions, dockerfile)
                write_instructions_to_dockerfile(self.env_dep_instructions, dockerfile)
                write_instructions_to_dockerfile(self.soft_dep_instructions, dockerfile)
                write_instructions_to_dockerfile(self.default_cmd_instructions, dockerfile)
        except Exception as e:
            # TODO: exception handling
            print("error while saving dockerfile", e)
            pass
