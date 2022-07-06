import os
import asyncio
import discord
from discord.ext import commands,tasks
import json
from bs4 import BeautifulSoup
import requests
import datetime
import yfinance as yf
intents = discord.Intents.default()
intents.members = True

client = commands.Bot(intents=intents, command_prefix='mimi ')

#Getting config datas
conf = open("./config/config.json")
config = json.load(conf)
supported_fiat = ["EUR", "USD", "CAD", "JPY", "GPB", "AUD", "CNY", "INR"]

def get_meta_from_mint():
    url = "https://api.thegraph.com/subgraphs/name/vinnytreasure/treasuremarketplace-fast-prod"
    payload = json.dumps({
        "query": "query getActivity($first: Int!, $skip: Int, $includeListings: Boolean!, $includeSales: Boolean!, $includeBids: Boolean!, $listingFilter: Listing_filter, $listingOrderBy: Listing_orderBy, $bidFilter: Bid_filter, $bidOrderBy: Bid_orderBy, $saleFilter: Sale_filter, $saleOrderBy: Sale_orderBy, $orderDirection: OrderDirection) {\n  listings(\n    first: $first\n    where: $listingFilter\n    orderBy: $listingOrderBy\n    orderDirection: $orderDirection\n    skip: $skip\n  ) @include(if: $includeListings) {\n    ...ListingFields\n  }\n  bids(\n    first: $first\n    where: $bidFilter\n    orderBy: $bidOrderBy\n    orderDirection: $orderDirection\n    skip: $skip\n  ) @include(if: $includeBids) {\n    ...BidFields\n  }\n  sales(\n    first: $first\n    where: $saleFilter\n    orderBy: $saleOrderBy\n    orderDirection: $orderDirection\n    skip: $skip\n  ) @include(if: $includeSales) {\n    ...SaleFields\n  }\n}\n\nfragment ListingFields on Listing {\n  timestamp\n  id\n  pricePerItem\n  quantity\n  seller {\n    id\n  }\n  token {\n    id\n    tokenId\n  }\n  collection {\n    id\n  }\n  currency {\n    id\n  }\n  status\n  expiresAt\n}\n\nfragment BidFields on Bid {\n  timestamp\n  id\n  pricePerItem\n  quantity\n  token {\n    id\n    tokenId\n  }\n  collection {\n    id\n  }\n  currency {\n    id\n  }\n  buyer {\n    id\n  }\n  status\n  expiresAt\n  bidType\n}\n\nfragment SaleFields on Sale {\n  timestamp\n  id\n  pricePerItem\n  quantity\n  type\n  seller {\n    id\n  }\n  buyer {\n    id\n  }\n  token {\n    id\n    tokenId\n  }\n  collection {\n    id\n  }\n  currency {\n    id\n  }\n}",
        "variables": {
            "skip": 0,
            "first": 200,
            "saleOrderBy": "timestamp",
            "saleFilter": {
                "collection": config['collection'],
                "timestamp_gte": 1656753149
            },
            "orderDirection": "desc",
            "includeListings": False,
            "includeSales": True,
            "includeBids": False
        },
        "operationName": "getActivity"
    })
    headers = {
        'authority': 'api.thegraph.com',
        'accept': '*/*',
        'accept-language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload).json()
    temp = response['data']['sales'][0]
    # json_object = json.dumps(temp,indent=4)
    return temp


def get_current_price(symbol):
    ticker = yf.Ticker(symbol)
    todays_data = ticker.history(period='1d')
    return todays_data['Close'][0]

# Fixing price got from trove
def fixed_price(pricePerItem):
    return str(int(pricePerItem)/1000000000000000000)

def get_thumbnail():
    html_page = requests.get("https://trove.treasure.lol/collection/"+config['symbol'].lower()).content

    soup = BeautifulSoup(html_page, "html.parser")
    images = []
    for img in soup.findAll('img'):
        images.append(img.get('src'))
    return images[1]

def get_image(tokenId):
    html_page = requests.get("https://trove.treasure.lol/collection/"+config['symbol'].lower()+'/'+str(tokenId)).content

    soup = BeautifulSoup(html_page, "html.parser")
    images = []
    for img in soup.findAll('img'):
        images.append(img.get('src'))
    return images[0]

@tasks.loop(seconds=10)
async def sales():
    channel_id = config['channel_id']
    channel = client.get_channel(channel_id)
    try:
        meta = get_meta_from_mint()
        new_sale = str(meta['id'])
    except:
        pass
    if new_sale not in previous_sales:
        usd = str(
            round((get_current_price("ETH-" + config['fiat_currency']) * float(fixed_price(meta['pricePerItem']))),
                  4))
        eth = fixed_price(meta['pricePerItem'])
        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=config['symbol'].capitalize() + "#" + str(meta['token']['tokenId']),
            url="https://trove.treasure.lol/collection/" + config['symbol'].lower() + '/' + str(
                meta['token']['tokenId'])
        )
        embed.set_image(
            url=get_image(meta['token']['tokenId']))
        embed.set_thumbnail(
            url=get_thumbnail())
        embed.add_field(name="USD", value=usd + "$", inline=True)
        embed.add_field(name="ETH", value=eth + "Ξ", inline=True)
        embed.add_field(name="Buyer", value=meta['buyer']['id'], inline=False)
        embed.add_field(name="Seller", value=meta['seller']['id'], inline=False)
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text='\u200b')
        previous_sales.append(str(meta['id']))
        await channel.send(embed=embed)

@client.event
async def on_ready():
    global previous_sales
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    previous_sales = []
    try:
        meta = get_meta_from_mint()
        new_sale = str(meta['id'])
    except:
        pass

    sales.start()

client.run(os.environ["DISCORD_TOKEN"])
