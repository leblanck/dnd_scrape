"""Scrape bullmoose.com for Stock Status of used D&D Books for
specific locations.
"""

import re
import csv
import os
import time
import base64
from postmarker.core import PostmarkClient
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium import webdriver

postmark = PostmarkClient(server_token=os.environ.get("POSTMARK_API_KEY"))

options = Options()
options.add_argument("--headless")
# Use the following driver when running locally via CLI
driver = webdriver.Chrome(options=options)

# Use the following driver when running via Docker
# driver = webdriver.Remote("http://127.0.0.1:4444/wd/hub", options=options)


def get_initial_stock():
    """Get initial list of all items that are returned from search
    """

    driver.get("https://www.bullmoose.com/search?q=dungeons%20and%20dragons&so=0&page=1&af=-3288|-3")
    html = driver.page_source
    soup = BeautifulSoup(html)
    link_list = []

    divs = soup.find_all("div", class_="producttitlelink product-grid-variant")
    for text in divs:
        link = text.find_all("a", href = re.compile('/pid/*'))
        for text in link:
            href = text['href']
            link_list.append(href)
    return link_list


def get_detail_stock(url_extension):
    """Get detail stock information for each item returned from search
    """

    driver.get(f"https://www.bullmoose.com{url_extension}")
    time.sleep(2)
    html = driver.page_source
    soup = BeautifulSoup(html)

    stock = {"Item_Title": "", "MillCreek": "", "Scarborough": ""}

    title = soup.find("title").text
    title_stripped = title.split("|", 1)[0]
    print("*******************")
    print(title_stripped)
    print("*******************")

    stock["Item_Title"]=title_stripped

    div = soup.find("div", class_="avail-grid")
    if div is None:
        stock["MillCreek"]="N/A"
        stock["Scarborough"]="N/A"
    else:
        rows = div.find_all("td")
        sub_row = rows[15:30]
        new = sub_row[0:3] + sub_row[-3:]
        newnew = new[2:3] + new[5:6]

        for item in newnew:
            label = item.find("i")["aria-label"]
            if "Mill Creek" in label:
                if "Out of stock" in label:
                    stock["MillCreek"]="NOT IN STOCK"
                elif "In stock" in label:
                    stock["MillCreek"]="IN STOCK"
            elif "Scarborough" in label:
                if "Out of stock" in label:
                    stock["Scarborough"]="NOT IN STOCK"
                elif "In stock" in label:
                    stock["Scarborough"]="IN STOCK"
            else:
                print("WHAT?")
    return stock


def write_csv(stock_inv):
    """Write stock info to local .csv
    """

    with open("stock.csv", "w") as file:
        writer = csv.DictWriter(file, fieldnames=["Item_Title", "MillCreek", "Scarborough"])
        writer.writeheader()
        writer.writerows(stock_inv)


def send_email():
    """Send email summary out with stock.csv attachment
    """

    with open("stock.csv", "rb") as csv_file:
        data = csv_file.read()

    encoded_file = base64.b64encode(data).decode()

    postmark.emails.send(
        From='admin@leblanc.sh',
        To='kyle@leblanc.sh',
        Subject='DAILY D&D USED INVENTORY REPORT',
        HtmlBody='<h1>Roll an investigation check...</h1>',
        Attachments=[
            {
                'Name': 'stock.csv',
                'Content': encoded_file,
                'ContentType': 'text/csv'
            }
        ]
    )


stock_list = []
COUNT = 0
for COUNT in range(0, 5):
    items = get_initial_stock()
    if not items:
        print("Empty List Found! Trying Again...")
        COUNT += 1
        print("Attempt ", COUNT)
        items = get_initial_stock()
    else:
        for item in items:
            stock_list.append(get_detail_stock(item))
        break

write_csv(stock_list)
send_email()
