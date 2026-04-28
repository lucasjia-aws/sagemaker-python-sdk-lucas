import json
from functools import lru_cache

from pydantic import BaseModel

from sagemaker.core.tools.constants import (
    ADDITIONAL_OPERATION_FILE_PATH,
    FEATURE_STORE_SERVICE_JSON_FILE_PATH,
    METRICS_SERVICE_JSON_FILE_PATH,
    SERVICE_JSON_FILE_PATH,
    RUNTIME_SERVICE_JSON_FILE_PATH,
)


class ServiceJsonData(BaseModel):
    sagemaker: dict
    sagemaker_runtime: dict
    sagemaker_feature_store: dict
    sagemaker_metrics: dict


@lru_cache(maxsize=1)
def load_service_jsons() -> ServiceJsonData:
    with open(SERVICE_JSON_FILE_PATH, "r") as file:
        service_json = json.load(file)
    with open(RUNTIME_SERVICE_JSON_FILE_PATH, "r") as file:
        runtime_service_json = json.load(file)
    with open(FEATURE_STORE_SERVICE_JSON_FILE_PATH, "r") as file:
        feature_store_service_json = json.load(file)
    with open(METRICS_SERVICE_JSON_FILE_PATH, "r") as file:
        metrics_service_json = json.load(file)
    return ServiceJsonData(
        sagemaker=service_json,
        sagemaker_runtime=runtime_service_json,
        sagemaker_feature_store=feature_store_service_json,
        sagemaker_metrics=metrics_service_json,
    )


def _filter_internal_only_operations(operations: dict) -> dict:
    """Filter out operations marked as internalonly."""
    return {name: defn for name, defn in operations.items() if not defn.get("internalonly")}


def _filter_internal_only_shapes(shapes: dict) -> dict:
    """Filter out shapes and shape members marked as internalonly."""
    filtered = {}
    for shape_name, shape_def in shapes.items():
        if shape_def.get("internalonly"):
            continue
        if "members" in shape_def:
            filtered_members = {
                member_name: member_def
                for member_name, member_def in shape_def["members"].items()
                if not member_def.get("internalonly")
            }
            shape_def = {**shape_def, "members": filtered_members}
        filtered[shape_name] = shape_def
    return filtered


@lru_cache(maxsize=1)
def load_combined_shapes_data() -> dict:
    service_json_data = load_service_jsons()
    combined = {
        **service_json_data.sagemaker_runtime["shapes"],
        **service_json_data.sagemaker_feature_store["shapes"],
        **service_json_data.sagemaker_metrics["shapes"],
        **service_json_data.sagemaker["shapes"],
    }
    return _filter_internal_only_shapes(combined)


@lru_cache(maxsize=1)
def load_combined_operations_data() -> dict:
    service_json_data = load_service_jsons()
    combined = {
        **service_json_data.sagemaker_runtime["operations"],
        **service_json_data.sagemaker_feature_store["operations"],
        **service_json_data.sagemaker_metrics["operations"],
        **service_json_data.sagemaker["operations"],
    }
    return _filter_internal_only_operations(combined)


@lru_cache(maxsize=1)
def load_additional_operations_data() -> dict:
    with open(ADDITIONAL_OPERATION_FILE_PATH, "r") as file:
        additional_operation_json = json.load(file)
    return additional_operation_json
