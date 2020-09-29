from bs4 import BeautifulSoup
import urllib.request as urb
import requests
from tqdm import tqdm
from time import sleep
import pandas as pd
import re
from fake_useragent import UserAgent

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

import traceback
import sys

options = webdriver.ChromeOptions()
chrome_prefs = {}
options.experimental_options["prefs"] = chrome_prefs
chrome_prefs["profile.default_content_settings"] = {"images": 2}
chrome_prefs["profile.managed_default_content_settings"] = {"images": 2}

ua = UserAgent()
chrome_prefs["user-agent"] = {'User-Agent':str(ua.chrome)}

url = 'https://www.electoralcommission.org.uk/2019-candidate-spending?section='

DRIVER_PATH = 'chromedriver_win32\chromedriver'
driver = webdriver.Chrome(options=options, executable_path=DRIVER_PATH)
driver.get(url)

columns_list = ["vote_share","total_reported_spending","electorate_figure","spending_limit","spending_as_percent",\
    "direct_spending","notional_spending","unpaid_claims","disputed_claims","advertising","unsolicitated_material",\
    "transport","public_meetings","agent_and_staff","accomodation",\
    "personal_expenses","donations_accepted"]
temp = {key: [] for key in columns_list}
url_li=[]
df = pd.read_excel ('input.xlsx', index_col=0)


driver.get(url)
#cookie choice
WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#ccc-notify-accept"))).click()


with tqdm(total=500, file=sys.stdout) as pbar:
    for index, row in df.iterrows():
        driver.get(url)
        sleep(1)

        try:
            name_ele = driver.find_element_by_xpath("//input[@name='filter-candidate-name-search']").send_keys(row["candidate_name"])
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "li[data-label='%s']" % row["candidate_name"])))
            element.click()
        except TimeoutException as e:
            driver.find_element_by_xpath("//input[@name='filter-candidate-name-search']").clear()
            #when middle name not present 
            if len(row["candidate_name"].split(" "))>2:
                name = row["candidate_name"].split(" ")[0]+" "+row["candidate_name"].split(" ")[-1]
            else:
                name = row["candidate_name"]
            name_ele = driver.find_element_by_xpath("//input[@name='filter-candidate-name-search']").send_keys(name)
            element = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "li[data-label='%s']" %name)))
            element.click()
        except StaleElementReferenceException as e:
            #try again
            driver.find_element_by_xpath("//input[@name='filter-candidate-name-search']").clear()
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "li[data-label='%s']" % row["candidate_name"])))
            element.click()

        # accordion button containing filters
        button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,\
            "#electoral-expenses-viz > div > div > div > div.electoral-expenses-viz-MetricSelection__metric-selection___1eBV6 > div > button")))
        button.click()

        sleep(1)
        # select all filter buttons
        for i in range(1,18):
            btn = WebDriverWait(driver,20).until(EC.element_to_be_clickable((By.CSS_SELECTOR,\
            "#electoral-expenses-viz > div > div > div > div.electoral-expenses-viz-MetricSelection__metric-selection___1eBV6 > div > div > div > button:nth-child(%s)" %i)))
            val = btn.get_attribute("aria-pressed")
            if val == "false": 
                btn.click()

        curr_url = driver.current_url
        url_li.append(curr_url)
        content = driver.page_source.encode('utf-8').strip()
        soup = BeautifulSoup(content, 'lxml')
        
        #scrape prices
        for i,j in zip(columns_list,range(1,18)):
            val = soup.select_one('#electoral-expenses-viz > div > div > div > div.electoral-expenses-viz-Panels__panels___2UPxQ > div > div:nth-child(%s) > div:nth-child(2) > div > div:nth-child(2)' %j).text.strip()
            val = re.sub("[,%u'\u00a3']", '', val)
            val.replace("Information not provided in the spending return",'0')
            temp[i].append(val)

        pbar.update(1)


for i in columns_list:
    df[i] = temp[i]
df["URL"] = url_li
df.replace(['Information not provided in the spending retrn', 'Retrn not received before deadline'], ['0', '0'],inplace=True)
df.to_excel("output.xlsx") 