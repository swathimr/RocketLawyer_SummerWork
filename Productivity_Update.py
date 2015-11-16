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
    sql = "SELECT sync_date FROM hd_event_sync_queue where event_name='tm_productivity'"
    cursor.execute(sql)
    data = cursor.fetchone()
    sync_date ="\'"+data[0].strftime('%Y-%m-%d')+"\'"
    logger.info("synDate::"+sync_date)
    
    current_date = datetime.now()
    today="\'"+current_date.strftime('%Y-%m-%d')+"\'"
    logger.info("today::"+today)
    
    if sync_date==today:
        filter = ["Scope.Schedule.Name='Bi-weekly US Schedule'","ChangeDate>="+sync_date]
        #print filter
        logger.info("Syn date and the todays date is same")
    else:
        filter =["Scope.Schedule.Name='Bi-weekly US Schedule'","ChangeDate>="+sync_date,"ChangeDate<="+today]
        logger.info("Syn date and the todays date are different")
    conn.close()
    return filter
    
def getJSONData():
    filter_param = getSyncDate()
    print filter_param
    v1PostData = {
    "from": "PrimaryWorkitem",
    "select":
    [
    "Number",
    "Name",
  	"Scope.Name",
  	"Status.Name",
    "Timebox.EndDate",
    "Estimate",
    "AssetType"
    ],
    "filter": filter_param
    }
    resp = requests.post("https://www2.v1host.com/RocketLawyer/query.v1",json=v1PostData,auth=('admin','admin'))
    jsonresp = resp.json()
    return jsonresp[0]
    
def populateBL_indb(data):
    query = "INSERT INTO Productivity(vid,ProjectName,SprintEndDate,Status,BacklogItemName,EstimatePts,Link) " \
            "VALUES(%s,%s,%s,%s,%s,%s,%s) " \
            "ON DUPLICATE KEY UPDATE ProjectName=VALUES(ProjectName),SprintEndDate=VALUES(SprintEndDate),Status=VALUES(Status),"\
            "BacklogItemName=VALUES(BacklogItemName),EstimatePts=VALUES(EstimatePts),Link=VALUES(Link)"
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
        logger.info("Productivity per daterange data insertion successful")
    except Error as e:
        conn.rollback()
        logger.debug("Exception occured while inserting Productivity data (Date Range) into database")
        logger.error(e)
    finally:
    	if conn:
    	    conn.close()
    	if cursor:
    	    cursor.close()
    	    
def populateBacklogData():
    logger.info("Start populating data for productivity based on last sync date")
    json_val=getJSONData()
    value_list=[]
    for value in json_val:
        if(value["Status.Name"] == None):
            value["Status.Name"] = 'Null'
        link_url = "https://www2.v1host.com/RocketLawyer/"+value["AssetType"]+".mvc/Summary?oidToken="+value["_oid"]
        value_list.append((value["Number"],value["Scope.Name"],value["Timebox.EndDate"],value["Status.Name"],value["Name"].encode('ascii', 'ignore').decode('ascii'),value["Estimate"],link_url))
    populateBL_indb(value_list)
    logger.info("**** Done *****")

if __name__ == '__main__':
    populateBacklogData()