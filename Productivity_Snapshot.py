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

def getsnapshot_syncdate():
    conn = mysql.connector.connect(host='dbrllasbihamaster.f1tst.rl.com',database='rl_intelligence',user='reporting',password='d4ta!sgo0d')
    cursor = conn.cursor()
    sql = "SELECT sync_date FROM hd_event_sync_queue where event_name='tm_prod_snapshot'"
    cursor.execute(sql)
    data = cursor.fetchone()
    sync_date ="\'"+data[0].strftime('%Y-%m-%d')+"\'"
    logger.info("Prod SnapShot synDate::"+sync_date)
    
    current_date = datetime.now()
    today="\'"+current_date.strftime('%Y-%m-%d')+"\'"
    logger.info("today::"+today)
    filter_value=["Timebox.EndDate>="+sync_date,"Timebox.EndDate<="+today]
    conn.close()
    return filter_value
    
def get_json_data():
    logger.info("Get Sprint Snaphot JSON from Version one api")
    prod_syncdate=getsnapshot_syncdate()
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
    "AssetType",
    "Scope.Schedule.Name",
    "Timebox",
    "Timebox.Name"
    ],
    "filter":prod_syncdate
    }
    print v1PostData
    resp = requests.post("https://www2.v1host.com/RocketLawyer/query.v1",json=v1PostData,auth=('admin','admin'))
    jsonresp = resp.json()
    return jsonresp[0]
    
def populate_sprint_snapshotindb(data):
    query = "INSERT INTO SprintProductivity(id,ProjectName,SprintEndDate,Status,BacklogItemName,EstimatePts,Link,Schedule,SprintName) " \
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) "
    conn = None
    cursor=None
    try:
        logger.info("Establishing DB connection")
        conn = mysql.connector.connect(host='dbrllasbihamaster.f1tst.rl.com',database='technology_metrics',user='reporting',password='d4ta!sgo0d')
        #conn = mysql.connector.connect(host='localhost',database='test',user='root',password='')
        if conn.is_connected():
            logger.info('Connected to MySQL database')
        cursor = conn.cursor()
        cursor.executemany(query,data)
        conn.commit()
        logger.info("SnapShot of Productivity data insertion successful")
    except Error as e:
        conn.rollback()
        logger.debug("Exception occured while inserting SnapShotProductivity data into database")
        logger.error(e)
    finally:
    	if conn:
    	    conn.close()
    	if cursor:
    	    cursor.close()

def populate_sprint_snapshot():
    logger.info("Start populating data for Sprint Snapshot based on last sync date")
    json_val=get_json_data()
    value_list=[]
    for value in json_val:
        if(value["Status.Name"] == None):
            value["Status.Name"] = 'Null'
        id_value=str(value["Timebox"]["_oid"].split(":")[1])+":"+str(value["Number"].split("-")[1])
        #print id_value
        link_url = "https://www2.v1host.com/RocketLawyer/"+value["AssetType"]+".mvc/Summary?oidToken="+value["_oid"]
        value_list.append((id_value,value["Scope.Name"],value["Timebox.EndDate"],value["Status.Name"],value["Name"].encode('ascii', 'ignore').decode('ascii'),value["Estimate"],link_url,value["Scope.Schedule.Name"],value["Timebox.Name"]))
    populate_sprint_snapshotindb(value_list)
    logger.info("****Sprint Productivity Snapshot Done *****")

if __name__ == '__main__':
    populate_sprint_snapshot()