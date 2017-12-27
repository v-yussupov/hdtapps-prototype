import docker
from flask import current_app


def deploy_app(dockerfile_path, tag, provider=None):
    try:
        client = docker.from_env()
        image = client.images.build(path=dockerfile_path, tag=tag, rm=True)
        if provider is None:
            p = "default"
        else:
            p = provider

        return {"providerQName": p, "pkgID": image.id}

    except Exception as e:
        # TODO: handle exception
        return {"error": e}


def generate_image_tag(app_name, app_version):
    return current_app.config["DOCKER_IMAGES_TAG_PREFIX"] + app_name.lower() + ":" + app_version.lower()
