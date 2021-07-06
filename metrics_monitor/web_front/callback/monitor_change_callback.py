import redis
from simulate_monitor_df import redis_client
import os
import platform
import time
import timeout_decorator



@timeout_decorator.timeout(0.02)
def decide_server(IP):
    cmd_str = f"nmap {IP} -PN -p ssh | egrep 'open|closed|filtered'"
    visit_IP = os.popen(cmd_str)
    # 读取结果
    result = visit_IP.read()
    # 关闭os.popen()
    visit_IP.close()
    # 判断IP是否在线
    if 'open' in result:
        return True
    else:
        return False
@timeout_decorator.timeout(0.02)
def decide_server_by_ping(IP):
    # 获取操作系统
    sys = platform.system()
    # IP地址
    # IP = "www.baidu.com"
    #print(sys)

    if sys == "Windows":
        # 打开一个管道ping IP地址
        visit_IP = os.popen('ping -n 1 %s' % IP)
        # 读取结果
        result = visit_IP.read()
        # 关闭os.popen()
        visit_IP.close()
        # 判断IP是否在线
        if 'TTL' in result:
            return True
        else:
            return False
    elif sys == "Linux":
        visit_IP = os.popen('ping -n -c 1 %s' % IP)
        result = visit_IP.read()
        visit_IP.close()
        if 'ttl' in result:
            return True
        else:
            return False
    else:
        print("Error")




redis_get_ip = redis.StrictRedis(host='192.168.1.1', port=9096, db=8, decode_responses=True)
computers = redis_get_ip.hgetall("devices")
hostnames, ips = [], []
for hostname, ip in computers.items():
    res = redis_client.hgetall(ip + '_metrics_info')
    # if_online = os.system(f"ping -c 1 {ip}")
    #if_on = decide_server(ip)
    # print(res, if_on)
    if res:
        hostnames.append(hostname)
        ips.append(ip)

py_head = '''import time


from dash.dependencies import Input, Output
import logging.config
from conf import log_setting
from simulate_monitor_df import get_df_by_ip
import plotly.express as px
from core.auto_report_status import get_ip


log_file_name = "web_front"
logging.config.dictConfig(log_setting(log_file_name))
logger = logging.getLogger(log_file_name)
period = 10


def register_callbacks(app):
'''

call_back_model = '''    @app.callback(Output("if_realtime_{}", "value"),
                  [Input('btn_get_{}', 'n_clicks')],)
    def update_realtime_false(n_clicks):
        if n_clicks == None:
            return "True"
        if int(n_clicks) % 2 == 0:
            return "True"
        else:
            return "False"

    @app.callback(Output("interval-component{}", "interval"),
                  [Input("if_realtime_{}", "value")], )
    def update_interval_disabled(value):
        if value == 'True':
            return 1 * 1000
        else:
            return 20 * 1000


    # refreshed by interval
    # Input("interval-component", "n_intervals"),
    @app.callback([Output("line-chart{}", "figure"),
                   Output("single_status{}", "children")],
                  [Input("if_realtime_{}", "value"),
                   Input("start_time{}", "value"),
                   Input("end_time{}", "value"),
                   Input("interval-component{}", "n_intervals"),])
    # it returns a pxline by realtime redis data
    def update_figure(*inputs):
        if_realtime = inputs[0]
        #print(if_realtime)
        ip = {{ip}}
        df = get_df_by_ip(ip)
        if df.empty:
            return px.line(), f"　　IP:{ip}　　　Status: Good"
        df.sort_values(by=['Time'], ascending=True)
        current_time = time.time()
        cut_time = current_time - period * 60
        cut_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cut_time))
        rdf = df[df['Time'] > cut_time]
        #print(df)
        # px.line(df,
        #         x="Time", y="Occupancy", color="Metrics", line_group="Metrics",
        #         hover_data=["used_memory_human", "used_memory_rss_human"]
        if if_realtime == 'True':
            #return px.line()
            if rdf.empty:
                if df.shape[0] > (period+1) * 60:
                    df = df.head(period*60)
                return px.line(df, x="Time", y="Occupancy", color='Metrics',
                               color_discrete_map={'cpu':'red', 'memory':'green', 'swap':'blue'},
                               hover_data=["used_memory_human", "used_memory_rss_human", "cpu_ratio", "memused"],),\\
                               f"　　IP:{ip}　　　Status: Good"
            else:
                return px.line(rdf, x="Time", y="Occupancy", color='Metrics',
                               color_discrete_map={'cpu': 'red', 'memory': 'green', 'swap': 'blue'},
                               hover_data=["used_memory_human", "used_memory_rss_human", "cpu_ratio", "memused"], ),\\
                               f"　　IP:{ip}　　　Status: Good"
        else:
            print('change')
            start_time = inputs[1]
            end_time = inputs[2]
            return px.line(df[(df['Time'] > start_time) & (df['Time'] < end_time)], x="Time", y="Occupancy", color='Metrics',
                           color_discrete_map={'cpu':'red', 'memory':'green', 'swap':'blue'},
                           hover_data=["used_memory_human", "used_memory_rss_human", "cpu_ratio", "memused"],),\\
                           f"　　IP:{ip}　　　Status: Good"
'''

gen_callback = open('./callback.py', 'w', encoding='utf-8')
gen_callback.write(py_head)
for index, ip in enumerate(ips):
    one_ip_callback = call_back_model.replace("{}", str(index + 1)).replace('{{ip}}', f'"{ip}"')
    gen_callback.write(one_ip_callback)
gen_callback.close()