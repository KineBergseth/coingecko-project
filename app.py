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


# id, symbol, name, image, current_price, market_cap, market_cap_rank, total volume?, high_24h, low_24h,
# price_change_24h, price,change,percentage_24h, market_cap_change_24h, market_cap_change_percentage_24h,
# circulating_supply, ath, ath_change_percentage

def get_coin(id='bitcoin'):
    return cg.get_coin_by_id(id)


#print(get_coin())


def get_data():
    data = cg.get_coins_markets(vs_currency='usd')
    df = pd.DataFrame(data)
    df.to_csv(r'data.csv')
    df.to_json(r'data.json')
    return df


print(get_data().loc[1])


# get data about a crypto currency for a specific date
def get_price_date(id, date):
    data = cg.get_coin_history_by_id(id, date)
    price = data['market_data']['current_price']['usd']  # kanskje ikke verdens beste løsning, men funker :P
    return price


# get history of a crypto currency's price
# 1 day will show data-points for each minute, 1 or more days will show hourly datapoints
# intervals higher than 90 days will show daily data
def get_price_history(coin, days):
    # get market_chart data from last x number of days
    price_history = cg.get_coin_market_chart_by_id(coin, "usd", days)
    # legger til alle timestamps i liste
    timestamps = [price[0] for price in price_history['prices']]
    dates = [datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S') for timestamp in timestamps]
    prices = [price[1] for price in price_history['prices']]
    # get lowest and highest price during the time interval
    historic_low = min([price[1] for price in price_history['prices']])
    historic_high = max([price[1] for price in price_history['prices']])
    # return coin, date-interval, prices, and historic low and high price
    return dates, prices, historic_low, historic_high
