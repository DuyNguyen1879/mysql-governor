#coding:utf-8
import math
import os
import shutil
import sys
import time
import urllib2
import tempfile
import errno

sys.path.append("../")

from utilities import is_file_owned_by_package, exec_command_out

class Storage(object):
    """
    Manage unneeded filesthat was left by previous MySQL installations
    """
    STORE_PATH = "/usr/share/lve/dbgovernor/storage/"

    def _is_writable(self, path):
        try:
            testfile = tempfile.TemporaryFile(dir = path)
            testfile.close()
        except OSError as e:
            if e.errno == errno.EACCES:  # 13
                return False
            e.filename = path
            raise
        return True

    def _file_from_list_exists(self, path, storage):
        if storage == True:
            path = self.STORE_PATH + path
        if os.path.islink(path):
            return True
        return os.path.exists(path)

    def _get_package_owner(self, file_path):
        package = is_file_owned_by_package(file_path)
        return package


    def _is_file_not_owned_by_package(self, path):
        return not self._get_package_owner(path)

    def _mkdir_p(self, path):
        path = os.path.dirname(os.path.abspath(path))
        try:
            os.makedirs(path)
            return True
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                return True
            else:
                return False

    def _find_empty_dirs_in_storage_one_iteration(self):
        for dirpath, dirs, files in os.walk(self.STORE_PATH):
            if not dirs and not files:
                yield dirpath


    def _find_empty_dirs_in_storage(self):
        result = list(self._find_empty_dirs_in_storage_one_iteration())
        root_found=False
        while not root_found and len(result)>0:
            for dir_name in result:
                dir_name_no_slash = dir_name.rstrip('/')
                if dir_name_no_slash==self.STORE_PATH.rstrip('/'):
                    root_found = True
                    break
                print("Directory %s is empty and will be removed" % dir_name)
                shutil.rmtree(dir_name)
            result = list(self._find_empty_dirs_in_storage_one_iteration())

    def _check_systemd_service(self, name, path_to_file):
        """
        If it is service. It should be disabled before moving
        """
        srv = name + ".service"
        if srv in path_to_file and os.path.exists("/usr/bin/systemctl"):
                exec_command_out("systemctl disable " + srv)

    def save_file_to_storage(self, path_to_file):
        """
        Save file to storage
        """
        if self._file_from_list_exists(path_to_file, False)==True and self._is_writable(self.STORE_PATH) == True and self._is_file_not_owned_by_package(path_to_file)==True:
            print("File %s moved to storage" % path_to_file)
            self._mkdir_p(self.STORE_PATH + path_to_file)
            self._check_systemd_service("mysql", path_to_file)
            self._check_systemd_service("mysqld", path_to_file)
            self._check_systemd_service("mariadb", path_to_file)
            shutil.move(path_to_file, self.STORE_PATH + path_to_file)

    def restore_file_from_storage(self, path_to_file):
        """
        Restore file from storage
        """
        if self._file_from_list_exists(path_to_file, True)==True:
            print("File %s restored" % path_to_file)
            self._mkdir_p(path_to_file)
            shutil.move(self.STORE_PATH + path_to_file, path_to_file)
        self._find_empty_dirs_in_storage()


    def list_files_from_storage(self, restore):
        """
        List files from storage
        """
        rootDir = self.STORE_PATH
        for dirName, subdirList, fileList in os.walk(rootDir):
            if dirName == rootDir:
                continue
            if len(fileList) > 0:
                for fname in fileList:
                    f_path = dirName +"/"+ fname
                    if restore==True:
                        self.restore_file_from_storage("/" + f_path.replace(rootDir, ""))
                    else:
                        access_time = ""
                        if os.path.islink(f_path):
                            access_time = time.ctime(os.lstat(f_path).st_ctime)
                        else:
                            access_time = time.ctime(os.path.getctime(f_path))
                        if dirName.replace(rootDir, "") != "":
                            print('Moved to storage: %s\tFile: /%s/%s' % (access_time, dirName.replace(rootDir, ""), fname))
                        else:
                            print('Moved to storage: %s\tFile: /%s' % (access_time, fname))
        if restore==True:
            self._find_empty_dirs_in_storage()

    def apply_files_from_list(self, path_to_list):
        """
        Save files from list to storage
        """
        if os.path.exists(path_to_list):
            with open(path_to_list) as fp:
                for line in fp:
                    line = line.strip()
                    if self._file_from_list_exists(line, True)==False and self._file_from_list_exists(line, False)==True:
                        self.save_file_to_storage(line)


    def empty_storage(self):
        """
        Delete all files from storage
        """
        for the_file in os.listdir(self.STORE_PATH):
            file_path = os.path.join(self.STORE_PATH, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path): 
                    shutil.rmtree(file_path)
            except Exception as e:
                print(e)

    def check_root_permissions(self):
        """
        Script should run under root only
        """
        if os.geteuid() != 0:
            exit("You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")