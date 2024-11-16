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
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from amazoncaptcha import AmazonCaptcha
from GenericScraper import GenericScraper


def json_from_video(video_link, json_path, CLEAR_JSON=True):

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
    try:
        driver.maximize_window()
    except:
        pass
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='expand']")))
    if (len(driver.find_elements(By.XPATH, "//*[@id='expand']")) > 0):
        input_element = driver.find_element(By.XPATH, '//*[@id="expand"]')
        print(input_element.text)
        driver.find_element(By.XPATH, '//*[@id="expand"]').click()
    WebElement = driver.find_element(By.XPATH, '//*[@id="description-inner"]')
    links = WebElement.find_elements(By.TAG_NAME, 'a')
    for link in links:
        href = link.get_attribute('href')
        if href:
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
                    for s in SOCIAL_MEDIA_URLS:
                        if (current_url.find(s) == 0):
                            time.sleep(0.5)
                            driver.close()
                    if (current_url.find(AMAZON) == 0):
                        amzn_web(driver, json_objs)
                    else:
                        generic_web(current_url, json_objs)
                    time.sleep(0.5)
                    driver.close()
    #By default, it clears the current json with the same name.
    if (CLEAR_JSON):
        with open(json_path, "w") as outfile:
            json.dump(json_objs, outfile)
    else:
        with open(json_path, "a") as outfile:
            json.dump(json_objs, outfile)
    #if (len(driver.find_elements(By.CLASS_NAME, "product-item style-scope ytd-merch-shelf-item-renderer")) > 0):
    #     items = driver.find_elements(By.CLASS_NAME, "product-item style-scope ytd-merch-shelf-item-renderer")
    #if (len(driver.find_elements(By.CLASS_NAME, "style-scope ytd-merch-shelf-item-renderer")) > 0):
    #    items = driver.find_elements(By.CLASS_NAME, "style-scope ytd-merch-shelf-item-renderer")
    time.sleep(10)
    driver.quit()
def amzn_web(driver, json_objs):
    #PRICE_PATH= '//*[@id="corePriceDisplay_desktop_feature_div"]/div[1]/span[2]'
    #set headless properties
    options = Options()
    #options.add_argument("--headless=new")
    try:
        link = driver.find_element(By.XPATH, "//div[@class = 'a-row a-text-center']//img").get_attribute('src')
        captcha = AmazonCaptcha.fromlink(link)
        captcha_value = AmazonCaptcha.solve(captcha)
        input_field = driver.find_element(By.ID, "captchacharacters").send_keys(captcha_value)
        button = driver.find_element(By.CLASS_NAME, "a-button-text")
        button.click()
        time.sleep(1)
    except NoSuchElementException:
        pass
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
        whole_class = price.find_element(By.CLASS_NAME, PRICE_WHOLE_CLASS)
        symbol_class = price.find_element(By.CLASS_NAME, PRICE_SYMBOL_CLASS)
        fraction_class = price.find_element(By.CLASS_NAME, PRICE_FRACTION_CLASS)
        price_value = symbol_class.text + whole_class.text + '.' + fraction_class.text
    except NoSuchElementException:
        try:
            price = driver.find_element(By.XPATH, KINDLE_PRICE_PATH)
            price_value = price.text
        except:
            print("Find price failed")
            return
    img = driver.find_element(By.XPATH, IMG_PATH)
    title = driver.find_element(By.XPATH, TITLE_PATH)
    info = {
        "product_price":  price_value,
        "product_image": img.get_attribute('src'),
        "product_name": title.text,
        "buy_link": current_url
    }
    print("appending json...")
    json_objs.append(info)
    #print("The price of the product is:", symbol_class.text, whole_class.text, '.', fraction_class.text, "with image link", img.get_attribute('src'))
    #print("Successful")
def generic_web(current_url, json_objs):
    generic_scraper = GenericScraper(current_url)
    price = generic_scraper.match_price()
    if(price != 'Not found'):
        product_title = generic_scraper.find_product_title()
        if(product_title != 'Not found'):
            product_img_url = generic_scraper.find_product_image(product_title)
            if (product_img_url != 'Not found'):
                print("appending json...")
                info = {
                    "product_price": price,
                    "product_image": product_img_url,
                    "product_name": product_title,
                    "buy_link": current_url
                }
                json_objs.append(info)
    generic_scraper.driver.close()

if __name__ == '__main__':
    LINK_ZERO = 'https://www.youtube.com/watch?v=ZFbiZIsS9vQ'
    LINK_ONE = 'https://www.youtube.com/watch?v=ju8OkY4EE24'
    LINK_TWO = 'https://www.youtube.com/watch?v=8QM7bnB1HzA'
    AMZN_LINK_TWO = 'https://www.youtube.com/watch?v=RYRLxVfijpI'
    #AMZN_LINK_ZERO = 'https://www.youtube.com/watch?v=yOl7q-DIz4s'
    JSON_PATH_0 = 'product_info_0.json'
    JSON_PATH_1 = 'product_info_1.json'
    JSON_PATH_2 = 'product_info_2.json'
    #JSON_PATH_3 = 'product_info_3.json'
    JSON_PATH_4 = 'product_info_4.json'
    #json_from_video(AMZN_LINK_TWO, JSON_PATH_4)
    #json_from_video(LINK_ZERO, JSON_PATH_0)
    json_from_video(LINK_TWO, JSON_PATH_2)
    '''
    df = pd.read_json("product_info.json", orient='records')
    print(df.head())
    print(df.columns)
    print(df.shape)
    '''

