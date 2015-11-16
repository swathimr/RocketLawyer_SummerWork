#!/usr/bin/python
# -*- coding: utf-8 -*-
#
import mysql.connector
from mysql.connector import Error
import jenkinsapi
from jenkinsapi.jenkins import Jenkins
from jenkinsapi.build import Build
from datetime import datetime
import logging
import requests

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_server_instance():
    jenkins_url = 'http://rllasbld001:5555/'
    server = Jenkins(jenkins_url, username = '', password = '')
    return server
    
def get_sync_date():
    logger.info("Getting syn date for CodeCoverage")
    db = mysql.connector.connect(host='dbrllasbihamaster.f1tst.rl.com',database='rl_intelligence',user='reporting',password='d4ta!sgo0d')
    cursor = db.cursor()
    sql = "SELECT sync_date FROM hd_event_sync_queue where event_name='tm_code_coverage'"
    cursor.execute(sql)
    data = cursor.fetchone()
    sync_date =data[0].strftime('%Y-%m-%dT%H:%M:%SZ')
    logger.info("Code Coverage SynDate::"+sync_date)
    cursor.close()
    db.close()
    return sync_date    
    
def get_codecoverage_data():
    instance = get_server_instance()
    data_list=[]
    d = get_sync_date()
    syncdate=datetime.strptime(d,"%Y-%m-%dT%H:%M:%SZ")
    for job in instance.keys():
        if(len(instance[job].get_build_dict())>0):
            last_build_time = instance[job].get_last_build().get_timestamp().strftime('%Y-%m-%dT%H:%M:%SZ')
            timevalue=datetime.strptime(last_build_time,"%Y-%m-%dT%H:%M:%SZ")
            logger.info("SyncDate for Codecoverage is::"+str(syncdate))
            logger.info("Last build time for the job is ::"+str(timevalue))
            print (syncdate<=timevalue)
            if(syncdate<=timevalue):
                builds = instance[job].get_build_dict()
                print job+":::::count :::"+str(len(builds))
                if(job != 'AvatarInfoMigrator' or job!='OPS-Chef Sync' or job!='OPS-Chef-dev Sync - Dev Lanes'):
                    for build_num in builds.keys():
                        build =instance[job].get_build(build_num)
                        buildtime=instance[job].get_build(build_num).get_timestamp().strftime('%Y-%m-%dT%H:%M:%SZ')
                        buildtimeval=datetime.strptime(buildtime,"%Y-%m-%dT%H:%M:%SZ")
                        if(syncdate<=buildtimeval):
                            coverage = requests.get("http://rllasbld001:5555/job/"+job+"/"+str(build_num)+"/jacoco/api/json")
                            if(coverage.status_code==200):
                                timestamp=instance[job].get_build(build_num).get_timestamp()
                                method_coverage =str(coverage.json()["methodCoverage"]["covered"])+"/"+str(coverage.json()["methodCoverage"]["total"])
                                class_coverage=str(coverage.json()["classCoverage"]["covered"])+"/"+str(coverage.json()["classCoverage"]["total"])
                                lines_coverage =str(coverage.json()["lineCoverage"]["covered"])+"/"+str(coverage.json()["lineCoverage"]["total"])
                                data_list.append((job,timestamp,str(coverage.json()["methodCoverage"]["percentage"])+'%',method_coverage,str(coverage.json()["classCoverage"]["percentage"])+"%",class_coverage,str(coverage.json()["lineCoverage"]["percentage"])+"%",lines_coverage))
                            else:
                                break
                        else:
                            break
    #print data_list
    return data_list
    
def populate_codecoverage_indb():
    logger.info("Start populating code coverage data")
    coverage_data = get_codecoverage_data()
    query_string="INSERT INTO CodeCoverage(JobName,Timestamp,MethodPercent,MethodCovered,LinesPercent,LinesCovered,ClassPercent,ClassCovered) "
    query = query_string+"VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"
    conn = None
    cursor=None
    try:
        logger.info("Establishing DB connection")
        conn = mysql.connector.connect(host='dbrllasbihamaster.f1tst.rl.com',database='technology_metrics',user='reporting',password='d4ta!sgo0d')
        #conn = mysql.connector.connect(host='localhost',database='test',user='root',password='')
        if conn.is_connected():
            logger.info('Connected to MySQL database')
        cursor = conn.cursor()
        cursor.executemany(query,coverage_data)
        conn.commit()
        logger.info("****CodeCoverage data insertion successful***")
    except Error as e:
        conn.rollback()
        logger.debug("Exception occured while inserting into database")
        logger.error(e)
    finally:
        if cursor:
    	    cursor.close()
    	if conn:
    	    conn.close() 

if __name__ == '__main__':
    populate_codecoverage_indb()