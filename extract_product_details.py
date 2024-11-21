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
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from amazoncaptcha import AmazonCaptcha
from GenericScraper import GenericScraper
from selenium.common.exceptions import InvalidSessionIdException
import re

def json_from_video(video_link, json_path, CLEAR_JSON=True, finding_wait=8, final_wait=0.5, extra_wait_param=2):
    try:
        json_from_video_helper(video_link, json_path, CLEAR_JSON=CLEAR_JSON, finding_wait=finding_wait, final_wait=final_wait, extra_wait_param=extra_wait_param)
    except StaleElementReferenceException as e:
        print("Please do not refresh page and retry", e)
        return
    except NoSuchElementException as e:
        print("Please do not close window and retry", e)
        return
def json_from_video_helper(video_link, json_path, CLEAR_JSON=True, finding_wait=8, final_wait=0.5, extra_wait_param=2):
    PATH = "C:/Program Files/chromedriver-win64/chromedriver.exe"
    REDIRECT = "https://www.youtube.com/redirect?"
    #Stop redirecting to common social media URLs
    AMAZON = "https://www.amazon."
    SOCIAL_MEDIA_URLS = ["facebook.com", "instagram.com", "x.com", "pinterest.com", "tiktok.com"]
    URL_REGEX = re.compile("^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(:\d+)?(\/[^\s]*)?$")
    YOUTUBE = "https://www.youtube.com"
    json_objs = []
    service = Service(executable_path=PATH)
    driver = webdriver.Chrome()
    driver.get(video_link)
    try:
        driver.maximize_window()
    except:
        pass
    try:
        WebDriverWait(driver, finding_wait).until(EC.element_to_be_clickable((By.XPATH, ".//*[@id='expand']")))
    except TimeoutException:
        try:
            WebDriverWait(driver, extra_wait_param*finding_wait).until(EC.element_to_be_clickable((By.XPATH, ".//*[@id='expand']")))
        except:
            print("TimeoutException.")
            return
    #If it is able to find the "more" button on the description, click. Else, ignore this.
    try:
        input_element = driver.find_element(By.XPATH, './/*[@id="expand"]')
        input_element.click()
        WebElement = driver.find_element(By.XPATH, './/*[@id="description-inner"]')
    except NoSuchElementException:
        pass
    #Find all 'a' tag, which contain all links
    if (WebElement):
        WebDriverWait(WebElement, 5).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'a')))
        links = WebElement.find_elements(By.TAG_NAME, 'a')
    amzn = Amazon_web()
    for link in links:
        href = link.get_attribute('href')
        if not href:
            continue
        #either a redirect url or another url that is not in youtube
        if (href.find(REDIRECT) == 0 or (href.find(YOUTUBE) == -1 and re.search(URL_REGEX, href))):
            response = requests.get(href)
            #If the link opens successfully
            if (response.status_code == 200):
                try:
                    IS_SOCIAL_MEDIA_URL = False
                    driver = webdriver.Chrome()
                    print(f"Link name is {href}")
                    driver.get(href)
                    #If youtube asks me to redirect, click on button
                    try:
                        driver.find_element(By.XPATH, './/*[@id="invalid-token-redirect-goto-site-button"]').click()
                    except NoSuchElementException:
                        pass
                    current_url = driver.current_url
                    for s in SOCIAL_MEDIA_URLS:
                        if (current_url.find(s) != -1):
                            IS_SOCIAL_MEDIA_URL = True
                            time.sleep(final_wait)
                            driver.close()
                            break
                    if not IS_SOCIAL_MEDIA_URL:
                        try:
                            if (current_url.find(AMAZON) == 0):
                                amzn.amzn_web(driver, json_objs)
                            else:
                                generic_web(current_url, json_objs)
                        except StaleElementReferenceException:
                            print("Element no longer exists. Please do not refresh the webpage as it will interrupt the process.")
                            continue
                        except NoSuchElementException:
                            print("Please do not close window, and re-run.")
                            continue
                        except NoSuchWindowException:
                            print("Window closed. Please do not close window.")
                            continue
                        #time.sleep(final_wait)
                        driver.close()
                except InvalidSessionIdException as e:
                    print("Link skipped due to InvalidSessionIdException ", e)
                    continue

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
    #time.sleep(10)
    #driver.quit()

#Function for opening up an amazon page and finding product info and appending to json file.
class Amazon_web:
    def __init__(self):
        self.PRICE_ID = 'corePrice_feature_div'
        self.IMG_PATH = './/*[@id="landingImage"]'
        self.TITLE_PATH = './/*[@id="productTitle"]'
        #self.KINDLE_PRICE_PATH = '//*[@id="kindle-price"]'
        # class names for price of item
        self.PRICE_WHOLE_CLASS = 'a-price-whole'
        self.PRICE_SYMBOL_CLASS = 'a-price-symbol'
        self.PRICE_FRACTION_CLASS = 'a-price-fraction'
        self.PRICE_REGEX = re.compile(
            '\s*(USD|EUR|GBP|CNY|KRW|JPY|€|£|¥|₩|\$)\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)|(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s?(USD|EUR|GBP|CNY|KRW|JPY|€|£|\$|¥|₩)')
        #self.SIMILAR_PRODUCT_LINK = ".//a[contains(@id, 'sp_detail') and contains(@id, 'title')]"
        self.SIMILAR_PRODUCT_LINK = ".//a[(contains(@id, 'sp_detail_') and contains(@id, '_title')) or contains(@class, a-link)]"
        self.SIMILAR_PRODUCT_LINK_REGEX = re.compile("^https?:\/\/(?:www\.)?amazon\.com(?:\/[^\s]*)?$")
        # Find element in Amazon's main section

    def amzn_web(self, driver, json_objs, related_products=True, finding_wait=3):
        try:
            link = driver.find_element(By.XPATH, ".//div[@class = 'a-row a-text-center']//img").get_attribute('src')
            captcha = AmazonCaptcha.fromlink(link)
            captcha_value = AmazonCaptcha.solve(captcha)
            driver.find_element(By.ID, "captchacharacters").send_keys(captcha_value)
            button = driver.find_element(By.CLASS_NAME, "a-button-text")
            button.click()
            time.sleep(1)
        except NoSuchElementException:
            pass
        current_url = driver.current_url
        try:
            price = driver.find_element(By.ID, self.PRICE_ID)
            #suppose the class is stored with whole elements and decimal elements
            price_value = self.__price_helper(price)
            if (price_value == -1):
                return
        except NoSuchElementException:
            try:
                spans_with_price_parent_or_grandparent = driver.find_elements(
                    By.XPATH, ".//span[parent::*[contains(@class, 'price')] or ancestor::*[contains(@class, 'price')]]"
                )
                # Print the found spans
                if (spans_with_price_parent_or_grandparent):
                    for span in spans_with_price_parent_or_grandparent:
                        price_search = re.search(self.PRICE_REGEX, span.text)
                        if price_search:
                            price_value = price_search.group()
                            break
                #If price not found, then return
                else:
                    return
            except (TypeError, ValueError) as e:
                print("Find price failed. Message: " + e)
                return
        try:
            img = driver.find_element(By.XPATH, self.IMG_PATH)
            title = driver.find_element(By.XPATH, self.TITLE_PATH)
        except NoSuchElementException:
            return
        info = {
            "product_price":  price_value,
            "product_image": img.get_attribute('src'),
            "product_name": title.text,
            "buy_link": current_url
        }
        print("appending json...")
        json_objs.append(info)
    #Find elements in the related products section
        if (related_products):
            try:
                #wait = WebDriverWait(driver, 2)  # Wait for up to 10 seconds
                #Wait on webDriver for a number of seconds
                WebDriverWait(driver, finding_wait).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//ol[@class='a-carousel']/li[@class='a-carousel-card']"))
                )
                #Related Products Section
                product_cards = driver.find_elements(By.XPATH, "//ol[@class='a-carousel']/li[@class='a-carousel-card']")
                for card in product_cards:
                    try:
                        WebDriverWait(card, finding_wait).until(
                            EC.presence_of_element_located((By.TAG_NAME, "img"))
                        )
                        WebDriverWait(card, finding_wait).until(
                            EC.presence_of_element_located((By.XPATH, self.SIMILAR_PRODUCT_LINK))
                        )
                        product_title = card.find_element(By.TAG_NAME, "div").text
                        product_img = card.find_element(By.TAG_NAME, "img").get_attribute('src')
                        product_price = self.__price_helper(card)
                        buy_link_a = card.find_elements(By.XPATH, self.SIMILAR_PRODUCT_LINK)
                        for buy_link_i in buy_link_a:
                            buy_link = buy_link_i.get_attribute('href')
                            if buy_link == "javascript:void(0)":
                                continue
                            else:
                                break
                        #print(buy_link)
                        #for buy_link_i in buy_link_a:
                        #    buy_link_res = buy_link_i.get_attribute('href')
                        #    buy_link_res = re.search(self.SIMILAR_PRODUCT_LINK_REGEX, buy_link_res)
                        #    if (buy_link_res):
                        #        buy_link = buy_link_res.group()
                        if (product_title and product_img and product_price and buy_link):
                            info = {
                                "product_price": product_price,
                                "product_image": product_img,
                                "product_name": product_title,
                                "buy_link": buy_link
                            }
                            print("appending json similar items...", info)
                            json_objs.append(info)
                    except NoSuchElementException:
                        pass
            except TimeoutException as e:
                pass
            except InvalidSessionIdException as e2:
                print("InvalidSessionException", e2)

    #Helper on locating the price element of a webpage
    def __price_helper(self, price_element):
        try:
            whole_class = price_element.find_element(By.CLASS_NAME, self.PRICE_WHOLE_CLASS)
            symbol_class = price_element.find_element(By.CLASS_NAME, self.PRICE_SYMBOL_CLASS)
            fraction_class = price_element.find_element(By.CLASS_NAME, self.PRICE_FRACTION_CLASS)
            price_value = symbol_class.text + whole_class.text + '.' + fraction_class.text
            return price_value
            #
        except NoSuchElementException:
            spans_with_price_parent_or_grandparent = price_element.find_elements(
                By.XPATH, ".//span[parent::*[contains(@class, 'price')] or ancestor::*[contains(@class, 'price')]]"
            )
            # Print the found spans
            if (spans_with_price_parent_or_grandparent):
                for span in spans_with_price_parent_or_grandparent:
                    try:
                        price_search = re.search(self.PRICE_REGEX, span.text)
                        if price_search:
                            price_value = price_search.group()
                            return price_value
                    except (TypeError, ValueError) as e:
                        print("Find price failed. Message: " + e)
                        return -1
            return -1

#For any other web page(except the social media pages that are blocked)
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
                    if info not in json_objs:
                        json_objs.append(info)
        generic_scraper.driver.close()

if __name__ == '__main__':
    LINK_ZERO = 'https://www.youtube.com/watch?v=ZFbiZIsS9vQ'
    LINK_ONE = 'https://www.youtube.com/watch?v=ju8OkY4EE24'
    LINK_TWO = 'https://www.youtube.com/watch?v=8QM7bnB1HzA'
    LINK_THREE = 'https://www.youtube.com/watch?v=TDzFYE8kA78'
    AMZN_LINK_TWO = 'https://www.youtube.com/watch?v=RYRLxVfijpI'
    LINK_FIVE = 'https://www.youtube.com/watch?v=3zLvByt52go'
    LINK_SIX = 'https://www.youtube.com/watch?v=7B8owry2dog'
    LINK_SEVEN = 'https://www.youtube.com/watch?v=9PCtfKr5Uw8'
    LINK_EIGHT = 'https://www.youtube.com/watch?v=0IQpOA0QpBk'
    #AMZN_LINK_ZERO = 'https://www.youtube.com/watch?v=yOl7q-DIz4s'
    JSON_PATH_0 = 'product_info_0.json'
    JSON_PATH_1 = 'product_info_1.json'
    JSON_PATH_2 = 'product_info_2.json'
    JSON_PATH_3 = 'product_info_3.json'
    JSON_PATH_4 = 'product_info_4.json'
    JSON_PATH_5 = 'product_info_5.json'
    JSON_PATH_6 = 'product_info_6.json'
    JSON_PATH_7 = 'product_info_7.json'
    JSON_PATH_8 = 'product_info_8.json'
    json_from_video(LINK_ONE, JSON_PATH_1)
    #json_from_video(LINK_ZERO, JSON_PATH_0)
    #json_from_video(LINK_ONE, JSON_PATH_1)
    #json_from_video(LINK_ZERO, JSON_PATH_0)
    #json_from_video(LINK_FIVE, JSON_PATH_5)
    #json_from_video(LINK_SIX, JSON_PATH_6)
    #json_from_video(LINK_TWO, JSON_PATH_2)
    #json_from_video(LINK_EIGHT, JSON_PATH_8)
    '''
    df = pd.read_json("product_info.json", orient='records')
    print(df.head())
    print(df.columns)
    print(df.shape)
    '''

