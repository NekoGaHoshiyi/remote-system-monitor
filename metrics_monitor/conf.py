import os

import redis

proj_root_path = os.path.abspath(os.path.dirname(__file__))

# global settings

redis_global_variable = redis.StrictRedis(host='localhost', port=9099, db=2)


def log_setting(file_name, max_byte=10000000):
    return {
        "version": 1,
        "disable_existing_loggers": False,  # this fixes the problem

        "formatters": {
            "brief": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "precise": {
                # "format": "%(asctime)s %(levelname)s %(module)s %(process)d %(thread)d %(message)s"
                "format": "%(asctime)s %(levelname)-8s [pid:%(process)d thread:%(thread)d] [%(filename)s:%(lineno)d] %(message)s"
            },
            "precise1": {
                # "format": "%(asctime)s %(levelname)s %(module)s %(process)d %(thread)d %(message)s"
                "format": "\n%(asctime)s %(levelname)-8s [pid:%(process)d thread:%(thread)d] [%(filename)s:%(lineno)d] %(message)s"
            },
        },

        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "precise"
            },
            "info_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "precise",
                "level": "INFO",
                "filename": "{}/logs/info/{}_info.log".format(proj_root_path, file_name),
                "maxBytes": max_byte,
                "backupCount": 1
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "precise1",
                "level": "ERROR",
                "filename": "{}/logs/error/{}_error.log".format(proj_root_path, file_name),
                # "filename": "{}/logs/error/error.log".format(proj_root_path),
                "maxBytes": max_byte,
                "backupCount": 1
            },
        },

        "loggers": {
            file_name: {
                "handlers": ["info_file", "error_file"],
                "level": "DEBUG",
                "propagate": False
            }
        }
    }


