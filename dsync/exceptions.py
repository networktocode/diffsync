"""Exception classes used in DSync."""


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
    """Exception raised when trying to store a DSyncModel or DiffElement that is already being stored."""


class ObjectNotFound(ObjectStoreException):
    """Exception raised when trying to access a DSyncModel that isn't in storage."""


class ObjectStoreWrongType(ObjectStoreException):
    """Exception raised when trying to store a DSyncModel of the wrong type."""
