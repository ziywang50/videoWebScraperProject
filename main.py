# This is a sample Python script.
import requests
import json
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import selenium
from selenium import webdriver
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

def example(video_link, json_path, CLEAR_JSON=True):
    #JSON_PATH = "product_info.json"
    PATH = "C:/Program Files/chromedriver-win64/chromedriver.exe"
    REDIRECT = "https://www.youtube.com/redirect?"
    AMAZON = "https://www.amazon.com"
    FACEBOOK = "https://www.facebook.com"
    INSTAGRAM = "https://www.instagram.com"
    X = "https://www.x.com"
    SOCIAL_MEDIA_URLS = [FACEBOOK, INSTAGRAM, X]
    json_objs = []
    service = Service(executable_path=PATH)
    driver = webdriver.Chrome()
    driver.get(video_link)
    driver.maximize_window()
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='expand']")))
    if (len(driver.find_elements(By.XPATH, "//*[@id='expand']")) > 0):
        input_element = driver.find_element(By.XPATH, '//*[@id="expand"]')
        print(input_element.text)
        driver.find_element(By.XPATH, '//*[@id="expand"]').click()
    WebElement = driver.find_element(By.XPATH, '//*[@id="description-inner"]')
    links = WebElement.find_elements(By.TAG_NAME, 'a')
    for link in links:
        href = link.get_attribute('href')
        if (href.find(REDIRECT) == 0):
            response = requests.get(href)
            if (response.status_code == 200):
                driver = webdriver.Chrome()
                print(f"Link name is {href}")
                driver.get(href)
                if driver.find_element(By.XPATH, '//*[@id="invalid-token-redirect-goto-site-button"]'):
                    driver.find_element(By.XPATH, '//*[@id="invalid-token-redirect-goto-site-button"]').click()
                    #break
                current_url = driver.current_url
                if (current_url.find(AMAZON) == 0):
                    amzn_web(driver, json_objs)
                time.sleep(3)
                driver.quit()
    with open(json_path, "w") as outfile:
        json.dump(json_objs, outfile)
        #if (driver.find_elements(By.XPATH, "//*[@id='items']/ytd-merch-shelf-item-renderer")):
    #WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "style-scope ytd-merch-shelf-item-renderer")))
    driver = webdriver.Chrome()
    driver.get(video_link)
    driver.maximize_window()
    if (len(driver.find_elements(By.CLASS_NAME, "product-item style-scope ytd-merch-shelf-item-renderer")) > 0):
         items = driver.find_elements(By.CLASS_NAME, "product-item style-scope ytd-merch-shelf-item-renderer")
    #if (len(driver.find_elements(By.CLASS_NAME, "style-scope ytd-merch-shelf-item-renderer")) > 0):
    #    items = driver.find_elements(By.CLASS_NAME, "style-scope ytd-merch-shelf-item-renderer")
    time.sleep(10)
    driver.quit()
def amzn_web(driver, json_objs):
    #PRICE_PATH= '//*[@id="corePriceDisplay_desktop_feature_div"]/div[1]/span[2]'
    current_url = driver.current_url
    PRICE_ID = 'corePrice_feature_div'
    IMG_PATH = '//*[@id="landingImage"]'
    TITLE_PATH = '//*[@id="productTitle"]'
    KINDLE_PRICE_PATH = '//*[@id="kindle-price"]'
    #class names for price of item
    PRICE_WHOLE_CLASS = 'a-price-whole'
    PRICE_SYMBOL_CLASS = 'a-price-symbol'
    PRICE_FRACTION_CLASS = 'a-price-fraction'
    try:
        price = driver.find_element(By.ID, PRICE_ID)
        if (price):
            whole_class = price.find_element(By.CLASS_NAME, PRICE_WHOLE_CLASS)
            symbol_class = price.find_element(By.CLASS_NAME, PRICE_SYMBOL_CLASS)
            fraction_class = price.find_element(By.CLASS_NAME, PRICE_FRACTION_CLASS)
            pricef = symbol_class.text + whole_class.text + '.' + fraction_class.text
        else:
            pricef = driver.find_element(By.XPATH, KINDLE_PRICE_PATH)
        img = driver.find_element(By.XPATH, IMG_PATH)
        title = driver.find_element(By.XPATH, TITLE_PATH)
        info = {
            "product_price":  pricef,
            "product_image": img.get_attribute('src'),
            "product_name": title.text,
            "buy_link": current_url
        }
        #with open(json_path, "a") as outfile:
        json_objs.append(info)
        #print("The price of the product is:", symbol_class.text, whole_class.text, '.', fraction_class.text, "with image link", img.get_attribute('src'))
        print("Successful")
    except:
        print("Failed")
    return

if __name__ == '__main__':
    LINK_ZERO = 'https://www.youtube.com/watch?v=qm1BBmV8RRY'
    LINK_ONE = 'https://www.youtube.com/watch?v=ju8OkY4EE24'
    AMZN_LINK_TWO = 'https://www.youtube.com/watch?v=RYRLxVfijpI'
    #AMZN_LINK_ZERO = 'https://www.youtube.com/watch?v=yOl7q-DIz4s'
    JSON_PATH_1 = 'product_info_1.json'
    #JSON_PATH_2 = 'product_info_2.json'
    #JSON_PATH_3 = 'product_info_3.json'
    JSON_PATH_4 = 'product_info_4.json'
    example(LINK_ZERO, JSON_PATH_1)
    #example(AMZN_LINK_TWO, JSON_PATH_4)
    #example(LINK_ONE, JSON_PATH_2)
    #example(AMZN_LINK_ZERO, JSON_PATH_3)
    #example('https://www.youtube.com/watch?v=ju8OkY4EE24')
    '''
    df = pd.read_json("product_info.json", orient='records')
    print(df.head())
    print(df.columns)
    print(df.shape)
    '''