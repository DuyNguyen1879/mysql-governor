#!/bin/bash

. /usr/share/lve/dbgovernor/utils/db_install_common.sh

if [ "$1" == "--delete" ]; then
        echo "Removing mysql for db_governor start"

        checkFile "/usr/local/directadmin/custombuild/build"
        param="mysql"
        if [ -e /usr/share/lve/dbgovernor/da.tp.old ]; then
          param=`cat /usr/share/lve/dbgovernor/da.tp.old`
        fi
        /usr/local/directadmin/custombuild/build set mysql_inst $param
        
        rm -f /etc/yum.repos.d/cl-mysql.repo
        /usr/local/directadmin/custombuild/build mysql update
        echo "Removing mysql for db_governor completed"
        exit

fi

echo "The installation of MySQL for db_governor has started"

checkFile "/usr/local/directadmin/custombuild/build"


checkFile "/usr/local/directadmin/custombuild/options.conf"
MYSQL_DA_VER=`cat /usr/local/directadmin/custombuild/options.conf | grep mysql= | cut -d= -f2`
mysqlTypeFileSet="/usr/share/lve/dbgovernor/mysql.type";

MYSQL_DA_TYPE=`cat /usr/local/directadmin/custombuild/options.conf | grep mysql_inst= | cut -d= -f2`
if [ -e /usr/share/lve/dbgovernor/da.tp.old ]; then
  da_old=`cat /usr/share/lve/dbgovernor/da.tp.old`
  if [ "$MYSQL_DA_TYPE" == "no" ]; then
    MYSQL_DA_TYPE=`echo "$da_old"`
  else
    echo "$MYSQL_DA_TYPE" > /usr/share/lve/dbgovernor/da.tp.old
  fi
else
  echo "$MYSQL_DA_TYPE" > /usr/share/lve/dbgovernor/da.tp.old
fi

/usr/local/directadmin/custombuild/build set mysql_inst no

MYSQL_TP="set"

if [ -f "$mysqlTypeFileSet" ]; then
	MYSQL_VER=`cat $mysqlTypeFileSet`
	MYSQL_TP="set"
else
    MYSQL_VER="auto"
    MYSQL_TP="unset"
fi

if [ "$MYSQL_VER" == "auto" ]; then
    MYSQL_VER=$MYSQL_DA_VER
fi

if [ "$MYSQL_TP" == "set" ]; then
  if [ "$MYSQL_VER" == "5.0" ]; then
    MYSQL_VER="mysql50"
  fi 
  if [ "$MYSQL_VER" == "5.1" ]; then
    MYSQL_VER="mysql51"
  fi 
  if [ "$MYSQL_VER" == "5.5" ]; then
    MYSQL_VER="mysql55"
  fi 
  if [ "$MYSQL_VER" == "5.6" ]; then
    MYSQL_VER="mysql56"
  fi 
  if [ "$MYSQL_VER" == "10.0.0" ]; then
    MYSQL_VER="mariadb100"
  fi 
  if [ "$MYSQL_VER" == "10.1.1" ]; then
    MYSQL_VER="mariadb101"
  fi
else
   if [ "$MYSQL_DA_TYPE" == "mysql" ]; then
    if [ "$MYSQL_VER" == "5.0" ]; then
      MYSQL_VER="mysql50"
    fi 
    if [ "$MYSQL_VER" == "5.1" ]; then
      MYSQL_VER="mysql51"
    fi 
    if [ "$MYSQL_VER" == "5.5" ]; then
      MYSQL_VER="mysql55"
    fi 
    if [ "$MYSQL_VER" == "5.6" ]; then
      MYSQL_VER="mysql56"
    fi
    if [ "$MYSQL_VER" == "10.0.0" ]; then
      MYSQL_VER="mariadb100"
    fi 
    if [ "$MYSQL_VER" == "10.1.1" ]; then
      MYSQL_VER="mariadb101"
    fi 
   fi
   if [ "$MYSQL_DA_TYPE" == "mariadb" ]; then
    if [ "$MYSQL_VER" == "10.1" ]; then
      MYSQL_VER="mariadb101"
    fi 
    if [ "$MYSQL_VER" == "10.0" ]; then
      MYSQL_VER="mariadb100"
    fi 
    if [ "$MYSQL_VER" == "5.5" ]; then
      MYSQL_VER="mariadb55"
    fi
    if [ "$MYSQL_VER" == "10.0.0" ]; then
      MYSQL_VER="mariadb100"
    fi 
    if [ "$MYSQL_VER" == "10.1.1" ]; then
      MYSQL_VER="mariadb101"
    fi
   fi
fi

if [ -e /usr/lib/systemd/system/mysql.service ] || [ -e /etc/systemd/system/mysql.service ]; then
/bin/systemctl stop mysql.service
else
/sbin/service mysql stop
fi

installDbTest "$MYSQL_VER"

sleep 5;

DACONF_FILE_MYSQL=/usr/local/directadmin/conf/mysql.conf
MYSQLUSER=`grep "^user=" ${DACONF_FILE_MYSQL} | cut -d= -f2`
MYSQLPASSWORD=`grep "^passwd=" ${DACONF_FILE_MYSQL} | cut -d= -f2`

if [ -e /usr/bin/mysql_upgrade ]; then
   /usr/bin/mysql_upgrade --user=${MYSQLUSER} --password=${MYSQLPASSWORD}
elif [ -e /usr/bin/mysql_fix_privilege_tables ]; then
   /usr/bin/mysql_fix_privilege_tables --user=${MYSQLUSER} --password=${MYSQLPASSWORD}
fi

echo "Patch governor configuration file"
checkFile "/etc/container/mysql-governor.xml"
if [ -e /etc/container/mysql-governor.xml ]; then
    IS_LOGIN=`cat /etc/container/mysql-governor.xml | grep login=`
    if [ -z "$IS_LOGIN" ]; then
         sed -e "s/<connector prefix_separator=\"_\"\/>/<connector prefix_separator=\"_\" login=\"$MYSQLUSER\" password=\"$MYSQLPASSWORD\"\/>/" -i /etc/container/mysql-governor.xml
    fi
    
fi

IS_GOVERNOR=`rpm -qa governor-mysql`
if [ -n "$IS_GOVERNOR" ]; then
	if [ -e /usr/lib/systemd/system/db_governor.service ] || [ -e /etc/systemd/system/db_governor.service ]; then
	    /bin/systemctl restart db_governor.service
	else
	    /sbin/service db_governor restart
	fi
	echo "DB-Governor installed/updated...";
fi

echo "The installation of MySQL for db_governor completed"
echo "Rebuild php please... /usr/local/directadmin/custombuild/build php"
