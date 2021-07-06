import json
import shutil

import redis
import pandas as pd
import numpy as np
import pickle
from core.auto_report_status import get_ip
import time
import subprocess
import os
import timeout_decorator
import datetime




redis_client = redis.StrictRedis(host='192.168.1.1', port=9096, db=7, decode_responses=True)
redis_get_ip = redis.StrictRedis(host='192.168.1.1', port=9096, db=8, decode_responses=True)
period = 20
metrics_num = 3
pd_columns = [
    "used_memory_human",
    "used_memory_rss_human",
    "mem_fragmentation_ratio",
    "rejected_connections",
    "cpu_ratio",
    "memtotal",
    "memused",
    "mem_ratio",
    "swaptotal",
    "swapused",
    "swap_ratio",
    "Occupancy",
    "Metrics",
    "Time"
 ]

def run_cmd(cmd_str):
    process = subprocess.Popen(cmd_str.split(), stdout=subprocess.PIPE, encoding="utf-8")
    output, _ = process.communicate()
    return output

#@timeout_decorator.timeout(3)
def get_remote_logfiles(ip):
    if os.path.exists(f'/home/user/metrics_logs/{ip}'):
        try:
            shutil.rmtree(f"/home/user/metrics_logs/{ip}/logs")
        except:
            pass
    else:
        os.mkdir(f'/home/user/metrics_logs/{ip}')
    remote_dir = '~/multilines_monitor/core/auto_report_metrics/logs'
    local_dir = '/home/user/metrics_logs'
    passwd = 'computersji'
    cmd_str = f"sshpass -p {passwd} scp -r -o 'StrictHostKeyChecking no'  computers@{ip}:{remote_dir} {local_dir}"
    res = os.system(cmd_str)
    time.sleep(1.5)
    logs = os.listdir(f"/home/user/metrics_logs/{ip}")
    #print(logs)
    if 'logs' in logs:
        return True
    else:
        return False

def get_history_by_utc(startsecs, endsecs, ip):
    res = get_remote_logfiles(ip)
    print(res)
    search_logs = f"/home/user/metrics_logs/{ip}/logs"
    # get history from start_time to start_time+period*60 and return
    if endsecs - startsecs > period * 60:
        start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(startsecs))
        end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(startsecs+period*60))
    else:
        start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(startsecs))
        end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(endsecs))
    # start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(startsecs))
    # end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(endsecs))
    print(start_time_str, end_time_str)
    start_date = start_time_str.split(' ')[0]
    start_hour = start_time_str.split(' ')[1].split(':')[0]
    end_date = end_time_str.split(' ')[0]
    end_hour = end_time_str.split(' ')[1].split(':')[0]
    rows = []
    #print(start_date, end_date, start_hour, end_hour)
    if start_hour == end_hour and start_date == end_date:
        with open(f"/home/user/metrics_logs/{ip}/logs/{end_date}_metrics/{end_hour}.log",
                  "r", encoding="utf-8") as read_log:
            readline = read_log.readline().strip()
            while readline:
                # add ratio and Performance Metrics
                readline = json.loads(readline)
                append_rows(readline, rows)
                readline = read_log.readline().strip()
    else:
        with open(f"/home/user/metrics_logs/{ip}/logs/{start_date}_metrics/{start_hour}.log",
                  "r", encoding="utf-8") as read_log:
            readline = read_log.readline().strip()
            while readline:
                # add ratio and Performance Metrics
                readline = json.loads(readline)
                append_rows(readline, rows)
                readline = read_log.readline().strip()
        with open(f"/home/user/metrics_logs/{ip}/logs/{end_date}_metrics/{end_hour}.log",
                  "r", encoding="utf-8") as read_log:
            readline = read_log.readline().strip()
            while readline:
                # add ratio and Performance Metrics
                readline = json.loads(readline)
                append_rows(readline, rows)
                readline = read_log.readline().strip()
    #print(rows)
    df = pd.DataFrame(data=rows, columns=pd_columns)
    #df['Time'] = pd.to_datetime(df['Time'])
    df = df[(df['Time'] > start_time_str) & (df['Time'] < end_time_str)]
    df.sort_values(by=['Time', 'Metrics'], ascending=True, inplace=True)
    # print(df)
    # metrics have 3 lines
    if df.shape[0] > period*60*metrics_num:
        return df.head(period*60*metrics_num)
    else:
        return df

def append_rows(data_dic, rows):
    for clock, line in data_dic.items():
        if not isinstance(line, dict):
            line = json.loads(line)
        # add ratio and Performance Metrics
        line['Time'] = clock
        line1 = {**line, "Occupancy": line['cpu_ratio'], "Metrics": "cpu"}
        rows.append(line1)
        line2 = {**line, "Occupancy": line['mem_ratio'], "Metrics": "memory"}
        rows.append(line2)
        line3 = {**line, "Occupancy": line['swap_ratio'], "Metrics": "swap"}
        rows.append(line3)

def get_df_by_ip(ip):
    data = redis_client.hgetall(ip + '_metrics_info')
    data_num = len(data)
    #print(data)
    # if data_num < 3600 * period:
    #     empty_data = np.zeros()
    #     df = pd.DataFrame(index=data_num * metrics_num, columns=pd_columns)
    #     #df = pd.DataFrame.from_dict(data)
    # else:
    #     df = pd.DataFrame(index=3600*period*metrics_num, columns=pd_columns)
    #     pass
    rows = []
    append_rows(data, rows)
    df = pd.DataFrame(data=rows, columns=pd_columns)
    df['Time'] = pd.to_datetime(df['Time'])
    df.sort_values(by=['Time', 'Metrics'], ascending=True, inplace=True)
    #df.sort_values(by=['Metrics'], ascending=True, inplace=True)
    #print(df)
    return df

def get_simu_df():
    ip = get_ip()
    df = pd.DataFrame(index=None)
    start_time = time.time()
    data = redis_client.hgetall(ip+'_metrics_info')
    end_time = time.time()
    #print(end_time - start_time)
    for clock, line in data.items():
        line = json.loads(line)
        # add ratio and Performance Metrics
        # line['Time'] = time.decode('utf-8')
        line['Time'] = clock
        line1 = {**line, "Occupancy": line['cpu_ratio'], "Metrics":"cpu"}
        df = df.append(line1, ignore_index=True)
        line2 = {**line, "Occupancy": line['mem_ratio'], "Metrics":"memory"}
        df = df.append(line2, ignore_index=True)
        line3 = {**line, "Occupancy": line['mem_fragmentation_ratio'], "Metrics":"redis_mem"}
        df = df.append(line3, ignore_index=True)
        line4 = {**line, "Occupancy": line['swap_ratio'], "Metrics":"swap"}
        df = df.append(line4, ignore_index=True)
        df.sort_values(by=['Time'], ascending=True, inplace=True)
    #print(df)
    return df

def get_alerts():
    computers = redis_get_ip.hgetall("devices")
    alert_list = []
    for hostname, ip in computers.items():
        alert_infos = redis_client.hgetall(ip + "_alert_info")
        if alert_infos:
            alert_list.append((hostname + '_' + ip, alert_infos))
    return alert_list


if __name__ == "__main__":
    #df = get_simu_df()
    #df.to_csv('from_redis.csv')
    # df = get_df_by_ip(get_ip())
    # print(df)
    ip = '192.168.1.1'
    res = get_remote_logfiles(ip)
    print(res)
    start_time = '2021-07-04 15:44:31'
    end_time = '2021-07-05 15:54:31'
    start_datetime = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    start_secs = time.mktime(start_datetime.timetuple())
    end_datetime = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    end_secs = time.mktime(end_datetime.timetuple())
    df = get_history_by_utc(start_secs, end_secs, ip)
    # print(df)