import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    DB_HOST = 'localhost'
    DB_PORT = 27017
    DB_NAME = 'hdtapps'
    APP_COLL_NAME = 'applications'
    TRANSF_COLL_NAME = 'transformations'
    DOCKER_IMAGES_TAG_PREFIX = 'hdtapps/'


    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    pass


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
