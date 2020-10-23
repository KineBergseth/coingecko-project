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
import json

# Python3 wrapper around the CoinGecko API
cg = CoinGeckoAPI()


# fetches data about a specific coin
def get_coin(coin_id='bitcoin'):
    return cg.get_coin_by_id(id)


# print(get_coin())

# fetches lots of data about all coins
def get_data():
    data = cg.get_coins_markets(vs_currency='usd')
    df = pd.DataFrame(data)
    df.drop(['image', 'max_supply', 'fully_diluted_valuation', 'roi'], axis=1, inplace=True)
    df.to_csv(r'data.csv')
    return df


print(get_data().loc[1])


# get data about a crypto currency for a specific date
def get_price_date(coin_id, date):
    data = cg.get_coin_history_by_id(coin_id, date)
    price = data['market_data']['current_price']['usd']  # kanskje ikke verdens beste løsning, men funker :P
    return price


# get history of a crypto currency's price
# 1 day will show data-points for each minute, 1 or more days will show hourly datapoints
# intervals higher than 90 days will show daily data
def get_price_history(coin_id, days):
    # get market_chart data from last x number of days
    price_history = cg.get_coin_market_chart_by_id(coin_id, "usd", days)
    # add timestamps to list
    timestamps = [price[0] for price in price_history['prices']]
    dates = [datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S') for timestamp in timestamps]
    prices = [price[1] for price in price_history['prices']]
    # get lowest and highest price during the time interval
    historic_low = min([price[1] for price in price_history['prices']])
    historic_high = max([price[1] for price in price_history['prices']])
    # return coin, date-interval, prices, and historic low and high price
    return dates, prices, historic_low, historic_high


# Dash App med plotly
# bruker extern CSS fil, har ikke skrevet den selv btw
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server


# create table and populate with account data
def generate_table():
    return DataTable(
        id='table',
        data=get_data().to_dict('records'),
        columns=[{"name": i, "id": i} for i in get_data().columns],
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


app.layout = html.Div(children=[
    html.Br(),
    html.H1("Crypto stuff",
            style={'text-align': 'center'}),
    generate_table(),
    html.Br(),
])

if __name__ == '__main__':
    app.run_server(debug=True)  # dev tool and hot-reloading hihi
