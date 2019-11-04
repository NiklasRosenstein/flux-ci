from enum import Enum

class GitFolderHandling(Enum):
  """
  This enum defines way, how is .git folder handled during project build.
  """
  DELETE_BEFORE_BUILD = 1
  DELETE_AFTER_BUILD = 2
  DISABLE_DELETE = 3