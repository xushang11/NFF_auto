#!/usr/bin/env python

# IMPORT BASE MODULES:
import os
import sys
import commands
import datetime
import exceptions
import subprocess
import string
import time
import re
import time
import traceback
import subprocess
import socket
import shlex
import optparse

#define variables for directory/file names
this=os.path.basename(sys.argv[0])

###############################################################################
# SOME COMMONs OF NFF
#NFF bundles location: http://lss-pulp03.ih.lucent.com/nff/
#NFFv1.0 release notes: http://inserv.ih.lucent.com/compas-cgi/wwwcompas?prodid=191334&dformat=pdf
#NFFv1.0 MariaDB location: http://lss-pulp03.ih.lucent.com/nff/artifacts/nff-mariadb/ 

###############################################################################

# Define debug and log level
LOG_CRITICAL = 	1
LOG_ERROR = 	2
LOG_WARNING = 	3
LOG_INFO =  	4
LOG_DEBUG = 	5

# Define return codes
RTC_SUCCESS =   0
RTC_ERROR =     1
RTC_FAILURE =   2

# Served as global variable. 
# stdout_log is for "Logging to standard output". It is default to False. 
# loglevel is initialized to LOG_ERROR so by default only the logs that has 
# the same or lower level e.g. CRITICAL will be logged. 
stdout_log    = 0 
loglevel = LOG_ERROR

alu_nff =           '/opt/alu-nff/'
alu_nff_bin =       '/opt/alu-nff/bin/'
alu_nff_share =     '/opt/alu-nff/share/'
nff_test_home =     '/root/Project/nff_test/'
logfile =           nff_test_home + 'nff_test.log'
yum_repod =         '/etc/yum.repos.d/'

# command fail or success description suffix
fail_desc = 'failed ~~'
success_desc = 'successfully ~~'

###############################################################################
# MariaDB bundle specific variables:
### default my.cnf example:
### Modified by mariadb_config
### replication active
##[mysqld]
##userstat=0
##datadir=/var/lib/mariadb
##max-binlog-size=100000000
##port=3306
##socket=/var/run/mariadb/mysqld.sock
##basedir=/opt/rh/mariadb55/root/usr
##user=mysql
##plugin-dir=/opt/rh/mariadb55/root/usr/lib64/mysql/plugin
##bind-address=135.2.88.167
##report-port=3306
##server-id=167
##report-host=135.2.88.166
##log-bin=/var/lib/mariadb/mysql-bin
##
##[mysqld_safe]
##pid-file=/var/run/mariadb/mysqld.pid
##log-error=/var/log/mariadb/mysqld.log

### default replication.sql example:
##STOP SLAVE;
##GRANT ALL PRIVILEGES ON *.* TO 'mysql'@'localhost';
##GRANT ALL PRIVILEGES ON *.* TO 'mysql'@'bc-g7-sim3b';
##GRANT ALL PRIVILEGES ON *.* TO 'mysql'@'135.2.88.166';
##GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost';
##GRANT ALL PRIVILEGES ON *.* TO 'root'@'bc-g7-sim3b';
##GRANT ALL PRIVILEGES ON *.* TO 'root'@'135.2.88.166';
##CHANGE MASTER TO 
##MASTER_HOST='135.2.88.166',
##MASTER_USER='mysql';
##GRANT REPLICATION SLAVE ON *.* TO 'mysql'@'%';
##START SLAVE;

# example of exectuting mariadb sql:
# set -o vi; export MDB=/opt/rh/mariadb55/root
# $MDB/usr/bin/mysql --socket=/var/run/mariadb/mysqld.sock -uroot -e "show master status;"

mariadb_nff_home ='/root/nff_test/mariadb/'
mariadb_repo_name = 'mariadb.repo'

mariadb_repo_content ='''[RH6_pulp]
name="redhat server 6"
baseurl=https://135.1.215.52/pulp/repos/content/dist/rhel/server/6/6Server/x86_64/os/
gpgcheck=0
sslverify=0

[RH6_optional]
name="redhat server 6 optional"
baseurl=https://135.1.215.52/pulp/repos/content/dist/rhel/server/6/6Server/x86_64/optional/os/
gpgcheck=0
sslverify=0

[RH6_maria_pulp]
name="mariadb server"
baseurl=https://135.1.215.52/pulp/repos/content/dist/rhel/server/6/6Server/x86_64/rhscl/1/os/
gpgcheck=0
sslverify=0
'''

ALU_nff_mariadb = 'ALU_nff-mariadb-5.5.37-1.x86_64.rpm'
wget_ALU_nff_mariadb = 'wget http://lss-pulp03.ih.lucent.com/nff/artifacts/nff-mariadb/ALU_nff-mariadb-5.5.37-1.x86_64.rpm'
mariadb_adm = alu_nff_bin + 'mariadb_adm'
mariadb_config = alu_nff_bin + 'mariadb_config'
mariadb_util = '/etc/init.d/mariadb_util'
my_cnf = '/etc/mariadb/my.cnf'
MDB = '/opt/rh/mariadb55/root'
mysql = MDB + '/usr/bin/mysql'
default_socket = '/var/run/mariadb/mysqld.sock'

Enable_replication = True
###############################################################################



###############################################################################
# UTILITY FUNCTIONS
###############################################################################
###############################################################################
# Log the specified message string
###############################################################################

def log(msg, filename = '', debug_level = LOG_INFO):
    
    try:
	srcfile = os.path.basename(filename)
	i = srcfile.find('.')
	if i > 0:
	    srcfile = srcfile[0:i]
	line = (str(datetime.datetime.utcnow())[0:22] +
		' ' + srcfile + ': ' + msg + '\n')

	f = open(logfile,"a")
	f.write(line)
	f.close()

	if stdout_log or ( debug_level <= loglevel):
	    print(msg+'\n')

    except Exception, exc:
	print exc # str(exc) is printed
	raise Exception, 'log() failed'


###############################################################################
# Various run command functions
# local_cmd
# remote_cmd
# run_cmd
###############################################################################

def local_cmd(command, display=True):
    '''Runs a shell command, gets its output, and returns its exit code.'''
    print '#########################################'
    if display:
        print command
    (status_code, output) = commands.getstatusoutput(command)
    return(status_code, output)


def remote_cmd(host, command, login='root', display=True, surround='"'):
    '''Runs a shell command remotely, gets its output, 
       and returns its exit code.'''
    print '#########################################'
    ssh_host = ("ssh "+ login + "@" + host + " ")
    ssh_command = (ssh_host + surround + command + surround)

    if display:
        print ssh_command

    (status_code, output) = commands.getstatusoutput(ssh_command)
    return(status_code, output)


def run_cmd(cmd, cmd_desc='shell cmd'):
    '''Module to handle bash/unix command/scripts while tracking return code.'''
#    print cmd_desc
    print '#########################################'
    status = 0
    (status,output) = commands.getstatusoutput(cmd)

    if (status != 0) and (status != None):
        return (status)
    else:
        return (RTC_SUCCESS)


def run_remote_cmd(host, command, cmd_desc='', login='root'):
    '''Wrapper of remote_cmd and run_cmd'''

    fail_desc = 'failed ~~'
    success_desc = 'successfully ~~'
    print '#########################################'
    
    rt, output = remote_cmd(host, command, login)
    if rt != RTC_SUCCESS:
        print cmd_desc + fail_desc
        print output
        exit(1)
    else:
        print cmd_desc + success_desc


def run_cmd_ignore_error(host, command, cmd_desc='', login='root'):
    '''Wrapper of remote_cmd and run_cmd'''
    
    fail_desc = 'failed ~~'
    success_desc = 'successfully ~~'
    print '#########################################'
    
    rt, output = remote_cmd(host, command, login)
    if rt != RTC_SUCCESS:
        print cmd_desc + fail_desc
        print output
    else:
        print cmd_desc + success_desc

        
################################################################################
# setup_sshkeys
# Required options: host. It is string of one host or comma seperated host list.
#If it's host list string, will be split to a host list
################################################################################

def setup_sshkeys(host):

        # autohost root -> VM root
        # setup ssh key for all the VMs that would be admined
        answer = raw_input('Do you want to run ssh key gen commands to setup ssh key? \
                                YES/NO  Please ENTER \n')
        if answer in ['YES', 'yes', 'y', 'Y', 'Yes']:
            pass
        else:
            print 'We have alreay setup sshkey, pass this step...'
            return

        rtc = 0
        SSHKEY_GEN = '/usr/bin/ssh-keygen -t rsa'
        
        # for root login
        id_rsa_root = '/root/.ssh/id_rsa'
        id_rsa_pub_root = '/root/.ssh/id_rsa.pub'
        authorized_keys_root = '/root/.ssh/authorized_keys'
        authorized_keys2_root = '/root/.ssh/authorized_keys2'
        
        # generate id_rsa and id_rsa.pub only if needed, for root
        if os.path.isfile(id_rsa_root) and os.path.isfile(id_rsa_pub_root):
            print 'SSH rsa for root alreay exists. Will reuse it. \n'
        else:
            print 'SSH rsa for root does not exit. Will generate it. \n'
            rtc = run_cmd(SSHKEY_GEN, 'Generate authorized_keys to distribute, set up ssh key')

        if rtc != RTC_SUCCESS:
            print 'SSHKEY GEN failed. Exit...'
            exit(RTC_ERROR)

        #split VM IP in list
        VM_list = []
        if ',' in host:
            VM_list = host.split(',')
        else:
            VM_list.append(host)

        # start to distribute the Key to all the VMs using root login
        for VM_ip in VM_list:
            SSHKEY_DIST = "cat /root/.ssh/id_rsa.pub " + "| ssh -l root " + VM_ip + " \"cat >>/root/.ssh/authorized_keys2 \" "
#            print 'Now we start to run SSHKEY_DIST cmd to distribute SSH key \
#                    for root login on lab MIs ' + VM_ip + '\n'
#            print 'The  SSHKEY_DIST is ' + SSHKEY_DIST
#            print "\n"
            rtc = run_cmd(SSHKEY_DIST, 'Distribute the pub key for ' + VM_ip)
            if rtc != RTC_SUCCESS:
                print 'SSHKEY_DIST failed. Exit...'
                exit(RTC_ERROR)
                
        print 'Now the setup_sshkeys completed successfully.\n'
        return 0

    
###############################################################################
# ASSET/BUNDLE SPECIFIC FUNCTIONS
###############################################################################
###############################################################################
# setenv function to setup NFF env
# env: ['common', 'mariadb', 'idm', ...]
# for common:
#       1) setup_sshkeys
#       2) mkdir required dirs, such as /root/nff_test/
#       3) ...
###############################################################################
def setenv(env = ['common']):
    pass


###############################################################################
## 
## MariaDB asset specific functions
##
###############################################################################
###############################################################################
# setenv function
## On Auto host, all the stuff are stored at nff_test_home, which is
## /root/Project/nff_test/
## On mariadb server, all the stuff are stored at mariadb_nff_home
###############################################################################
def setenv_mariadb(host=''):

    try:
        
        # mkdir mariadb nff home on target VM if does not exist
        step_desc = 'ls to see if mariadb_nff_home exists - '
	command = 'ls -l ' + mariadb_nff_home
	rt, output = remote_cmd(host, command)
	if rt != 0:
            # need to mkdir
            step_desc = 'mkdir mariadb_nff_home on VM - ' + host
            command = '/bin/mkdir -p ' + mariadb_nff_home
            run_remote_cmd(host, command, step_desc)
        else:
            print 'mariadb_nff_home aleady exists on mariadb server ~'

    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'cleanup_mariadb() failed'

###############################################################################
# package cleanup function
# Procedure:
###! /bin/sh
##echo "Cleaning up ALU NFF MariaDB"
##yum -y remove ALU_nff-mariadb
##rm -rf /etc/mariadb /var/run/mariadb /var/log/mariadb /var/lib/mariadb
##chkconfig --del mariadb_util
##echo "Cleaning up ALU NFF MariaDB and MariaDB55"
##yum -y remove mariadb55-mariadb
##yum -y remove mariadb55-runtime
##rm -rf /opt/rh/mariadb55
###############################################################################

def cleanup_mariadb(host=''):

    try:

        run_remote_cmd = run_cmd_ignore_error
	# stop mysqld if it still running
	step_desc = '/etc/init.d/mariadb_util stop - '
	command = '/etc/init.d/mariadb_util stop'
	run_remote_cmd(host, command, step_desc)
	
	#print 'cleanup_mariadb: Cleaning up ALU NFF MariaDB \n'
	# yum -y remove ALU_nff-mariadb
	step_desc = 'Remove ALU_nff-mariadb: yum -y remove ALU_nff-mariadb - '
	command = '/usr/bin/yum -y remove ALU_nff-mariadb'
	run_remote_cmd(host, command, step_desc)

	# rm -rf /etc/mariadb /var/run/mariadb /var/log/mariadb /var/lib/mariadb
	step_desc = 'Remove /etc/mariadb /var/run/mariadb /var/log/mariadb /var/lib/mariadb - '
	command = 'rm -rf /etc/mariadb /var/run/mariadb /var/log/mariadb /var/lib/mariadb'
	run_remote_cmd(host, command, step_desc)

##	# chkconfig --del mariadb_util
##	step_desc = 'chkconfig --del mariadb_util - '
##	command = 'chkconfig --del mariadb_util'
##	run_remote_cmd(host, command, step_desc)

        #    print 'Cleaning up ALU NFF MariaDB and MariaDB55 \n'
	# yum -y remove mariadb55-mariadb
	step_desc = 'yum -y remove mariadb55-mariadb - '
	command = 'yum -y remove mariadb55-mariadb'
	run_remote_cmd(host, command, step_desc)

	# yum -y remove mariadb55-runtime
	step_desc = 'yum -y remove mariadb55-runtime - '
	command = 'yum -y remove mariadb55-runtime'
	run_remote_cmd(host, command, step_desc)

	# rm -rf /opt/rh/mariadb55
	step_desc = 'rm -rf /opt/rh/mariadb55 - '
	command = 'rm -rf /opt/rh/mariadb55'
	run_remote_cmd(host, command, step_desc)

    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'cleanup_mariadb() failed'
	

###############################################################################
# installation function
## Steps:
##      1) wget http://lss-pulp03.ih.lucent.com/nff/artifacts/nff-mariadb/ALU_nff-mariadb-5.5.37-1.x86_64.rpm
##      2) setup yum repo
##      3) yum localinstall ALU_nff
##      4) yum install mariadb server...
##      5) 
###############################################################################

def install_mariadb(host=''):

    try:

	# generate mariadb.repo on autohost then scp to mariadb VM
	fd = open(mariadb_repo_name, 'w')
	fd.write(mariadb_repo_content)
	fd.close()
	
	if os.path.isfile(mariadb_repo_name):
		login = 'root'
		cmd_desc = 'scp mariadb.repo to mariadb server - '
	command = 'scp ' + mariadb_repo_name + ' ' + login + '@' + host + ':' + yum_repod
	rt = run_cmd(command, cmd_desc)
	if rt != RTC_SUCCESS:
	    print cmd_desc + fail_desc
	    exit(1)
	else:
	    print cmd_desc + success_desc

	# wget ALU_nff-mariadb to autohost then scp to mariadb server
	# wget_ALU_nff-mariadb = 'wget http://lss-pulp03.ih.lucent.com/nff/artifacts/nff-mariadb/ALU_nff-mariadb-5.5.37-1.x86_64.rpm'
	cmd_desc = 'wget ALU_nff-mariadb-5.5.37-1.x86_64.rpm from pulp sever - '
	rt = run_cmd(wget_ALU_nff_mariadb, cmd_desc)
	if rt != RTC_SUCCESS:
		print cmd_desc + fail_desc
		exit(1)
	else:
		print cmd_desc + success_desc
		
	# then scp to mariadb server
	cmd_desc = 'scp ALU_nff-mariadb-5.5.37-1.x86_64.rpm to mariadb server - '
	command = 'scp ' + ALU_nff_mariadb + ' ' + login + '@' + host + ':' + mariadb_nff_home
	rt = run_cmd(command, cmd_desc)
	if rt != RTC_SUCCESS:
		print cmd_desc + fail_desc
		exit(1)
	else:
		print cmd_desc + success_desc        

	# yum localinstall ALU_nff-mariadb - yum -y localinstall ALU_nff-mariadb-5.5.37-1.x86_64.rpm
	cmd_desc = 'yum localinstall ALU_nff-mariadb rpm - '
	command = 'yum -y localinstall ' + mariadb_nff_home + ALU_nff_mariadb 
	run_remote_cmd(host, command, cmd_desc)

	# yum install mariadb server
	cmd_desc = 'yum install mariadb55-mariadb-server rpm - '
	command = 'yum -y install mariadb55-mariadb-server' 
	run_remote_cmd(host, command, cmd_desc)    

    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'install_mariadb() failed'
	

###############################################################################
# configuation function
## Steps:
##      1) ./mariadb_config
##
##mariadb_adm = alu_nff_bin + 'mariadb_adm'
##mariadb_config = alu_nff_bin + 'mariadb_config'
##mariadb_util = '/etc/init.d/mariadb_util'
###############################################################################

def config_mariadb(host=''):
    
    try:

        # mariadb_util to generate /etc/mariadb/my.cnf
	cmd_desc = 'mariadb_config to generate my.cnf - '
	command = mariadb_config 
	run_remote_cmd(host, command, cmd_desc)    

        # ls check to see if the my.cnf generated correctly
        # /etc/mariadb/my.cnf
        cmd_desc = 'ls to see if /etc/mariadb/my.cnf exists - '
	command = 'ls -l ' + my_cnf
	rt, output = remote_cmd(host, command)
	if rt != 0:
            print cmd_desc + fail_desc
            exit(1)
        else:
            print 'my.cnf generated successfully on mariadb server ~'

    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'config_mariadb() failed'        

###############################################################################
# start function
# start mariadb server
###############################################################################

def start_mariadb(host=''):

    try:
        # mariadb_util to start mariadb
	cmd_desc = 'mariadb_util to start mariadb server - '
	command = mariadb_util + ' start'
	run_remote_cmd(host, command, cmd_desc)  
        
    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'start_mariadb() failed'   

###############################################################################
# stop function
# stop mariadb server
###############################################################################

def stop_mariadb(host=''):

    try:
        # mariadb_util to start mariadb
	cmd_desc = 'mariadb_util to stop mariadb server - '
	command = mariadb_util + ' stop'
	run_remote_cmd(host, command, cmd_desc)  
        
    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'stop_mariadb() failed'   

###############################################################################
# restart function
# restart mariadb server
###############################################################################

def restart_mariadb(host=''):

    try:
        # stop then start
        stop_mariadb(host)
        start_mariadb(host)
        
    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'restart_mariadb() failed'
    
###############################################################################
# status function
# status mariadb server
###############################################################################

def status_mariadb(host=''):

    try:
        # mariadb_util to status mariadb
	cmd_desc = 'mariadb_util to get status mariadb server - '
	command = mariadb_util + ' status'
	run_remote_cmd(host, command, cmd_desc)  
        
    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'status_mariadb() failed'
    
###############################################################################
# repliaction function
# setup repliaction between master and slave
# Example:
# mariadb_config --activate-repl --bind-address=10.52.72.16 --report-host=10.52.72.80 --server-id=1  
# mariadb_config --activate-repl --bind-address=10.52.72.80 --report-host=10.52.72.16 --server-id=2
# to enable replication correctly:
#       1) after install and configure mariadb, start mariadb
#       2) run replication_mariadb to make configuration
#       3) restart mariadb
# otherwise the replication may not take effect correctly
# (show slave status shows Slave_SQL_Running Error)
###############################################################################

def replication_mariadb(master='', slave=''):

    try:
        # mariadb_config one by one
        # generate server id by using the 4th oct of IP address
        # for master
        server_id = master.split('.')[3]
        cmd_desc = 'mariadb_config to set replication for master - '
        command = mariadb_config + ' --activate-repl '
        command = command + ' --bind-address=' + master
        command = command + ' --report-host=' + slave
        command = command + ' --server-id=' + server_id
        run_remote_cmd(master, command, cmd_desc)  

        # for slave
        server_id = slave.split('.')[3]
        cmd_desc = 'mariadb_config to set replication for slave - '
        command = mariadb_config + ' --activate-repl '
        command = command + ' --bind-address=' + slave
        command = command + ' --report-host=' + master
        command = command + ' --server-id=' + server_id
        run_remote_cmd(slave, command, cmd_desc)              
        
    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'replication_mariadb() failed'

###############################################################################
# replication health check function
# It will run 'show master status' and 'show slave status' to check health
###############################################################################

def replhealth_mariadb(host=''):
    
    try:

    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'replhealth_mariadb() failed'
        
###############################################################################
# log cleanup function
# setup cron jobs to cleanup mariadb mater logs
# Example Cronjob:
##Mariadb_log_cleanup
## Every hour, clean up mariadb master logs
##15 * * * * root /opt/alu-nff/bin/mariadb_adm --action cleanup_master_logs --db testdb >/dev/null 2>&1
##*/1 * * * * root /opt/alu-nff/bin/mariadb_adm --action cleanup_master_logs --db testdb >/dev/null 2>&1
# Options: host as the mariadb server, db for the server db to be cleanup
###############################################################################

def logcleanup_mariadb(host='', db=''):

    try:
        #

    except Exception, exc:
        log( traceback.format_exc(), debug_level = LOG_ERROR)
	raise Exception, 'logcleanup_mariadb() failed'

###############################################################################
#  health check function
# setup cron jobs to do health check/replication check
### Mariadb_repl_health
### Every 5 minutes, check mariadb replication
##*/5 * * * * root /opt/alu-nff/bin/mariadb_adm --action check_health --db testdb > /dev/null 2>&1
# Options: host as the mariadb server, db for the server db to be health check
###############################################################################

def healthcheck_mariadb(host='', db=''):
    pass


###############################################################################
# CLASS DEFINITIONS
###############################################################################

###############################################################################
#   TestPlan - Test Plan Defination
##Based on TMS test plan defination
##The difference is that we use a list to host
##all the test cases to be executed.
##
## TestPlan Driven
## TestPlan -> multiple TestCase
## TestCase -> single TestResult
##
###############################################################################

class TestPlan:
    #data member:
    #setname
    #appl - NFF1.0, NFF1.1, etc
    #asset/bundle, MariaDB, etc. A list to include all the bundles covered
    #tidnum list. A list to include all the test cases.
    #comment
    
    def __init__(self, data = None):
        pass


###############################################################################
#   TestResult - Test Result Defination
##Based on TMS result defination
##TMS result example:
##setname = ct_R10.0_75577_ft
##appl = platform
##grp = 84.101_FT
##tidnum = nb8740
##rload = NFF1.0
##rplace = SYSLAB
##tester = shawn.xu
##run = 24-jul-2014 09:00
##status = 0
##imrno = 
##rexectime = 
##jobnum = 
##official = 
##rmode = 
##fastat = 
##rqstat = 
##casestat = c1:0
##rconfig = 
##rparams = 
##rusr1 = 
##rusr2 = 
##rcomment = 
###############################################################################

class TestResult:
    #data member
    #setname
    #appl - NFF1.0, NFF1.1, etc
    #load 
    #tidnum
    #platform - openstack etc
    #lab
    #status pass or fail
    #time
    #comment

    def __init__(self, data = None):
        pass



###############################################################################
#   TestCase - Test Case Defination
##Based on TMS test plan defination
##TMS case example:
##setname = ct_R10.0_75577_ft
##appl = platform
##grp = 84.101_FT
##phase = 1
##tidnum = nb8726
##pload = R30.09.00
##pplace = SYSLAB
##testtype = 
##pusr1 = 
##pusr2 = 
##plancase = c1, c2
##pconfig = 
##pparams = 
##pcomment = 
###############################################################################

class TestCase:
    ##data member:
    #setname
    #appl - NFF1.0, NFF1.1, etc
    #asset/bundle, MariaDB, etc
    #feature, 84.101 etc
    #requirement
    #description
    #target platform
    #target load
    #tidnum
    #initial condition
    #test procedure - a list or dict of commands to be executed [].
    #"cmd; cmd type; remote or local; descriptoin;"
    #comment
    ##methods:
    #readData() - read from disk file the test cases to be executed
    #testExecute()
    #generateResult()
    #
    
    def __init__(self, data = None):
        pass


###############################################################################
# User-defined exception for cli input errors
# Accepts either a single string or a list of strings as the 'msg'
# Print the msg, log it, and return failure.
class UserInputError(Exception):
    
    def __init__(self, msg):
        self.msg = msg
        
    def __str__(self):
        err_str = ''
	if isinstance(self.msg, str):
            err_str = '\nERROR: ' + self.msg
	else: 	# it's a list
	    for m in self.msg:
		err_str = err_str + '\nERROR: ' + m
	err_str = err_str + '\n'

	print str(err_str)
	# log these, but as INFO, since they are not hard internal errors
	#log(err_str, debug_level = sc.LOG_INFO)
	sys.exit(1)

###############################################################################
# Used for cases where the requested change has already been performed.
# Print the msg, log it, and return success.
class UserInputInfo(Exception):
    
    def __init__(self, msg=''):
	self.msg = msg
	
    def __str__(self):
	info_str = ''
	if isinstance(self.msg, str):
	    info_str = '\nINFO: ' + self.msg
	else: 	# it's a list
	    for m in self.msg:
		info_str = info_str + '\nINFO: ' + m
	info_str = info_str + '\n'

	print str(info_str)
	# log these, but as INFO, since they are not hard internal errors
	log(info_str, debug_level = LOG_INFO)
	sys.exit(0)    

###############################################################################
# test function for unit test
## to do:
##      1) mariadb cleanup                      - done
##      2) mariadb install
##      3) mariadb configuration
##      4) mariadb audit, clean master log
##      5) mariadb verification/health check
##      6) TestDB rewrite
def test():
#    setup_sshkeys('135.2.88.167')
    master = '135.2.88.167'
    slave = '135.2.88.166'

    setup_sshkeys(master)
    setup_sshkeys(slave)
    
    setenv_mariadb(master)
    stop_mariadb(master)
    cleanup_mariadb(master)
    install_mariadb(master)
    config_mariadb(master)
    start_mariadb(master)

    setenv_mariadb(slave)
    stop_mariadb(slave)
    cleanup_mariadb(slave)
    install_mariadb(slave)
    config_mariadb(slave)
    start_mariadb(slave)
    
    replication_mariadb(master, slave)
    
    restart_mariadb(master)
    status_mariadb(master)

    restart_mariadb(slave)
    status_mariadb(slave)


###############################################################################
# MAIN:
###############################################################################
def main(argv):
    
    try:
        test()


    except KeyboardInterrupt:
	    print 'User interrupt to stop command!'
	    sys.exit(1)

    except Exception, exc:
	    print (str(exc))
	    print 'Command failed!'
	    sys.exit(1)

# Execute main
if __name__ == '__main__':
    main(sys.argv[1:])

