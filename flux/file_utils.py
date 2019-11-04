# -*- coding: utf8 -*-

import io
import os
import shutil
import stat


def split_url_path(path):
  """
  Separates URL path to repository name and path.

  # Parameters
  path (str): The path from URL.

  # Return
  tuple (str, str): The repository name and the path to be listed.
  """

  separator = '/'
  parts = path.split(separator)
  return separator.join(parts[0:2]), separator.join(parts[2:])


def list_folder(cwd):
  """
  List folder on *cwd* path as list of *File*.

  # Parameters
  cwd (str): The absolute path to be listed.

  # Return
  list (File): The list of files and folders listed in path.
  """

  data = sorted(os.listdir(cwd))
  dirs = []
  files = []
  for filename in data:
    file = File(filename, cwd)
    if file.type == File.TYPE_FOLDER:
      dirs.append(file)
    else:
      files.append(file)
  result = dirs + files
  return result


def create_folder(cwd, folder_name):
  """
  Creates folder named *folder_name* on defined *cwd* path.
  If does not exist, it creates it and return new path of folder.
  If already exists, it returns empty str.

  # Parameters
  cwd (str): The absolute path, where folder should be created.
  folder_name (str): The name of folder to be created.

  # Return
  str: Path of newly created folder, if it does not already exist.
  """

  path = os.path.join(cwd, folder_name)
  if not os.path.exists(path):
    os.makedirs(path)
    return path
  return ''


def create_file(cwd, file_name):
  """
  Creates file named *file_name* on defined *cwd* path.
  If does not exist, it creates it and return new path of file.
  If already exists, it returns empty str.

  # Parameters
  cwd (str): The absolute path, where file should be created.
  file_name (str): The name of file to be created.

  # Return
  str: Path of newly created file, if it does not already exist.
  """

  path = os.path.join(cwd, file_name)
  if not os.path.exists(path):
    open(path, 'w').close()
    return path
  return ''


def create_file_path(file_path):
  """
  Creates file defined by *file_path*.
  If does not exist, it creates it and return new path of file.
  If already exists, it returns empty str.

  # Parameters
  cwd (str): The absolute path, where file should be created.
  file_name (str): The name of file to be created.

  # Return
  str: Path of newly created file, if it does not already exist.
  """

  if not os.path.exists(file_path):
    open(file_path, 'w').close()
    return file_path
  return ''


def read_file(path):
  """
  Reads file located in defined *path*.
  If does not exist, it returns empty str.

  # Parameters
  path (str): The absolute path of file to be read.

  # Return
  str: Text content of file.
  """

  if os.path.isfile(path):
    file = open(path, mode='r')
    content = file.read()
    file.close()
    return content
  return ''


def write_file(path, data, encoding='utf8'):
  """
  Writes *data* into file located in *path*, only if it already exists.
  As workaround, it replaces \r symbol.

  # Parameters
  path (str): The absolute path of file to be written.
  data (str): Text content to be written.
  """

  if os.path.isfile(path):
    file = io.open(path, mode='w', encoding=encoding)
    file.write(data.replace('\r', ''))
    file.close()


def rename(path, new_path):
  """
  Performs rename operation from *path* to *new_path*. This operation
  performs only in case, that there is not file/folder with same name.

  # Parameters
  path (str): Old path to be renamed.
  new_path (str): New path to be renamed to.
  """

  if (os.path.isfile(path) and not os.path.isfile(new_path)) or (os.path.isdir(path) and not os.path.isdir(new_path)):
    os.rename(path, new_path)


def delete(path, force=False):
  """
  Performs delete operation on file or folder stored on *path*.
  If on *path* is file, it performs os.remove().
  If on *path* is folder, it performs shutil.rmtree().

  # Parameters
  path (str): The absolute path of file or folder to be deleted.
  """

  onerror = None
  if force:
    def onerror(func, path, exc_info):
      if not os.access(path, os.W_OK):
          os.chmod(path, stat.S_IWUSR)
          func(path)
      else:
          raise

  if os.path.isfile(path):
    os.remove(path)
  elif os.path.isdir(path):
    shutil.rmtree(path, onerror=onerror)


def human_readable_size(filesize = 0):
  """
  Converts number of bytes from *filesize* to human-readable format.
  e.g. 2048 is converted to "2 kB".

  # Parameters:
  filesize (int): The size of file in bytes.

  # Return:
  str: Human-readable size.
  """

  for unit in ['', 'k', 'M', 'G', 'T', 'P']:
    if filesize < 1024:
      return "{} {}B".format("{:.2f}".format(filesize).rstrip('0').rstrip('.'), unit)
    filesize = filesize / 1024
  return '0 B'


class File:
  TYPE_FOLDER = 'folder'
  TYPE_FILE = 'file'

  def __init__(self, filename, path):
    full_path = os.path.join(path, filename)

    self.type = File.TYPE_FOLDER if os.path.isdir(full_path) else File.TYPE_FILE
    self.filename = filename
    self.path = path
    self.filesize = os.path.getsize(full_path) if self.type == File.TYPE_FILE else 0
    self.filesize_readable = human_readable_size(self.filesize)
