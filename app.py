import requests
from datetime import date
from pycoingecko import CoinGeckoAPI  # https://github.com/man-c/pycoingecko
from datetime import datetime
import pandas as pd
from dash import Dash
import dash_core_components as dcc
import dash_html_components as html
from dash_table import DataTable
from dash.dependencies import Input, Output, State
from itertools import islice
import json

# Python3 wrapper around the CoinGecko API
cg = CoinGeckoAPI()


# fetches data about a specific coin
def get_coin(coin_id='bitcoin'):
    return cg.get_coin_by_id(coin_id)


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


print(get_data().loc[1])


# get data about a crypto currency for a specific date
def get_price_date(coin_id, chosen_date):
    date_data = cg.get_coin_history_by_id(coin_id, chosen_date)
    price = date_data['market_data']['current_price']['usd']  # kanskje ikke verdens beste løsning, men funker :P
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


# Dash App user interface
# bruker extern CSS fil, har ikke skrevet den selv btw
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server


# create table and populate with crypto data
def generate_table():
    return DataTable(
        id='table',
        data=get_data()[0:10].to_dict('records'),  # only show 10/100 rows
        columns=[{"name": item, "id": item} for item in get_data().columns],
        filter_action='native',
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


# generate slider where user can select input
def generate_slider():
    return html.Div(dcc.Slider(
        id='slider',
        min=1,
        max=360,
        value=30,
        step=1,
        marks={
            7: '1 week',
            30: '1 month',
            90: 'Quarter',
            180: '6 months',
            360: '1 year'
        }
    ),
        style={'width': '80%', 'padding': '20px 10px 10px 20px'},
    )


def coin_info():
    return html.Div(html.Img(src=('https://assets.coingecko.com/coins/images/1/large/bitcoin.png?1547033579')))


# description

# summary table
app.layout = html.Div(children=[
    html.Br(),
    html.H1("Crypto stuff",
            style={'text-align': 'center'}),
    generate_table(),
    html.Br(),
    coin_info(),
    html.Br(),
    html.Div([generate_ddl_coins(),
              generate_ddl_currencies()]),
    html.Div(id='graph'),
    generate_slider(),
    html.Br(),
    dcc.Tabs(id='tabs-example', value='tab-1', children=[
        dcc.Tab(label='Tab one', value='tab-1'),
        dcc.Tab(label='Tab two', value='tab-2'),
        dcc.Tab(label='Tab three', value='tab-3'),
    ]),
    html.Div(id='tabs-example-content')
])


# graph - price, market cap


@app.callback(Output('tabs-example-content', 'children'),
              [Input('tabs-example', 'value')])
def render_content(tab):
    if tab == 'tab-1':
        return html.Div([
            html.H3('Tab content 1')
        ])
    elif tab == 'tab-2':
        return html.Div([
            html.H3('Tab content 2')
        ])
    elif tab == 'tab-3':
        return html.Div([
            html.H3('Tab content 3')
        ])


# find data for graph
@app.callback(
    Output('graph', 'children'),
    [Input('input-ddl-coins', 'value'),
     Input('input-ddl-currencies', 'value'),
     Input('slider', 'value')])
def update_graph(coin, currency, days):
    dates, prices, historic_low, historic_high = get_price_history(coin, currency, days)
    return html.Div(dcc.Graph(
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
    )


# start flask server
if __name__ == '__main__':
    app.run_server(debug=True)  # dev tool and hot-reloading hihi
