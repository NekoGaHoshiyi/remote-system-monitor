import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
from core.auto_report_status import get_ip
from simulate_monitor_df import get_df_by_ip
from web_front.callback.monitor_change_callback import redis_get_ip, decide_server
from simulate_monitor_df import redis_client
import logging.config
from conf import log_setting
import time


log_file_name = "check_if_online"
logging.config.dictConfig(log_setting(log_file_name))
logger_if_on = logging.getLogger(log_file_name)

# return many graphs like this
# [
#     dcc.Graph(id="line-chart", figure=px.line(df,
#         x="Time", y="Occupancy", color="Performance Metrics", hover_data=["used_memory_human", "used_memory_rss_human", "queue_size"])),
# ]
# offline test
#df = pd.read_csv('monitor_demo.csv')

def get_pc_list(redis_get_ip, redis_client):
    computers = redis_get_ip.hgetall("devices")
    hostnames, ips, select = [], [], []
    for hostname, ip in computers.items():
        res = redis_client.hgetall(ip + '_metrics_info')
        # if_online = os.system(f"ping -c 1 {ip}")
        try:
            if_on = decide_server(ip)
            logger_if_on.info(f"{hostname}-{ip} is reachable")
        except:
            if_on = False
            logger_if_on.info(f"{hostname}-{ip} is unreachable in a limited time period")
        if res and if_on:
            select.append(hostname + '_' + ip)
    return select
def get_children():
    ctime = time.time()
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ctime))
    option = get_pc_list(redis_get_ip, redis_client)
    Headtitle = html.Div([
        html.H1(children="Monitor Remotes Performance Metrics", style={"text-align": "center"}),
        html.P(children="Online: 0, Offline: 0, Busy: 0, Abnormal:0", id="status_num"),
        dcc.Interval(
            id='interval-get-status',
            interval=10 * 1000,  # in milliseconds
            n_intervals=0
        ),
    ])
    splitline = html.Hr()
    graphs = []

    single_graph = html.Div(className='graph_container_big', children=[
        dcc.Interval(
            id=f'interval-component',
            interval=1 * 1000,  # in milliseconds
            n_intervals=0
        ),
        html.H5(className="inline", children="　Select Machine:　"),
        #html.P(className="inline", children="　start_time:　"),
        dcc.Dropdown(
            id="select_machine",
            options=[{"label": i, "value": i} for i in option],
            value=option[0],
            className="dcc_dropdown",
            clearable=False,
        ),
        # html.P(id=f"single_status", children="　　IP:Unknown　　　Status: Unknown",
        #        style={"text-align": "left", "color": "green"}),
        dcc.Graph(id=f"line-chart", className="line_chart_one_big", figure=px.line()),
        html.P(className="inline", children="　start_time:　"),
        dcc.Input(value=time_str, className="time_input",
                  id=f"start_time"),
        # html.P(className="inline", children="　"),
        html.P(className="inline", children="end_time:　"),
        dcc.Input(value=time_str, className="time_input",
                  id=f"end_time"),
        html.Button(children="Get/Restore", className="refreshbtn", id=f"btn_get"),
        html.Div(children=[
            dcc.Input(value='',
                      id=f"start_time_hidden"),
            # this hidden textarea is used to change "realtime" or "show lines by time period"
            dcc.Input(value='',
                      id=f"end_time_hidden"),
        ], hidden=True),
        html.Br(),
        html.Br(),
        html.P(className="inline", children="　Realtime Monitoring:　"),
        dcc.Input(value='True',
                  id=f"if_realtime", disabled=True),
    ]
                            )
    # graphs.append(interval)
    clear_alert_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ctime-60*60*24))
    logs_div = html.Div(
        children=[
            dcc.Interval(
                id='interval-get-alert',
                interval=1 * 1000,  # in milliseconds
                n_intervals=0
            ),
            html.H4("Alert Notes　", className="inline_red"),
            html.Br(),
            dcc.Input(value=clear_alert_time, className="clear_alert_time",
                      id=f"clear_alert_by_time"),
            html.Div(children=[dcc.Input(value=clear_alert_time,
                      id=f"clear_alert_by_time_hide")], hidden=True),
            html.Button(children="Clear Alert", className="clear_alert_btn", id="clear_alert_btn"),
            html.Div(children=[], id="get_alert_logs"),
        ],
        className="logs_div",
    )
    graphs.append(single_graph)
    graphs.append(logs_div)
    graphDiv = html.Div(children=graphs, className="graph_div")
    return [Headtitle, splitline, graphDiv]




def get_children_old():
    ctime = time.time()
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ctime))
    N = 30
    Headtitle = html.Div([
        html.H1(children="Monitor Remotes Performance Metrics", style={"text-align": "center"}),
        html.P(children="Online: 15, Offline: 10, Busy: 3, Abnormal:2"),
    ])
    splitline = html.Hr()
    graphs = []
    for i in range(N):
        index = i + 1
        single_graph = html.Div(className='graph_container', children=[
            dcc.Interval(
            id=f'interval-component{index}',
            interval=1 * 1000,  # in milliseconds
            n_intervals=0
            ),
            html.P(id=f"single_status{index}", children="　　IP:Unknown　　　Status: Unknown",
                   style={"text-align": "left", "color": "green"}),
            dcc.Graph(id=f"line-chart{index}", className="line_chart_one", figure=px.line()),
            html.P(className="inline", children="　start_time:　"),
            dcc.Input(value=time_str, className="time_input",
                          id=f"start_time{index}"),
            #html.P(className="inline", children="　"),
            html.P(className="inline", children="end_time:　"),
            dcc.Input(value=time_str, className="time_input",
                          id=f"end_time{index}"),
            html.Button(children="Get/Restore", className="refreshbtn", id=f"btn_get_{index}"),
            html.Div(children=[
                dcc.Input(value='',
                          id=f"start_time_hidden_{index}"),
                # this hidden textarea is used to change "realtime" or "show lines by time period"
                dcc.Input(value='',
                          id=f"end_time_hidden_{index}"),
            ], hidden=True),
            html.Br(),
            html.Br(),
            html.P(className="inline", children="　Realtime Monitoring:　"),
            dcc.Input(value='True',
                      id=f"if_realtime_{index}", disabled=True),
            ]
        )
        # graphs.append(interval)
        graphs.append(single_graph)
    graphDiv = html.Div(children=graphs)
    return [Headtitle, splitline, graphDiv]
