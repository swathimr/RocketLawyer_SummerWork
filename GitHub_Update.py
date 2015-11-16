#!/usr/bin/python
# -*- coding: utf-8 -*-
#
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import requests
import json
import logging
import calendar

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_sync_date():
    logger.info("Getting syn date for Github api")
    db = mysql.connector.connect(host='dbrllasbihamaster.f1tst.rl.com',database='rl_intelligence',user='reporting',password='d4ta!sgo0d')
    cursor = db.cursor()
    sql = "SELECT sync_date FROM hd_event_sync_queue where event_name='tm_github'"
    cursor.execute(sql)
    data = cursor.fetchone()
    sync_date =data[0].strftime('%Y-%m-%dT%H:%M:%SZ')
    cursor.close()
    db.close()
    return sync_date
    
def get_All_Repositories():
    logger.info("Creating list to insert into database")
    resp = requests.get("https://api.github.com/orgs/rocketlawyer/repos",headers={"Authorization":"token b69de408a2dc35790d8b775befb61746a80013f4"})
    repo_name = resp.json()
    repo_pages = resp.headers["link"].split(",")[1].split(";")[0]
    length =repo_pages[len(repo_pages)-2]
    for index in range(2,int(length)+1):
        print index
        respnse=requests.get("https://api.github.com/orgs/rocketlawyer/repos?per_page=100&page="+str(index),headers={"Authorization":"token b69de408a2dc35790d8b775befb61746a80013f4"})
        repo_name+=respnse.json()
    data_list=[]
    logger.info("Getting all the commits for all the repositories")
    since_date=get_sync_date()
    for repoval in repo_name:
        commits_json_complete=[]
        logger.info("**********************")
        logger.info(repoval["name"])
        logger.info("**********************")
        repo_geturl=requests.get("https://api.github.com/repos/rocketlawyer/"+repoval["name"]+"/commits?per_page=100&since="+since_date,headers={"Authorization":"token b69de408a2dc35790d8b775befb61746a80013f4"})
        i=2
        reset=True
        if(len(repo_geturl.json())>0 and repo_geturl.status_code==200):
            commits_json_complete+=repo_geturl.json()
            while(reset):
                commits = requests.get("https://api.github.com/repos/rocketlawyer/"+repoval["name"]+"/commits?per_page=100&since="+since_date+"&page="+str(i),headers={"Authorization":"token b69de408a2dc35790d8b775befb61746a80013f4"})
                if(commits.status_code==200):
                    commits_json_complete+=commits.json()
                    i=i+1
                    if not commits.json():
                        reset=False
                        logger.info("Total Number of Commit Pages fetched were"+str(i))
                        logger.info("Value reset to 0")
                        i=0
        if commits_json_complete!=None:
            for commit_values in commits_json_complete:
                d=commit_values["commit"]["committer"]["date"]
                date_convert=datetime.strptime(d,"%Y-%m-%dT%H:%M:%SZ")
                message = commit_values["commit"]["message"].encode('ascii', 'ignore').decode('ascii')
                description = message[:1000] + (message[1000:] and '..')
                data_list.append((repoval["name"],commit_values["commit"]["committer"]["name"],commit_values["commit"]["committer"]["email"],date_convert,description,commit_values["html_url"]))
    logger.info("Created list for insertion")
    return data_list
    
def populate_github_data():
    logger.info("Start populating data for Github based on sync date")
    github_data = get_All_Repositories()
    query = "INSERT INTO GitHubPerformance(RepositoryName,UserName,Email,CommitDate,Message,CommitURL) " \
            "VALUES(%s,%s,%s,%s,%s,%s)"
    conn = None
    cursor=None
    try:
        logger.info("Establishing DB connection")
        conn = mysql.connector.connect(host='dbrllasbihamaster.f1tst.rl.com',database='technology_metrics',user='reporting',password='d4ta!sgo0d')
        if conn.is_connected():
            logger.info('Connected to MySQL database')
        cursor = conn.cursor()
        cursor.executemany(query,github_data)
        conn.commit()
        logger.info("GitHub data insertion successful")
    except Error as e:
        conn.rollback()
        logger.debug("Exception occured while inserting into database")
        logger.error(e)
    finally:
    	if conn:
    	    conn.close()
    	if cursor:
    	    cursor.close()    
    
if __name__ == '__main__':
    populate_github_data()