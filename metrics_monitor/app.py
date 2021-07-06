import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from web_front.pages.main_children import get_children, get_children_old
from web_front.callback.call_back import register_callbacks
# df = px.data.gapminder()
# all_continents = df.continent.unique()

#df = pd.read_csv('monitor_demo.csv')

app = dash.Dash(__name__)

app.title = "Monitor Metrics"
app.layout = html.Div(children=get_children())
register_callbacks(app)

# @app.callback(
#     Output("line-chart", "figure"),
#     [Input("checklist", "value")])
# def update_line_chart(continents):
#     mask = df.continent.isin(continents)
#     fig = px.line(df[mask],
#         x="year", y="lifeExp", color='country')
#     return fig


if __name__ == "__main__":
    app.run_server(host='0.0.0.0', port=8788, debug=False)
