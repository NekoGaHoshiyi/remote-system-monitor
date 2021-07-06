import json
import time
import dash

from dash.dependencies import Input, Output
import logging.config
from conf import log_setting
from simulate_monitor_df import get_df_by_ip, redis_get_ip, redis_client
from web_front.pages.main_children import get_pc_list
import plotly.express as px
from core.auto_report_status import get_ip
from simulate_monitor_df import get_alerts, get_history_by_utc
import dash_html_components as html
import datetime

log_file_name = "web_front"
logging.config.dictConfig(log_setting(log_file_name))
logger = logging.getLogger(log_file_name)
# ip = get_ip()
period = 10



def register_callbacks(app):
    @app.callback(Output("clear_alert_by_time_hide", "value"),
                  [Input('clear_alert_by_time', 'value'),
                   Input('clear_alert_btn', 'n_clicks')])
    def clear_alert_by_time(*inputs):
        clear_alert_time = inputs[0]
        clear_alert_datetime = datetime.datetime.strptime(clear_alert_time, "%Y-%m-%d %H:%M:%S")
        clear_alert_secs = time.mktime(clear_alert_datetime.timetuple())
        changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
        if 'clear_alert_btn' in changed_id:
            computers = redis_get_ip.hgetall("devices")
            for hostname, ip in computers.items():
                res = redis_client.hgetall(ip + '_alert_info')
                # print(type(res))
                for key_time, value in res.items():
                    key_datetime = datetime.datetime.strptime(key_time, "%Y-%m-%d %H:%M:%S")
                    key_secs = time.mktime(key_datetime.timetuple())
                    if clear_alert_secs > key_secs:
                        redis_client.hdel(ip + '_alert_info', key_time)
        return clear_alert_time

    @app.callback(Output("status_num", "children"),
                  [Input('interval-get-status', 'n_intervals')], )
    def update_status_num(n_intervals):
        # content = "Online: {{}}, Offline: {{}}, Busy: {{}}, Abnormal:{{}}"
        computers = redis_get_ip.hgetall("devices")
        total = len(computers)
        pc_list = get_pc_list(redis_get_ip, redis_client)
        online_num = len(pc_list)
        busy, abnormal = 0, 0
        for hostname, ip in computers.items():
            res = redis_client.hgetall(ip + '_alert_info')
            # print(type(res))
            for key_time, value in res.items():
                key_datetime = datetime.datetime.strptime(key_time, "%Y-%m-%d %H:%M:%S")
                key_secs = time.mktime(key_datetime.timetuple())
                ctime = time.time()
                if ctime - key_secs > 60*period:
                    continue
                # print(value)
                # value = value.replace("true", True)
                value = json.loads(value)
                # print(type(value))
                # print('---', value)
                if value["if_cpu_busy"] == True:
                    busy += 1
                    break
                elif value["if_mem_busy"] == True or value["if_swap_abnormal"] == True:
                    abnormal += 1
                    break
        content = f"Online: {online_num}, Offline: {total - online_num}, Busy: {busy}, Abnormal:{abnormal}"
        return content
    @app.callback(Output("get_alert_logs", "children"),
                  [Input('interval-get-alert', 'n_intervals')], )
    def update_realtime_alert(n_intervals):
        content = []
        alert_list = get_alerts()
        for alert in alert_list:
            host_ip = alert[0]
            alert_infos = alert[1]
            show_host_ip = html.H5(children=host_ip)
            content.append(show_host_ip)
            content += [html.P(className="alert_item", children=f"{alert_info}----{alert_infos[alert_info]}"
                               .replace('{', '').replace('}', '')) for alert_info in alert_infos]
        return content
    # not refreshd by interval
    @app.callback(Output("if_realtime", "value"),
                  [Input('btn_get', 'n_clicks')],)
    def update_realtime_false(n_clicks):
        if n_clicks == None:
            return "True"
        if int(n_clicks) % 2 == 0:
            return "True"
        else:
            return "False"

    @app.callback(Output("interval-component", "interval"),
                  [Input("if_realtime", "value")], )
    def update_interval_disabled(value):
        if value == 'True':
            return 1 * 1000
        else:
            return 20 * 1000

    # refreshed by interval
    # Input("interval-component", "n_intervals"),
    @app.callback(Output("line-chart", "figure"),
                  [Input("if_realtime", "value"),
                   Input("start_time", "value"),
                   Input("end_time", "value"),
                   Input("select_machine", "value"),
                   Input("interval-component", "n_intervals"),])
    # it returns a pxline by realtime redis data
    def update_figure(*inputs):
        if_realtime = inputs[0]
        ip = inputs[3].split('_')[1]
        df = get_df_by_ip(ip)
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
            if df.empty:
                return px.line()
            if rdf.empty:
                if df.shape[0] > (period+1) * 60:
                    df = df.head(period*60)
                return px.line(df, x="Time", y="Occupancy", color='Metrics',
                               color_discrete_map={'cpu':'red', 'memory':'green', 'swap':'blue'},
                               hover_data=["used_memory_human", "used_memory_rss_human", "cpu_ratio", "memused"],)
            else:
                return px.line(rdf, x="Time", y="Occupancy", color='Metrics',
                               color_discrete_map={'cpu': 'red', 'memory': 'green', 'swap': 'blue'},
                               hover_data=["used_memory_human", "used_memory_rss_human", "cpu_ratio", "memused"], )
        else:
            # print('change')
            start_time = inputs[1]
            end_time = inputs[2]
            # if df.empty:
            start_datetime = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            start_secs = time.mktime(start_datetime.timetuple())
            end_datetime = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            end_secs = time.mktime(end_datetime.timetuple())
            df = get_history_by_utc(start_secs, end_secs, ip)
            if df.empty:
                return px.line()
            else:
                # print(df)
                return px.line(df, x="Time", y="Occupancy", color='Metrics',
                               color_discrete_map={'cpu': 'red', 'memory': 'green', 'swap': 'blue'},
                               hover_data=["used_memory_human", "used_memory_rss_human", "cpu_ratio", "memused"], )

