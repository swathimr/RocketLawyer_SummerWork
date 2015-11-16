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

def get_sync_date():
    db = mysql.connector.connect(host='dbrllasbihamaster.f1tst.rl.com',database='rl_intelligence',user='reporting',password='d4ta!sgo0d')
    cursor = db.cursor()
    sql = "SELECT sync_date FROM hd_event_sync_queue where event_name='tm_pagerduty'"
    cursor.execute(sql)
    data = cursor.fetchone()
    sync_date =data[0].strftime('%Y-%m-%dT%H:%M:%S')+"-07"
    logger.info("SyncDate::"+sync_date)
    return sync_date

def get_pagerdutyjson_list():
    logger.info("Get JSON from PagerDuty API's")
    json_response=[]
    since_date=get_sync_date()
    current_date = datetime.now()
    today=current_date.strftime('%Y-%m-%dT%H:%M:%S')+"-07"
    logger.info("today::"+today)
    resp = requests.get("https://rocketlawyer.pagerduty.com/api/v1/incidents?since="+since_date+"&until="+today+"&limit=100&time_zone=Pacific Time (US %26 Canada)",headers={"Authorization":"Token token=Sz6jJJbdVUpxwziuYJHw"})
    json_response = resp.json()
    logger.info(json_response["total"])
    total =json_response["total"]
    offset=100
    if json_response["total"]>100:
        while(total>=00):
            resp = requests.get("https://rocketlawyer.pagerduty.com/api/v1/incidents?since="+since_date+"&until="+today+"&offset="+str(offset)+"&limit=100&time_zone=Pacific Time (US %26 Canada)",headers={"Authorization":"Token token=Sz6jJJbdVUpxwziuYJHw"})
            for incident_pages in resp.json()["incidents"]:
                json_response["incidents"].append(incident_pages)
            total = int(total)-100
            offset=offset+100        
    incident_list=[]
    logger.info("Creating list for insertion")
    for data in json_response["incidents"]:
        resolved_by = None
        description = None
        if "description" in data["trigger_summary_data"]:
            description=data["trigger_summary_data"]["description"]
        else:
            description=data["trigger_summary_data"]["subject"]
        if "resolved_by_user" in data:
            if data["resolved_by_user"]!= None:
                resolved_by=data["resolved_by_user"]["name"]
            else:
                resolved_by="None"
        d=data["created_on"]
        d=d[:-6]+"Z"
        created_date=datetime.strptime(d,"%Y-%m-%dT%H:%M:%SZ")
        incident_list.append((data["incident_number"],description,created_date,data["status"],data["html_url"],resolved_by))
    return incident_list
    
def populate_pagerduty_indb():
    data_list = get_pagerdutyjson_list()
    logger.info("Start populating data for PagerDuty to fetch incidents till date")
    query = "INSERT INTO PagerDutyIncidents(IncidentNumber,Description,CreatedDate,Status,URL,ResolvedBy) " \
            "VALUES(%s,%s,%s,%s,%s,%s)" \
            "ON DUPLICATE KEY UPDATE Description=VALUES(Description),CreatedDate=VALUES(CreatedDate),Status=VALUES(Status),"\
            "ResolvedBy=VALUES(ResolvedBy)"
    conn = None
    cursor=None
    try:
        logger.info("Establishing DB connection")
        conn = mysql.connector.connect(host='dbrllasbihamaster.f1tst.rl.com',database='technology_metrics',user='reporting',password='d4ta!sgo0d')
        if conn.is_connected():
            logger.info('Connected to MySQL database')
        cursor = conn.cursor()
        logger.info("Inserting PagerDuty data into database")
        cursor.executemany(query,data_list)
        conn.commit()
        logger.info("****Pager Duty data insertion successful***")
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
    populate_pagerduty_indb()