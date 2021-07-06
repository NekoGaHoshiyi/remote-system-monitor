import os, sys
proj_dir = os.path.dirname(os.getcwd())
sys.path.append(proj_dir)
import subprocess
import redis
# import logging.config
import re
# from conf import log_setting
import time
import datetime
import json
import socket
import psutil
import shutil

# log_file_name = "memory_metrics"
# logging.config.dictConfig(log_setting(log_file_name))
# logger = logging.getLogger(log_file_name)
redis_client = redis.StrictRedis(host='192.168.1.1', port=9096, db=7, decode_responses=True)
cpu_busy = 0.8
cpu_busy_time = 30
memory_busy = 0.8
swap_occur = 0.1
swap_occur_time = 10
redis_mem = 1024
memory_out_time = 10


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def run_cmd(cmd_str):
    process = subprocess.Popen(cmd_str.split(), stdout=subprocess.PIPE, encoding="utf-8")
    output, _ = process.communicate()
    return output


def merge(dict1, dict2):
    res = {**dict1, **dict2}
    return res


def dic_add_to_df(df, dic):
    print('append')
    df = df.append(dic, ignore_index=True)
    return df


def get_metrics_info():
    info = {}
    topline = f"top -bi -n 2 -d 0.01"
    time.sleep(0.02)
    output = run_cmd(topline)
    #output = os.popen(topline).read().split()[2]
    # It only contains top,Tasks,%Cpu,KiB Mem,KiB Swap
    # ['top - 13:17:35 up 22 days,  3:37,  6 users,  load average: 0.45, 0.63, 0.70',
    #  'Tasks: 1647 total,   2 running, 1304 sleeping,   1 stopped,   2 zombie',
    #  '%Cpu(s):  1.8 us,  0.4 sy,  0.0 ni, 97.7 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st',
    #  'KiB Mem : 13165443+total, 12656956 free, 18846780 used, 10015069+buff/cache',
    #  'KiB Swap: 12800000+total, 12176540+free,  6234592 used. 11092016+avail Mem ']
    outputlist = output.split('\n')[:5]
    #print(outputlist[2])
    # its digit is the load percentage,so /100 to get the value (0, 1)
    # cpu_ratio = (100 - float(re.search('(\d{2}\.\d)\sid', outputlist[2]).group(1)))/100
    cpu_ratio = float(psutil.cpu_percent())/100
    # cpu_ratio = round(float(os.popen('''grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage }' ''').readline()),2)
    memtotal = float(re.search('(\d+.)total', outputlist[3]).group(1).replace('+', '0'))/1024/1024
    memused = float(re.search('(\d+.)used', outputlist[3]).group(1).replace('+', '0'))/1024/1024
    mem_ratio = memused / memtotal
    swaptotal = float(re.search('(\d+.)total', outputlist[4]).group(1).replace('+', '0'))/1024/1024
    swapused = float(re.search('(\d+.)used', outputlist[4]).group(1).replace('+', '0'))/1024/1024
    swap_ratio = swapused / swaptotal
    info['cpu_ratio'] = round(cpu_ratio, 2)
    info['memtotal'] = round(memtotal, 2)
    info['memused'] = round(memused, 2)
    info['mem_ratio'] = round(mem_ratio, 2)
    info['swaptotal'] = round(swaptotal, 2)
    info['swapused'] = round(swapused, 2)
    info['swap_ratio'] = round(swap_ratio, 2)
    return info

# delete history logs by UTCsecs, it deletes 7 days older logs dir
def delete_log_date_dir(utcsecs):
    storedays = 7
    if os.path.exists('./logs'):
        pass
    else:
        os.mkdir('./logs')
    logs_dates = os.listdir('./logs')
    log_date_dir = {}
    if logs_dates:
        for log_date in logs_dates:
            log_date_str = log_date.split('_')[0]
            date_time = datetime.datetime.strptime(log_date_str, '%Y-%m-%d')
            date_time_secs = time.mktime(date_time.timetuple())
            if date_time_secs + 60*60*24*storedays < utcsecs:
                shutil.rmtree('./logs/' + log_date)

def get_log(host, period = 1):
    queue = []
    ip = get_ip()
    redis_client.delete(ip+"_metrics_info")
    if os.path.exists('./logs'):
        pass
    else:
        os.mkdir('./logs')
    # use countsec to delete the log dir by day
    cpu_check, mem_check, swap_check, countsec = 0, 0, 0, 1
    while True:
        cmd = f"redis-cli -h {host} -p 9099 info"
        output = run_cmd(cmd)
        redis_info = {
            "used_memory_human":re.search("used_memory_human:(.*)", output).group(1),
            "used_memory_rss_human":re.search("used_memory_rss_human:(.*)", output).group(1),
            "mem_fragmentation_ratio":re.search("mem_fragmentation_ratio:(.*)", output).group(1),
            "rejected_connections":re.search("rejected_connections:(.*)", output).group(1),
        }

        # call the get metrics func
        metrics_info = get_metrics_info()

        row_info = merge(redis_info, metrics_info)

        q_names = [
            "q_write",
            "q_split",
            "q_concat",
            "q_clf",
            "q_save_res",
            "q_save_events",
            "q_save_imgs",
            "q_basecall",
            "q_single_read_basecall"
        ]
        pending_num_list = [redis_client.llen(q_name) for q_name in q_names]

        for q_name, pending_num in zip(q_names, pending_num_list):
            if pending_num != 0:
                row_info[q_name] = pending_num
        #print(row_info)
        # time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        ctime = time.time()
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ctime))
        date_str = time.strftime("%Y-%m-%d", time.localtime(ctime))
        hour_str = time.strftime("%H", time.localtime(ctime))
        if len(queue) == period*60:
            del_time_str = queue.pop()
            redis_client.hdel(ip+"_metrics_info", del_time_str)
        # df = dic_add_to_df(df, row_info)
        # print(df)
        #df_to_redis(df, redis_client)
        #print(df.to_msgpack())
        redis_client.hset(ip+"_metrics_info", time_str, json.dumps(row_info))
        if row_info['cpu_ratio'] > cpu_busy:
            cpu_check += 1
        if row_info['mem_ratio'] > memory_busy:
            mem_check += 1
        if row_info['swap_ratio'] > swap_occur:
            swap_check += 1
        if_cpu_busy = (cpu_check > cpu_busy_time)
        if_mem_busy = (mem_check > memory_out_time)
        if_swap_abnormal = (swap_check > swap_occur_time)
        alert_info = {}
        if if_cpu_busy or if_mem_busy or if_swap_abnormal:
            alert_info['if_cpu_busy'] = if_cpu_busy
            alert_info['if_mem_busy'] = if_mem_busy
            alert_info['if_swap_abnormal'] = if_swap_abnormal
            redis_client.hset(ip + "_alert_info", time_str, json.dumps(alert_info))
        if if_cpu_busy:
            cpu_check = 0
        if if_mem_busy:
            mem_check = 0
        if if_swap_abnormal:
            swap_check = 0
        queue.insert(0, time_str)
        if os.path.exists('./logs/'+date_str+'_metrics'):
            pass
        else:
            os.mkdir('./logs/'+date_str+'_metrics')
        with open('./logs/' + date_str + '_metrics/' + hour_str + '.log', 'a', encoding='utf-8') as wa:
            wa.write(json.dumps({time_str: row_info}) + '\n')
        if alert_info:
            with open('./logs/' + date_str + '_metrics/alert.log', 'a', encoding='utf-8') as walert:
                walert.write(json.dumps({time_str: alert_info}) + '\n')
        another_day_secs = countsec % (60*60*24)
        if another_day_secs == 0:
            delete_log_date_dir(ctime)
        countsec = another_day_secs + 1
        print(time_str)
        time.sleep(1)
if __name__ == '__main__':
    # period units is minutes
    get_log('localhost', period=20)
    # while True:
    #     time.sleep(1)
    #     print(get_metrics_info())
