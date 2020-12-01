"""DiffSync helper classes for calculating and performing diff and sync operations.

Copyright (c) 2020 Network To Code, LLC <info@networktocode.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from collections.abc import Iterable as ABCIterable, Mapping as ABCMapping
from typing import Iterable, List, Mapping, Optional, Tuple, Type, TYPE_CHECKING

import structlog  # type: ignore

from .diff import Diff, DiffElement
from .enum import DiffSyncModelFlags, DiffSyncFlags, DiffSyncStatus
from .exceptions import ObjectNotFound, ObjectNotCreated, ObjectNotUpdated, ObjectNotDeleted, ObjectCrudException
from .utils import intersection

if TYPE_CHECKING:  # pragma: no cover
    # For type annotation purposes, we have a circular import loop between __init__.py and this file.
    from . import DiffSync, DiffSyncModel  # pylint: disable=cyclic-import


class DiffSyncDiffer:
    """Helper class implementing diff calculation logic for DiffSync.

    Independent from Diff and DiffElement as those classes are purely data objects, while this stores some state.
    """

    def __init__(
        self, src_diffsync: "DiffSync", dst_diffsync: "DiffSync", flags: DiffSyncFlags, diff_class: Type[Diff] = Diff
    ):
        """Create a DiffSyncDiffer for calculating diffs between the provided DiffSync instances."""
        self.src_diffsync = src_diffsync
        self.dst_diffsync = dst_diffsync
        self.flags = flags

        self.logger = structlog.get_logger().new(src=src_diffsync, dst=dst_diffsync, flags=flags)
        self.diff_class = diff_class
        self.diff: Optional[Diff] = None

    def calculate_diffs(self) -> Diff:
        """Calculate diffs between the src and dst DiffSync objects and return the resulting Diff."""
        if self.diff is not None:
            return self.diff

        self.logger.info("Beginning diff calculation")
        self.diff = self.diff_class()
        for obj_type in intersection(self.dst_diffsync.top_level, self.src_diffsync.top_level):
            diff_elements = self.diff_object_list(
                src=self.src_diffsync.get_all(obj_type), dst=self.dst_diffsync.get_all(obj_type),
            )

            for diff_element in diff_elements:
                self.diff.add(diff_element)

        self.logger.info("Diff calculation complete")
        self.diff.complete()
        return self.diff

    def diff_object_list(self, src: Iterable["DiffSyncModel"], dst: Iterable["DiffSyncModel"]) -> List[DiffElement]:
        """Calculate diffs between two lists of like objects.

        Helper method to `calculate_diffs`, usually doesn't need to be called directly.

        These helper methods work in a recursive cycle:
        diff_object_list -> diff_object_pair -> diff_child_objects -> diff_object_list -> etc.
        """
        diff_elements = []

        if isinstance(src, ABCIterable) and isinstance(dst, ABCIterable):
            # Convert a list of DiffSyncModels into a dict using the unique_ids as keys
            dict_src = {item.get_unique_id(): item for item in src} if not isinstance(src, ABCMapping) else src
            dict_dst = {item.get_unique_id(): item for item in dst} if not isinstance(dst, ABCMapping) else dst

            combined_dict = {}
            for uid in dict_src:
                combined_dict[uid] = (dict_src.get(uid), dict_dst.get(uid))
            for uid in dict_dst:
                combined_dict[uid] = (dict_src.get(uid), dict_dst.get(uid))
        else:
            # In the future we might support set, etc...
            raise TypeError(f"Type combination {type(src)}/{type(dst)} is not supported... for now")

        self.validate_objects_for_diff(combined_dict.values())

        for uid in combined_dict:
            src_obj, dst_obj = combined_dict[uid]
            diff_element = self.diff_object_pair(src_obj, dst_obj)

            if diff_element:
                diff_elements.append(diff_element)

        return diff_elements

    @staticmethod
    def validate_objects_for_diff(object_pairs: Iterable[Tuple[Optional["DiffSyncModel"], Optional["DiffSyncModel"]]]):
        """Check whether all DiffSyncModels in the given dictionary are valid for comparison to one another.

        Helper method for `diff_object_list`.

        Raises:
            TypeError: If any pair of objects in the dict have differing get_type() values.
            ValueError: If any pair of objects in the dict have differing get_shortname() or get_identifiers() values.
        """
        for src_obj, dst_obj in object_pairs:
            # TODO: should we check/enforce whether all source models have the same DiffSync, whether all dest likewise?
            # TODO: should we check/enforce whether ALL DiffSyncModels in this dict have the same get_type() output?
            if src_obj and dst_obj:
                if src_obj.get_type() != dst_obj.get_type():
                    raise TypeError(f"Type mismatch: {src_obj.get_type()} vs {dst_obj.get_type()}")
                if src_obj.get_shortname() != dst_obj.get_shortname():
                    raise ValueError(f"Shortname mismatch: {src_obj.get_shortname()} vs {dst_obj.get_shortname()}")
                if src_obj.get_identifiers() != dst_obj.get_identifiers():
                    raise ValueError(f"Keys mismatch: {src_obj.get_identifiers()} vs {dst_obj.get_identifiers()}")

    def diff_object_pair(
        self, src_obj: Optional["DiffSyncModel"], dst_obj: Optional["DiffSyncModel"]
    ) -> Optional[DiffElement]:
        """Diff the two provided DiffSyncModel objects and return a DiffElement or None.

        Helper method to `calculate_diffs`, usually doesn't need to be called directly.

        These helper methods work in a recursive cycle:
        diff_object_list -> diff_object_pair -> diff_child_objects -> diff_object_list -> etc.
        """
        if src_obj:
            model = src_obj.get_type()
            unique_id = src_obj.get_unique_id()
            shortname = src_obj.get_shortname()
            keys = src_obj.get_identifiers()
        elif dst_obj:
            model = dst_obj.get_type()
            unique_id = dst_obj.get_unique_id()
            shortname = dst_obj.get_shortname()
            keys = dst_obj.get_identifiers()
        else:
            raise RuntimeError("diff_object_pair() called with neither src_obj nor dst_obj??")

        log = self.logger.bind(model=model, unique_id=unique_id)
        if self.flags & DiffSyncFlags.SKIP_UNMATCHED_SRC and not dst_obj:
            log.debug("Skipping unmatched source object")
            return None
        if self.flags & DiffSyncFlags.SKIP_UNMATCHED_DST and not src_obj:
            log.debug("Skipping unmatched dest object")
            return None
        if src_obj and src_obj.model_flags & DiffSyncModelFlags.IGNORE:
            log.debug("Skipping due to IGNORE flag on source object")
            return None
        if dst_obj and dst_obj.model_flags & DiffSyncModelFlags.IGNORE:
            log.debug("Skipping due to IGNORE flag on dest object")
            return None

        diff_element = DiffElement(
            obj_type=model,
            name=shortname,
            keys=keys,
            source_name=self.src_diffsync.name,
            dest_name=self.dst_diffsync.name,
            diff_class=self.diff_class,
        )

        if src_obj:
            diff_element.add_attrs(source=src_obj.get_attrs(), dest=None)
        if dst_obj:
            diff_element.add_attrs(source=None, dest=dst_obj.get_attrs())

        # Recursively diff the children of src_obj and dst_obj and attach the resulting diffs to the diff_element
        self.diff_child_objects(diff_element, src_obj, dst_obj)

        return diff_element

    def diff_child_objects(
        self, diff_element: DiffElement, src_obj: Optional["DiffSyncModel"], dst_obj: Optional["DiffSyncModel"],
    ):
        """For all children of the given DiffSyncModel pair, diff recursively, adding diffs to the given diff_element.

        Helper method to `calculate_diffs`, usually doesn't need to be called directly.

        These helper methods work in a recursive cycle:
        diff_object_list -> diff_object_pair -> diff_child_objects -> diff_object_list -> etc.
        """
        children_mapping: Mapping[str, str]
        if src_obj and dst_obj:
            # Get the subset of child types common to both src_obj and dst_obj
            src_mapping = src_obj.get_children_mapping()
            dst_mapping = dst_obj.get_children_mapping()
            children_mapping = {}
            for child_type, child_fieldname in src_mapping.items():
                if child_type in dst_mapping:
                    children_mapping[child_type] = child_fieldname
        elif src_obj:
            children_mapping = src_obj.get_children_mapping()
        elif dst_obj:
            children_mapping = dst_obj.get_children_mapping()
        else:
            raise RuntimeError("Called with neither src_obj nor dest_obj??")

        for child_type, child_fieldname in children_mapping.items():
            # for example, child_type == "device" and child_fieldname == "devices"

            # for example, getattr(src_obj, "devices") --> list of device uids
            #          --> src_diffsync.get_by_uids(<list of device uids>, "device") --> list of device instances
            src_objs = self.src_diffsync.get_by_uids(getattr(src_obj, child_fieldname), child_type) if src_obj else []
            dst_objs = self.dst_diffsync.get_by_uids(getattr(dst_obj, child_fieldname), child_type) if dst_obj else []

            for child_diff_element in self.diff_object_list(src=src_objs, dst=dst_objs):
                diff_element.add_child(child_diff_element)

        return diff_element


class DiffSyncSyncer:
    """Helper class implementing data synchronization logic for DiffSync.

    Independent from DiffSync and DiffSyncModel as those classes are purely data objects, while this stores some state.
    """

    def __init__(
        self, diff: Diff, src_diffsync: "DiffSync", dst_diffsync: "DiffSync", flags: DiffSyncFlags,
    ):
        """Create a DiffSyncSyncer instance, ready to call `perform_sync()` against."""
        self.diff = diff
        self.dst_diffsync = dst_diffsync
        self.flags = flags

        self.base_logger = structlog.get_logger().new(src=src_diffsync, dst=dst_diffsync, flags=flags)

        # Local state maintained during synchronization
        self.logger: structlog.BoundLogger = self.base_logger
        self.model_class: Type["DiffSyncModel"]
        self.action: Optional[str] = None

    def perform_sync(self) -> bool:
        """Perform data synchronization based on the provided diff.

        Returns:
            bool: True if any changes were actually performed, else False.
        """
        changed = False
        self.base_logger.info("Beginning sync")
        for element in self.diff.get_children():
            changed |= self.sync_diff_element(element)
        self.base_logger.info("Sync complete")
        return changed

    def sync_diff_element(self, element: DiffElement, parent_model: "DiffSyncModel" = None) -> bool:
        """Recursively synchronize the given DiffElement and its children, if any, into the dst_diffsync.

        Helper method to `perform_sync`.

        Returns:
            bool: True if this element or any of its children resulted in actual changes, else False.
        """
        self.model_class = getattr(self.dst_diffsync, element.type)
        diffs = element.get_attrs_diffs()
        self.logger = self.base_logger.bind(
            action=element.action,
            model=element.type,
            unique_id=self.model_class.create_unique_id(**element.keys),
            diffs=diffs,
        )
        self.action = element.action
        ids = element.keys
        # We only actually need the "new" attrs to perform a create/update operation, and don't need any for a delete
        attrs = diffs.get("+", {})

        model: Optional["DiffSyncModel"]
        try:
            model = self.dst_diffsync.get(self.model_class, ids)
            model.set_status(DiffSyncStatus.UNKNOWN)
        except ObjectNotFound:
            model = None

        changed, modified_model = self.sync_model(model, ids, attrs)
        model = modified_model or model

        if not modified_model or not model:
            self.logger.warning("No object resulted from sync, will not process child objects.")
            return changed

        if self.action == "create":
            if parent_model:
                parent_model.add_child(model)
            self.dst_diffsync.add(model)
        elif self.action == "delete":
            if parent_model:
                parent_model.remove_child(model)
            if model.model_flags & DiffSyncModelFlags.SKIP_CHILDREN_ON_DELETE:
                # We don't need to process the child objects, but we do need to discard them from the dst_diffsync
                self.dst_diffsync.remove(model, remove_children=True)
                return changed
            self.dst_diffsync.remove(model)

        for child in element.get_children():
            changed |= self.sync_diff_element(child, parent_model=model)

        return changed

    def sync_model(
        self, model: Optional["DiffSyncModel"], ids: Mapping, attrs: Mapping
    ) -> Tuple[bool, Optional["DiffSyncModel"]]:
        """Create/update/delete the current DiffSyncModel with current ids/attrs, and update self.status and self.message.

        Helper method to `sync_diff_element`.

        Returns:
            tuple: (changed, model) where model may be None if an error occurred
        """
        if self.action is None:
            status = DiffSyncStatus.SUCCESS
            message = "No changes to apply; no action needed"
            self.log_sync_status(self.action, status, message)
            return (False, model)

        try:
            self.logger.debug(f"Attempting model {self.action}")
            if self.action == "create":
                if model is not None:
                    raise ObjectNotCreated(f"Failed to create {self.model_class.get_type()} {ids} - it already exists!")
                model = self.model_class.create(diffsync=self.dst_diffsync, ids=ids, attrs=attrs)
            elif self.action == "update":
                if model is None:
                    raise ObjectNotUpdated(f"Failed to update {self.model_class.get_type()} {ids} - not found!")
                model = model.update(attrs=attrs)
            elif self.action == "delete":
                if model is None:
                    raise ObjectNotDeleted(f"Failed to delete {self.model_class.get_type()} {ids} - not found!")
                model = model.delete()
            else:
                raise ObjectCrudException(f'Unknown action "{self.action}"!')

            if model is not None:
                status, message = model.get_status()
            else:
                status = DiffSyncStatus.FAILURE
                message = f"{self.model_class.get_type()} {self.action} did not return the model object."

        except ObjectCrudException as exception:
            status = DiffSyncStatus.ERROR
            message = str(exception)
            self.log_sync_status(self.action, status, message)
            if self.flags & DiffSyncFlags.CONTINUE_ON_FAILURE:
                return (True, None)
            raise

        self.log_sync_status(self.action, status, message)

        return (True, model)

    def log_sync_status(self, action: Optional[str], status: DiffSyncStatus, message: str):
        """Log the current sync status at the appropriate verbosity with appropriate context.

        Helper method to `sync_diff_element`/`sync_model`.
        """
        if action is None:
            if self.flags & DiffSyncFlags.LOG_UNCHANGED_RECORDS:
                self.logger.debug(message, status=status.value)
        elif status == DiffSyncStatus.SUCCESS:
            self.logger.info(message, status=status.value)
        elif status == DiffSyncStatus.FAILURE:
            self.logger.warning(message, status=status.value)
        else:
            self.logger.error(message, status=status.value)
