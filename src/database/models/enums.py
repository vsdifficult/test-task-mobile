from enum import Enum

class ActionType(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"  
    SHARE = "share"     


class PermissionScope(str, Enum):
    OWN = "own"              
    DEPARTMENT = "department"  
    ALL = "all"              


class ResourceType(str, Enum):
    DOCUMENT = "document"
    PROJECT = "project"
    REPORT = "report"
    USER = "user"
    SETTING = "setting"