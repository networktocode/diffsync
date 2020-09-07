class ObjectCrudException(Exception):
    pass


class ObjectNotCreated(ObjectCrudException):
    pass


class ObjectNotUpdated(ObjectCrudException):
    pass


class ObjectNetDeleted(ObjectCrudException):
    pass


class ObjectAlreadyExist(Exception):
    pass
