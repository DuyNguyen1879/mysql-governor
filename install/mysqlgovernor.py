#!/opt/alt/python27/bin/python2.7
#coding:utf-8
import argparse
import sys
import time

from clcommon import cpapi

from modules import InstallManager, Storage
from utilities import exec_command, bcolors, query_yes_no, correct_mysqld_service_for_cl7, set_debug


def build_parser():
    """
    Build CLI parser
    """
    parser = argparse.ArgumentParser(prog="install-mysql", add_help=True,
                                     description="Use following syntax to manage DBGOVERNOR install utility:")
    parser.add_argument("--verbose", help="switch verbose level on",
                        dest="verbose", action="store_true", default=False)
    parser.add_argument("--mysql-version", help="select MySQL version for db-governor. Available mysql types: auto, mysql50, mysql51, mysql55, mysql56, mysql57, mariadb55, mariadb100, mariadb101",
                        dest="mysql_version", required=False)
    parser.add_argument("-i", "--install", help="install MySQL for db-governor",
                        dest="install", action="store_true", default=False)
    parser.add_argument("-d", "--delete", help="delete MySQL for db-governor",
                        dest="delete", action="store_true", default=False)
    parser.add_argument("--install-beta", help="install MySQL beta for governor or update beta if exists newer beta version",
                        dest="install_beta", action="store_true", default=False)
    parser.add_argument("-c", "--clean-mysql", help="clean MySQL packages list (after governor installation)",
                        dest="clean_mysql", action="store_true", default=False)
    parser.add_argument("-m", "--clean-mysql-delete", help="clean cl-MySQL packages list (after governor deletion)",
                        dest="clean_mysql_delete", action="store_true", default=False)
    parser.add_argument("-t", "--dbupdate", help="update UserMap file",
                        dest="dbupdate", action="store_true", default=False)
    parser.add_argument("--fix-cpanel-hooks", help="fix adduser and deluser hooks for cPanel",
                        dest="fix_cpanel_hooks", action="store_true", default=False)
    parser.add_argument("--fix-cpanel-cl-mysql", help="fix mysqld service for cPanel(CL7)",
                        dest="fix_cpanel_cl_mysql", action="store_true", default=False)
    parser.add_argument("--force", help="Don`t exit if percona installation found",
                        dest="force", action="store_true", default=False)
    parser.add_argument("-u", "--upgrade", help="Option is deprecated. Use `yum update` instead",
                        dest="upgrade", action="store_true", default=False)
    parser.add_argument("--update-mysql-beta", help="Option is deprecated. Use --install-beta instead",
                        dest="update_mysql_beta", action="store_true", default=False)
    parser.add_argument("--fs-suid", help="Helper utility", dest="fs_suid",
                        action="store_true", default=False)
    parser.add_argument("--yes", help="Install without confirm", dest="yes",
                        action="store_true", default=False)
    parser.add_argument("--list-saved-files", help="Show list of saved MySQL old files in storage",
                        dest="store_list", action="store_true", default=False)
    parser.add_argument("--save-file-to-storage", help="Save file to storage",
                        dest="store_save", required=False)
    parser.add_argument("--restore-file-from-storage", help="Restore file from storage",
                        dest="store_restore", required=False)
    parser.add_argument("--save-files-from-list", help="Save file to storage according to files list /usr/share/lve/dbgovernor/list_problem_files.txt",
                        dest="store_list_files", action="store_true", default=False)
    parser.add_argument("--restore-all-files", help="Restore all files from storage",
                        dest="restore_list_all", action="store_true", default=False)
    parser.add_argument("--clean-storage", help="Clean up storage",
                        dest="store_clean", action="store_true", default=False)
    parser.add_argument("--correct-cl7-service-name", help="Remove /etc/init.d/mysql(d) if exists for CloudLinux 7",
                        dest="cl7_correct", action="store_true", default=False)
    parser.add_argument("--output-commands", help="Echo al commands executed by governor's install script",
                        dest="debug_flag", action="store_true", default=False)
    return parser


def main(argv):
    """
    Run main actions
    """
    parser = build_parser()
    if not argv:
        parser.print_help()
        sys.exit(2)

    opts = parser.parse_args(argv)


    storage_holder = Storage()
    storage_holder.check_root_permissions()
    # create install manager instance for current cp
    manager = InstallManager.factory(cpapi.CP_NAME)
    
    if opts.debug_flag:
        set_debug()

    if opts.install or opts.install_beta:
        warn_message()
        manager.cleanup()
        detect_percona(opts.force)

        # remove current packages and install new packages
        if manager.install(opts.install_beta, opts.yes) == True:
            print("Give mysql service time to start before service checking(15 sec)")
            time.sleep(15)

        # check mysqld service status
        if manager.ALL_PACKAGES_NEW_NOT_DOWNLOADED == False:
            if exec_command("ps -Af | grep -v grep | grep mysqld | grep datadir",
                        True, silent=True):
                manager.save_installed_version()
                print "Installation mysql for db_governor completed"
        
            # if sql server failed to start ask user to restore old packages
            elif query_yes_no("Installation is failed. Restore previous version?"):
                print ("Installation mysql for db_governor was failed. Restore "
                   "previous mysql version")
                manager.install_rollback(opts.install_beta)

        manager.cleanup()

    elif opts.delete:
        manager.delete()
        print "Deletion is complete"

        manager.cleanup()

    elif opts.mysql_version:
        manager.set_mysql_version(opts.mysql_version)
        print "Now set MySQL to type '%s'" % opts.mysql_version
    elif opts.dbupdate:
        manager.update_user_map_file()
    elif opts.fix_cpanel_hooks:
        manager.install_mysql_beta_testing_hooks()
    elif opts.fix_cpanel_cl_mysql:
        manager.fix_cl7_mysql()
    elif opts.clean_mysql:
        print "Option is deprecated."
    elif opts.clean_mysql_delete:
        print "Option is deprecated."
    elif opts.upgrade:
        print "Option is deprecated. Use `yum update` instead."
    elif opts.update_mysql_beta:
        print "Option is deprecated. Use --install-beta instead."
    elif opts.fs_suid:
        manager.set_fs_suid_dumpable()
    elif opts.store_list:
        storage_holder.list_files_from_storage(False)
    elif opts.store_save:
        storage_holder.save_file_to_storage(opts.store_save)
    elif opts.store_restore:
        storage_holder.restore_file_from_storage(opts.store_restore)
    elif opts.store_list_files:
        storage_holder.apply_files_from_list("/usr/share/lve/dbgovernor/list_problem_files.txt")
    elif opts.restore_list_all:
        storage_holder.list_files_from_storage(True)
    elif opts.store_clean:
        storage_holder.empty_storage()
    elif opts.cl7_correct:
        correct_mysqld_service_for_cl7("mysql")
        correct_mysqld_service_for_cl7("mysqld")
    else:
        parser.print_help()
        sys.exit(2)


def detect_percona(force):
    if force:
        return None

    packages = exec_command("""rpm -qa|grep -iE "^percona-" """, silent=True)
    if len(packages):
        print "Percona packages deteced:" + ",".join(packages)
        print "You are running Percona, which is not supported by MySQL Governor. If you want to run MySQL governor, we would have to uninstall Percona,and substitute it for MariaDB or MySQL. Run installator next commands for install:"
        print InstallManager._rel("mysqlgovernor.py")+" --mysql-version=mysql56 (or mysql50, mysql51, mysql55, mysql57, mariadb55, mariadb100, mariadb101)"
        print InstallManager._rel("mysqlgovernor.py")+" --install --force"
        sys.exit(2)


def warn_message():
    print bcolors.WARNING + "!!!Before making any changing with database make sure that you have reserve copy of users data!!!"+ bcolors.ENDC
    print bcolors.FAIL + "!!!!!!!!!!!!!!!!!!!!!!!!!!Ctrl+C for cancellation of installation!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"+ bcolors.ENDC
    print bcolors.OKGREEN + "Instruction: how to create whole database backup - " + bcolors.OKBLUE +"http://docs.cloudlinux.com/index.html?backing_up_mysql.html"+ bcolors.ENDC
    time.sleep(10)


if "__main__" == __name__:
    main(sys.argv[1:])
