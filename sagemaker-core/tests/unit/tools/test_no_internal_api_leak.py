"""
Validation test to prevent internal-only APIs from leaking into the public SDK.

This test reads service-2.json to identify items marked as "internalonly",
then verifies that none of them appear in the generated resources.py.
This works regardless of whether the service-2.json is the public or internal version.

See: P422086537
"""

import json
import os
import re

import pytest

from sagemaker.core.tools.constants import SERVICE_JSON_FILE_PATH


@pytest.mark.skipif(
    not os.path.exists(SERVICE_JSON_FILE_PATH),
    reason="service-2.json not found - this test requires source files",
)
class TestNoInternalAPILeak:
    @pytest.fixture(autouse=True)
    def setup(self):
        with open(SERVICE_JSON_FILE_PATH, "r") as f:
            self.service_json = json.load(f)

        # Get the source of resources.py as a string for inspection
        from sagemaker.core import resources

        self.resources_module = resources
        self.resources_source_path = os.path.abspath(resources.__file__)
        with open(self.resources_source_path, "r") as f:
            self.resources_source = f.read()

    def test_internal_operations_not_in_resources(self):
        """Ensure operations marked internalonly in service-2.json are not generated into resources.py."""
        internal_ops = [
            name
            for name, defn in self.service_json.get("operations", {}).items()
            if defn.get("internalonly")
        ]

        if not internal_ops:
            return  # public service-2.json has no internal ops, nothing to check

        # Convert operation names to snake_case method calls
        leaked = []
        for op in internal_ops:
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", op).lower()
            if snake in self.resources_source:
                leaked.append(op)

        assert leaked == [], (
            f"resources.py contains references to {len(leaked)} internal-only operations "
            f"from service-2.json: {leaked[:10]}"
        )

    def test_internal_fields_not_in_resources(self):
        """Ensure shape members marked internalonly in service-2.json are not generated into resources.py."""
        internal_fields = []
        for shape_name, shape_def in self.service_json.get("shapes", {}).items():
            for member_name, member_def in shape_def.get("members", {}).items():
                if member_def.get("internalonly"):
                    internal_fields.append((shape_name, member_name))

        if not internal_fields:
            return  # public service-2.json has no internal fields, nothing to check

        # Check if internal field names appear as parameters in resources.py
        leaked = []
        for shape_name, member_name in internal_fields:
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", member_name).lower()
            if (
                re.search(rf"\b{snake}\s*[:=]", self.resources_source)
                or f'"{member_name}"' in self.resources_source
            ):
                leaked.append(f"{shape_name}.{member_name}")

        assert leaked == [], (
            f"resources.py contains references to {len(leaked)} internal-only fields "
            f"from service-2.json: {leaked[:10]}"
        )

    def test_no_internal_class_names(self):
        """Ensure resources.py does not contain any *Internal class names."""
        resource_classes = [
            name
            for name in dir(self.resources_module)
            if isinstance(getattr(self.resources_module, name), type) and name.endswith("Internal")
        ]
        assert (
            resource_classes == []
        ), f"resources.py contains {len(resource_classes)} internal-only classes: {resource_classes}"
