import requests
from datetime import date
from pycoingecko import CoinGeckoAPI  # https://github.com/man-c/pycoingecko
from datetime import datetime
import pandas as pd
import dash
from dash import Dash
import dash_core_components as dcc
import dash_html_components as html
from dash_table import DataTable
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from itertools import islice
import json

# Python3 wrapper around the CoinGecko API
cg = CoinGeckoAPI()


# get list of all supported currencies
def get_currencies():
    return cg.get_supported_vs_currencies()


# fetches lots of data about all coins
def get_data():
    coin_data = cg.get_coins_markets(vs_currency='usd')
    df = pd.DataFrame(coin_data)
    df.drop(['image', 'max_supply', 'fully_diluted_valuation', 'price_change_24h', 'market_cap_change_24h', 'ath',
             'ath_change_percentage', 'ath_date', 'atl', 'atl_change_percentage', 'atl_date', 'roi'], axis=1,
            inplace=True)
    df.to_csv(r'data.csv')
    return df


# gets data about specific coin
def get_coin_data(coin_id):
    coin_data = cg.get_coin_by_id(coin_id, market_data='true', sparkline='true')
    df = pd.DataFrame.from_dict(coin_data, orient='index')
    df.to_csv(r'coin_data.csv')
    return df


get_coin_data('bitcoin')


# get data about a crypto currency for a specific date
def get_price_date(coin_id, chosen_date):
    date_data = cg.get_coin_history_by_id(coin_id, chosen_date)
    price = date_data['market_data']['current_price']['usd']
    return price


# get history of a crypto currency's price
# 1 day will show data-points for each minute, 1 or more days will show hourly datapoints
# intervals higher than 90 days will show daily data
def get_price_history(coin_id, currency, days):
    # get market_chart data from last x number of days
    price_history = cg.get_coin_market_chart_by_id(coin_id, currency, days)
    # add timestamps to list
    timestamps = [price[0] for price in price_history['prices']]
    dates = [datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S') for timestamp in timestamps]
    prices = [price[1] for price in price_history['prices']]
    # get lowest and highest price during the time interval
    historic_low = min([price[1] for price in price_history['prices']])
    historic_high = max([price[1] for price in price_history['prices']])
    # return coin, date-interval, prices, and historic low and high price
    return dates, prices, historic_low, historic_high


########################################################################################################################
# DASH APP USER INTERFACE
# bruker extern CSS fil, har ikke skrevet den selv btw
# https://codepen.io/chriddyp/pen/bWLwgP.css
# THEMES: https://www.bootstrapcdn.com/bootswatch/
external_stylesheets = [dbc.themes.BOOTSTRAP]
app = Dash(__name__)  # , external_stylesheets=external_stylesheets)

server = app.server


def gen_nav_bar():
    # temporary logo taken from
    # <a href="https://lovepik.com/images/png-coin.html">Coin Png vectors by Lovepik.com</a>
    return dbc.Navbar([
        html.A(
            # Use row and col to control vertical alignment of logo / brand
            dbc.Row(
                [
                    dbc.Col(html.Img(src=app.get_asset_url('logo.png'), height="50px")),
                    dbc.Col(dbc.NavbarBrand("Cryptocurrency dashboard", className="dashboard-nav")),
                ],
                align="center",
                no_gutters=True,
            ),
            # href="https://plot.ly",
        ),
    ],
        color="dark",
        dark=True,
    )


data_columns = ['id', 'symbol', 'Coin', 'Price', 'Mkt Cap', 'tot_volume', 'h24', 'l24', '24h Mkt', 'circulating_supply', 'tot_supply','last update']

# create table and populate with crypto data
def generate_table():
    return DataTable(
        id='table',
        data=get_data()[0:10].to_dict('records'),  # only show 10/100 rows
        columns=[{"name": item, "id": item} for item in get_data().columns],
        sort_action='native',
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{price_change_percentage_24h} < 0',
                    'column_id': 'price_change_percentage_24h',
                },
                'color': 'red'
            },
            {
                'if': {
                    'filter_query': '{price_change_percentage_24h} > 0',
                    'column_id': 'price_change_percentage_24h',
                },
                'color': 'green'
            }
        ]
    )


# create dropdownlist with all coins
def generate_ddl_coins():
    return dcc.Dropdown(
        id="input-ddl-coins",
        options=[{'label': i, 'value': i} for i in get_data()['id']],
        value='bitcoin',
        style=dict(
            width='40%',
        )
    )


# create dropdownlist with all supported currencies
def generate_ddl_currencies():
    return dcc.Dropdown(
        id="input-ddl-currencies",
        options=[{'label': i, 'value': i} for i in get_currencies()],
        value='usd',
        style=dict(
            width='40%',
        )
    )


# create buttons where user can select time interval
def time_buttons():
    return html.Div([
        dbc.ButtonGroup([
            dbc.Button("24h", id="1d"),
            dbc.Button("7d", id="7d"),
            dbc.Button("14d", id="14d"),
            dbc.Button("30d", id="30d", active=True),
            dbc.Button("90d", id="90d"),
            dbc.Button("180d", id="180d"),
            dbc.Button("360d", id="360d"),
        ])
    ])


# Generate tabs
def generate_tabs():
    return dcc.Tabs([
        dcc.Tab(label='Overview', children=[
            html.H3('Bitcoin overview'),
            html.Div(id='coin_info'),
            html.Div(id='coin_info_bar'),
            html.Div(id='coin_summary'),
        ]),
        dcc.Tab(label='Graphs', children=[
            html.Div([
                html.H3('Bitcoin - US Dollar Chart (BTC/USD) '),
                time_buttons(),
                html.Div(id='day_value', style={'display': 'none'}),
                html.Div(id='demo'),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(id="info1text"), html.P("Info")],
                                    id="info1",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="info2Text"), html.P("Info")],
                                    id="info2",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="info3Text"), html.P("Info")],
                                    id="info3",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="info4Text"), html.P("Info")],
                                    id="info4",
                                    className="mini_container",
                                ),
                            ],
                            id="info-container",
                            className="row container-display",
                        ),
                        html.Div(id='graph',
                                 className="pretty_container"),
                    ],
                    id="right-column",
                    className="eight columns",
                ),
            ])
        ]),
        dcc.Tab(label='Historical data', children=[
            html.H3('Tab content 3')
        ])
    ])


# Define layout
app.layout = html.Div(children=[
    gen_nav_bar(),
    html.Br(),
    html.H1("Top 10 Coins by Market Capitalization",
            style={'text-align': 'center'}),
    generate_table(),
    html.Br(),
    html.Br(),
    html.Div([generate_ddl_coins(),
              generate_ddl_currencies()
              ]),
    html.Br(),
    generate_tabs()
])


# this callback uses dash.callback_context to figure out which button
# was clicked most recently. it then updates the "active" style of the
# buttons appropriately, and sets some output. it could be split into
# multiple callbacks if you prefer.
@app.callback(
    [
        Output("day_value", "children"),
        Output("1d", "active"),
        Output("7d", "active"),
        Output("14d", "active"),
        Output("30d", "active"),
        Output("90d", "active"),
        Output("180d", "active"),
        Output("360d", "active"),
    ],
    [
        Input("1d", "n_clicks"),
        Input("7d", "n_clicks"),
        Input("14d", "n_clicks"),
        Input("30d", "n_clicks"),
        Input("90d", "n_clicks"),
        Input("180d", "n_clicks"),
        Input("360d", "n_clicks"),
    ]
)
def toggle_buttons(n_1d, n_7d, n_14d, n_30d, n_90d, n_180d, n_360d):
    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if not any([n_1d, n_7d, n_14d, n_30d, n_90d, n_180d, n_360d]):
        return "Nothing selected yet", False, False, False, False, False, False, False
    elif button_id == "1d":
        return "1", True, False, False, False, False, False, False
    elif button_id == "7d":
        return "7", False, True, False, False, False, False, False
    elif button_id == "14d":
        return "14", False, False, False, False, False, False, False
    elif button_id == "30d":
        return "30", False, False, False, True, False, False, False
    elif button_id == "90d":
        return "90", False, False, False, False, True, False, False
    elif button_id == "180d":
        return "180", False, False, False, False, False, True, False
    elif button_id == "360d":
        return "360", False, False, False, False, False, False, True


# find data for graph
@app.callback(
    Output('graph', 'children'),
    [Input('input-ddl-coins', 'value'),
     Input('input-ddl-currencies', 'value'),
     Input('day_value', 'children')])
def update_graph(coin, currency, days):
    dates, prices, historic_low, historic_high = get_price_history(coin, currency, days)
    return dcc.Graph(
        id='figure',
        figure={
            'data': [{
                'x': dates,
                'y': prices,
                'type': 'scatter',
                'name': coin + 'price'
            }
            ],
            'layout': {
                'title': coin + ' Last ' + str(days) + ' Days',
                'xaxis': {
                    'title': 'Date',
                    'showgrid': True,
                },
                'yaxis': {
                    'title': 'Price ' + currency,
                    'showgrid': True,
                }
            }
        },
        config={
            'displayModeBar': False
        }
    )

# combine name and value and put them in a HTML element
def get_top_bar_cell(cellTitle, cellValue):
    return html.Div(
        className="two-col",
        children=[
            html.P(className="p-top-bar", children=cellTitle),
            html.P(id=cellTitle, className="display-none", children=cellValue),
            # TODO make numbers readeble with currency symbol, commas % etccc, make function for this hihi
        ],
    )


# Returns Top cell bar for header area
@app.callback(
    Output('coin_info_bar', 'children'),
    [Input('input-ddl-coins', 'value'),
     Input('input-ddl-currencies', 'value')]
)
# Returns HTML Top Bar with coin info for app layout
def get_top_bar(coin_id, currency):
    data = get_coin_data(coin_id)
    name = data[0]['name']
    symbol = data[0]['symbol']
    homepage = data[0]['links']['homepage'][0]
    mc_rank = data[0]['market_cap_rank']
    current_price = data[0]['market_data']['current_price'][currency]
    pc_24h = data[0]['market_data']['price_change_percentage_24h']
    market_cap = data[0]['market_data']['market_cap'][currency]
    low_24h = data[0]['market_data']['low_24h'][currency]
    high_24h = data[0]['market_data']['high_24h'][currency]
    circulating_supply = data[0]['market_data']['circulating_supply']
    fully_diluted_valuation = data[0]['market_data']['fully_diluted_valuation'][currency]
    max_supply = data[0]['market_data']['max_supply']
    # data[0]['links']['blockchain_site']

    return [
        html.Img(src=(data[0]['image']['thumb'])),
        get_top_bar_cell("Name", name),
        get_top_bar_cell("Symbol", symbol),
        get_top_bar_cell("Homepage", homepage),
        get_top_bar_cell("Market cap rank", mc_rank),
        get_top_bar_cell("Current_price", current_price),
        get_top_bar_cell("Price change 24h", pc_24h),
        get_top_bar_cell("Market cap", market_cap),
        get_top_bar_cell("Low 24h", low_24h),
        get_top_bar_cell("High 24h", high_24h),
        get_top_bar_cell("Circulation supply", circulating_supply),
        get_top_bar_cell("Fully diluted valuation", fully_diluted_valuation),
        get_top_bar_cell("Max supply", max_supply),
    ]

    # html.Img(src=(data[0]['image']['thumb'])),
    # html.P(data[0]['symbol']),
    # html.P(data[0]['description']['en']),
    # html.P(data[0]['genesis_date']),
    # html.P(data[0]['market_data']['ath'][currency]),
    # html.P(data[0]['market_data']['ath_change_percentage'][currency]),
    # html.P(data[0]['market_data']['ath_date'][currency]),
    # html.P(data[0]['market_data']['fully_diluted_valuation'][currency]),
    # html.P(data[0]['market_data']['total_volume'][currency]),
    # html.P(data[0]['market_data']['price_change_24h']),
    # html.P(data[0]['market_data']['price_change_percentage_24h']),
    # html.P(data[0]['market_data']['price_change_percentage_7d']),
    # html.P(data[0]['market_data']['price_change_percentage_14d']),
    # html.P(data[0]['market_data']['price_change_percentage_30d']),
    # html.P(data[0]['market_data']['price_change_percentage_60d']),
    # html.P(data[0]['market_data']['price_change_percentage_200d']),
    # html.P(data[0]['market_data']['price_change_percentage_1y']),
    # html.P(data[0]['market_data']['market_cap_change_24h']),
    # html.P(data[0]['market_data']['market_cap_change_percentage_24h']),
    # html.P(data[0]['market_data']['total_supply']),
    # html.P(data[0]['market_data']['max_supply']),
    # html.P(data[0]['market_data']['circulating_supply']),
    # html.P(data[0]['market_data']['last_updated']),
    # html.P(data[0]['links']['homepage'][0]),
    # html.P(data[0]['links']['blockchain_site']),
    # html.P(data[0]['links']['official_forum_url'][0])


# start flask server
if __name__ == '__main__':
    app.run_server(debug=True)  # dev tool and hot-reloading hihi

# TANKER
# NÅR MAN KLIKKER PÅ COIN I TABELL SETTER DEN DROPDOWNLIST TIL DEN VERDIEN?
# graph - price, market cap?
