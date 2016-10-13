import yaml
import json
import logging
from jsonschema import validate as schema_validate

logger = logging.getLogger(__name__)


def deserialize_me(s):
    try:
        return json.loads(s)
    except Exception as e:
        logger.debug("Tried to deserialize as JSON: {}".format(e))
        pass

    try:
        return yaml.load(s)
    except Exception as e:
        logger.debug("Tried to deserialize as YAML: {}".format(e))
        pass

    raise ValueError("Cannot deserialize string")


def validate_me(obj, validation_file):
    with open(validation_file, "r") as fp:
        return schema_validate(obj, json.load(fp))
