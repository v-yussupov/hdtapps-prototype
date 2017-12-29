from pymongo import MongoClient
from flask import current_app
from bson.objectid import ObjectId
from app.mod_repo.models import ApplicationSpecification
from typing import List
from pprint import pprint


def store_app(app_obj: ApplicationSpecification) -> ApplicationSpecification:
    try:
        client = MongoClient(current_app.config["DB_HOST"], current_app.config["DB_PORT"])
        db = client[current_app.config["DB_NAME"]]
        apps_collection = db[current_app.config["APP_COLL_NAME"]]
        trfs_collection = db[current_app.config["TRANSF_COLL_NAME"]]

        for t in app_obj.t_specs:
            t_dict = t.to_dict()
            t_dict.pop('transformationID', None)
            t_id = trfs_collection.insert_one(t_dict).inserted_id
            t.id = str(t_id)

        app_id = apps_collection.insert_one(app_obj.to_dict()).inserted_id

        return app_obj
    except:
        # TODO: add error handling
        raise


def find_app(app_id: str):
    client = MongoClient(current_app.config["DB_HOST"], current_app.config["DB_PORT"])
    db = client[current_app.config["DB_NAME"]]
    apps_collection = db[current_app.config["APP_COLL_NAME"]]

    result = apps_collection.find_one({"appInfo.appID": app_id})

    result.pop('_id', None)
    for t in result["transformations"]:
        t.pop('_id', None)

    return result


def find_apps_by_tags(tags: List[str]):
    client = MongoClient(current_app.config["DB_HOST"], current_app.config["DB_PORT"])
    db = client[current_app.config["DB_NAME"]]
    apps_collection = db[current_app.config["APP_COLL_NAME"]]

    if len(tags) > 0:
        results = list(apps_collection.find({"appInfo.tags": {"$in": tags}}))
    else:
        results = list(apps_collection.find())

    for r in results:
        r.pop('_id', None)
        for t in r["transformations"]:
            t.pop('_id', None)

    return results


def find_app_transformations(app_id: str):
    client = MongoClient(current_app.config["DB_HOST"], current_app.config["DB_PORT"])
    db = client[current_app.config["DB_NAME"]]
    apps_collection = db[current_app.config["APP_COLL_NAME"]]

    result = apps_collection.find_one({"appInfo.appID": app_id})

    for t in result["transformations"]:
        t.pop('_id', None)

    return result["transformations"]


def delete_app(app_id):
    client = MongoClient(current_app.config["DB_HOST"], current_app.config["DB_PORT"])
    db = client[current_app.config["DB_NAME"]]
    apps_collection = db[current_app.config["APP_COLL_NAME"]]
    trfs_collection = db[current_app.config["TRANSF_COLL_NAME"]]

    trfs_collection.delete_many({"appID": app_id})
    apps_collection.delete_one({"appInfo.appID": app_id})

    return True


def find_transformation_by_id(t_id):
    client = MongoClient(current_app.config["DB_HOST"], current_app.config["DB_PORT"])
    db = client[current_app.config["DB_NAME"]]
    trfs_collection = db[current_app.config["TRANSF_COLL_NAME"]]

    result = trfs_collection.find_one({"_id": ObjectId(t_id)})
    id = str(result["_id"])
    result.pop('_id', None)
    result["transformationID"] = id

    return result


def find_transformation_by_qname(qname):
    client = MongoClient(current_app.config["DB_HOST"], current_app.config["DB_PORT"])
    db = client[current_app.config["DB_NAME"]]
    trfs_collection = db[current_app.config["TRANSF_COLL_NAME"]]

    result = trfs_collection.find_one({"qname": qname})
    id = str(result["_id"])
    result.pop('_id', None)
    result["transformationID"] = id

    return result


def find_transformation_by_signature(signature: str, strict=False):
    client = MongoClient(current_app.config["DB_HOST"], current_app.config["DB_PORT"])
    db = client[current_app.config["DB_NAME"]]
    trfs_collection = db[current_app.config["TRANSF_COLL_NAME"]]

    print(signature)

    if strict:
        results = list(trfs_collection.find({"strictSignature": signature}))
    else:
        results = list(trfs_collection.find({"relaxedSignature": signature}))

    for r in results:
        id = str(r["_id"])
        r.pop('_id', None)
        r["transformationID"] = id

    return results