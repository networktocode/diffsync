"""Exception classes used in DiffSync.

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


class ObjectCrudException(Exception):
    """Base class for various failures during CRUD operations."""


class ObjectNotCreated(ObjectCrudException):
    """Exception raised if an object Create operation failed."""


class ObjectNotUpdated(ObjectCrudException):
    """Exception raised if an object Update operation failed."""


class ObjectNotDeleted(ObjectCrudException):
    """Exception raised if an object Delete operation failed."""


class ObjectStoreException(Exception):
    """Base class for various failures during object storage in local caches."""


class ObjectAlreadyExists(ObjectStoreException):
    """Exception raised when trying to store a DiffSyncModel or DiffElement that is already being stored."""


class ObjectNotFound(ObjectStoreException):
    """Exception raised when trying to access a DiffSyncModel that isn't in storage."""


class ObjectStoreWrongType(ObjectStoreException):
    """Exception raised when trying to store a DiffSyncModel of the wrong type."""
