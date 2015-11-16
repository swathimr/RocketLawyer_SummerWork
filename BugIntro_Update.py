#!/usr/bin/python
# -*- coding: utf-8 -*-
#
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import requests
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def getSyncDate():
    conn = mysql.connector.connect(host='dbrllasbihamaster.f1tst.rl.com',database='rl_intelligence',user='reporting',password='d4ta!sgo0d')
    cursor = conn.cursor()
    sql = "SELECT sync_date FROM hd_event_sync_queue where event_name='tm_bug_introduction'"
    cursor.execute(sql)
    data = cursor.fetchone()
    sync_date ="\'"+data[0].strftime('%Y-%m-%d')+"\'"
    logger.info("synDate::"+sync_date)
    
    current_date = datetime.now()
    today="\'"+current_date.strftime('%Y-%m-%d')+"\'"
    logger.info("today::"+today)
    
    if sync_date==today:
        filter = ["ChangeDate>="+sync_date]
        #print filter
        logger.info("Syn date and the todays date is same")
    else:
        filter =["ChangeDate>="+sync_date,"ChangeDate<="+today]
        logger.info("Syn date and the todays date are different")
    conn.close()
    return filter
    
def getJSONData():
    logger.info("Calling extrenal versionone api and retrieving JSON data")
    filter_param = getSyncDate()
    print filter_param
    v1PostData = {
    "from": "Defect",
    "select":
    [
    "Number",
    "Name",
    "Priority.Name",
  	"Scope.Name",
  	"Status.Name",
    "CreateDate",
    "AssetType",
    "AssetState",
    "ChangeDate"
    ],
    "filter": filter_param
    }
    
    resp = requests.post("https://www2.v1host.com/RocketLawyer/query.v1",json=v1PostData,auth=('admin','admin'))
    jsonresp = resp.json()
    return jsonresp[0]
    
def populateBugIntro_indb(data):
    query = "INSERT INTO BugIntroduction(defect_id,DefectName,Priority,ProjectName,Status,CreatedDate,Link,State,Age) " \
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)" \
            "ON DUPLICATE KEY UPDATE DefectName=VALUES(DefectName),Priority=VALUES(Priority),ProjectName=VALUES(ProjectName),"\
            "Status=VALUES(Status),CreatedDate=VALUES(CreatedDate),Link=VALUES(Link),State=VALUES(State),Age=VALUES(Age)"
    conn = None
    cursor=None
    try:
        logger.info("Establishing DB connection")
        conn = mysql.connector.connect(host='dbrllasbihamaster.f1tst.rl.com',database='technology_metrics',user='reporting',password='d4ta!sgo0d')
        if conn.is_connected():
           logger.info('Connected to MySQL database')
        cursor = conn.cursor()
        cursor.executemany(query,data)
        conn.commit()
        logger.info("Bug Introduction per daterange data insertion successful")
    except Error as e:
        conn.rollback()
        logger.debug("Exception occured while inserting BugIntro data (Date Range) into database")
        logger.error(e)
    finally:
        if cursor:
    	    cursor.close()
    	if conn:
    	    conn.close()
    	    
def populateBugIntroduction():
    logger.info("Start populating data for BugInto based on last sync date")
    json_val=getJSONData()
    value_list=[]
    for value in json_val:
        age=None
        if(value["Priority.Name"] == None):
            value["Priority.Name"]='Null'
        if(value["Status.Name"] == None):
            value["Status.Name"] = 'Null'
        if(str(value["AssetState"])!='200'):
            if (value["AssetState"] == "Closed"):
                change_date = value["ChangeDate"].split('.')[0]+"Z"
                date_convert1 = datetime.strptime(str(change_date),"%Y-%m-%dT%H:%M:%SZ")
                create_date = value["CreateDate"].split('.')[0]+"Z"
                date_convert=datetime.strptime(str(create_date),"%Y-%m-%dT%H:%M:%SZ")
                difference = date_convert1-date_convert
                age = str(difference.days)
                if(difference.days==0):
                    age=1
            link_url = "https://www2.v1host.com/RocketLawyer/"+value["AssetType"]+".mvc/Summary?oidToken="+value["_oid"]
            value_list.append((value["Number"],value["Name"].encode('ascii', 'ignore').decode('ascii'),value["Priority.Name"],value["Scope.Name"],value["Status.Name"],value["CreateDate"],link_url,value["AssetState"],age))
    #print value_list
    populateBugIntro_indb(value_list)
    logger.info("****Bug intro Rate Done****")

if __name__ == '__main__':
    populateBugIntroduction()