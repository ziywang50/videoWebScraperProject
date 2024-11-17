from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import heapq
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidSessionIdException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from transformers import pipeline
from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image
from PIL import UnidentifiedImageError
import numpy as np
import requests



class GenericScraper:
    def __init__(self, product_link):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")  # Ensure the new session starts maximized
        #Both decimals and integers
        self.__price_regex = re.compile('\s*(USD|EUR|GBP|CNY|KRW|JPY|€|£|¥|₩|\$)\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)|(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s?(USD|EUR|GBP|CNY|KRW|JPY|€|£|\$|¥|₩)')
        #force to have a decimal, which is the prioritized method
        self.__price_regex_dec = re.compile('\s*(USD|EUR|GBP|CNY|KRW|JPY|€|£|¥|₩|\$)\s?(\d{1,3}(?:[.,]\d{3})*\.\d{1,2})|(\d{1,3}(?:[.,]\d{3})*\.\d{1,2})\s?(USD|EUR|GBP|CNY|KRW|JPY|€|£|\$|¥|₩)')
        #self.__url_regex = re.compile("^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(:\d+)?(\/[^\s]*)?$")
        self.product_link = product_link
        self.driver = webdriver.Chrome()
        self.driver.get(self.product_link)
        #self.driver.maximize_window()
        self.__viewport_height = self.driver.execute_script("return window.innerHeight;")
        self.__viewport_width = self.driver.execute_script("return window.innerWidth;")

    # Function to check and ensure a browser instance is running
    def __ensure_browser_open(self, driver, browser_type="chrome"):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")  # Ensure the new session starts maximized
        try:
            # Check if the driver is still active
            driver.current_url  # Access any property to check if the driver is active
            #print("Browser is already running.")
        except (WebDriverException, InvalidSessionIdException):
            # If the driver is not active, start a new one
            #print("Browser is closed. Starting a new browser instance.")
            if browser_type.lower() == "chrome":
                driver = webdriver.Chrome()
            elif browser_type.lower() == "firefox":
                driver = webdriver.Firefox()
            else:
                raise ValueError("Unsupported browser type!")
        return driver

    def __list_to_xPath_helper(self, li, list_of_tags=[]):
        #(//h1|//h2|//span)[contains(@class, 'active') or contains(@id,'main')]
        if len(li) == 0:
            return ''
        left, right = '', ''
        if not list_of_tags:
            left = '//*'
        elif len(list_of_tags) == 1:
            left = '//' + list_of_tags[0]
        else:
            for i,tag in enumerate(list_of_tags):
                if i==0:
                    left += '('
                else:
                    left += ' | '
                t = '//' + tag
                left += t
                if i== len(list_of_tags)-1:
                    left += ')'
        for i, l in enumerate(li):
            q = 'contains(@class, ' + l + ')'
            if i == 0:
                right+='['
            right += q
            if i != len(li) - 1:
                right += ' or '
            else:
                right+=']'
        return left+right

    def __find_max_img_helper(self, driver, heap_of_images, product_title, finding_wait=2, extra_wait_param=3, similarity_threshold=0.2):
        try:
            WebDriverWait(driver, finding_wait).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'img')))
        except TimeoutException:
            WebDriverWait(driver, extra_wait_param*finding_wait).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'img')))
        # front_page_container = driver.find_element(By.CSS_SELECTOR, 'div.front-page')
        im = driver.find_elements(By.TAG_NAME, 'img')
        model, processor = self._load_clip_model()
        # print(im.get_attribute('src'))
        if im:
            for i in im:
                if 0 < i.rect['x'] < self.__viewport_width and 0 < i.rect['y'] < self.__viewport_height:
                    # print(i.get_attribute('src'))
                    # Image tags are 'src' or 'srcset'
                    if i.get_attribute('src'):
                        img_size = float(i.get_attribute('width')) * float(i.get_attribute('height'))
                        img_url = i.get_attribute('src')
                        similarity = self._find_image_match_product_similarity(model, processor, img_url, product_title)
                        #Check if image-text similarity is greater than threshold
                        if (similarity >= similarity_threshold):
                            heapq.heappush(heap_of_images, (-img_size, -similarity, i.get_attribute('src')))
                    elif i.get_attribute('srcset'):
                        img_size = float(i.get_attribute('width')) * float(i.get_attribute('height'))
                        pdt_links = i.get_attribute('srcset').split(' ')
                        #Check if image-text similarity is greater than threshold
                        for pdt_url in pdt_links:
                            #pdt_url = re.search(self.__url_regex, pdt_url)
                            if pdt_url:
                                similarity = self._find_image_match_product_similarity(model, processor, pdt_url.group(),
                                                                                       product_title)
                                if (similarity >= similarity_threshold):
                                    heapq.heappush(heap_of_images, (-img_size, -similarity, pdt_url))
                    # print("Image size is ", max_img_size, "with url ", max_img_url)
        # print(max_img_url)
        return heap_of_images

    def __find_url_helper(self, string):
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        url = re.findall(regex, string)
        return url[0][0]
    def _zero_shot_text_binary_classify(self, text, score_threshold):
        classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

        labels = ["product", "not a product"]

        result = classifier(text, candidate_labels=labels)
        return result['scores'][0] > score_threshold
#-------------------------------------------------------Functions to apply CLIP models----------------------------------------------------
    #Load a CLIP model and CLIP processor
    def _load_clip_model(self, model_path="openai/clip-vit-base-patch32", processor_path="openai/clip-vit-base-patch32"):
        # Load the CLIP model and processor from Hugging Face
        model = CLIPModel.from_pretrained(model_path)
        processor = CLIPProcessor.from_pretrained(processor_path)
        return model, processor

    # Function to load image from file path or URL
    def _load_image(self, image_path_or_url):
        if image_path_or_url.startswith("http"):
            # If the input is a URL, fetch the image
            image = Image.open(requests.get(image_path_or_url, stream=True).raw)
        else:
            # If it's a local file path, open the image from disk
            image = Image.open(image_path_or_url)
        return image

    # Function to compute similarity score
    def _find_image_match_product_similarity(self, model, processor, image_path_or_url, product_title):
        try:
            # Load and preprocess the image
            image = self._load_image(image_path_or_url)
        except (FileNotFoundError, UnidentifiedImageError):
            return 0

        # Preprocess the image and text (title)
        inputs = processor(text=[product_title], images=image, return_tensors="pt", padding=True)

        # Get image and text embeddings
        with torch.no_grad():
            outputs = model(**inputs)

        # Compute cosine similarity between image and text embeddings
        image_embeds = outputs.image_embeds
        text_embeds = outputs.text_embeds
        similarity = torch.cosine_similarity(image_embeds, text_embeds)

        return similarity.item()

    def _is_product_image(self, model, processor, image_path):
        # Load the image
        image = self._load_image(image_path)

        # Prepare the image and text prompt
        inputs = processor(text=["a photo of a product", "a photo of something that is not a product"], images=image,
                           return_tensors="pt", padding=True)

        # Make the prediction
        with torch.no_grad():
            outputs = model(**inputs)

        # Get the similarity scores for the two categories
        logits_per_image = outputs.logits_per_image  # this is the similarity score between the image and the text
        probs = logits_per_image.softmax(dim=1)  # softmax to get probabilities

        product_prob = probs[0][0].item()  # Probability that the image is a product
        non_product_prob = probs[0][1].item()  # Probability that the image is not a product

        # Decision based on higher probability
        if product_prob > non_product_prob:
            return True  # It's a product
        else:
            return False  # It's not a product

# --------------------------------------------End of functions to apply CLIP models----------------------------------------------------

    #initial_wait is the initial wait tiem
    #finding_wait is the wait time until I find the corresponding elements on a webpage.
    def find_product_image(self, product_title, initial_wait=5, finding_wait=3, extra_wait_param=2, final_wait=1):
        heap_of_images = []
        #time.sleep(initial_wait)
        WebDriverWait(self.driver, initial_wait).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        self.driver = self.__ensure_browser_open(self.driver)
        self.driver.get(self.product_link)
        try:
            self.driver.maximize_window()
        except WebDriverException as e:
            #print(e)
            pass
        images = ['"product_image"', '"ProductImage"', '"productImage"', '"product-image"']
        product_im_class_li = []
        max_img_url = ''
        image_xpath = self.__list_to_xPath_helper(images)
        try:
            WebDriverWait(self.driver, finding_wait).until(EC.presence_of_all_elements_located((By.XPATH, image_xpath)))
        except TimeoutException:
            try:
                WebDriverWait(self.driver, extra_wait_param*extra_wait_param*finding_wait).until(EC.presence_of_all_elements_located((By.XPATH, image_xpath)))
            except TimeoutException:
                pass
        except StaleElementReferenceException as e:
            try:
                WebDriverWait(self.driver, extra_wait_param*finding_wait).until(
                    EC.presence_of_all_elements_located((By.XPATH, image_xpath)))
            except:
                print("StaleElementRefereceException", e)
        product_im_class_li = self.driver.find_elements(By.XPATH, image_xpath)
        if (not product_im_class_li):
            #if not then find the largest image in the viewing window.
            heap_of_images = self.__find_max_img_helper(self.driver, heap_of_images, product_title, finding_wait, extra_wait_param)
        else:
            for web_element in product_im_class_li:
                heap_of_images = self.__find_max_img_helper(web_element, heap_of_images, product_title, finding_wait, extra_wait_param)
        while(heap_of_images):
            model, processor = self._load_clip_model()
            elmt = heapq.heappop(heap_of_images)
            max_img_url = elmt[2]
            if len(max_img_url)>0:
                max_img_url = self.__find_url_helper(max_img_url)
                time.sleep(final_wait)
                #self.driver.close()
                return max_img_url
        time.sleep(final_wait)
        #self.driver.close()
        return 'Not found'
            # get product price

    #initial_wait is the initial wait tiem
    #finding_wait is the wait time until I find the corresponding elements on a webpage.
    #extra_wait_param is the multiple of wait time if a timeout occurs
    def find_product_title(self, initial_wait=5, finding_wait=3, final_wait=1, extra_wait_param=3, text_classifier_threshold=0.7):
        t = None
        heap_of_titles = []
        titlels = ['"title"', '"Title"', '"name"', '"Name"', '"header"', '"Header"', '"Heading"', '"heading"',
                   '"product"', '"Product"']
        list_of_tags = ['h1', 'h2', 'h3', 'span']
        self.driver = self.__ensure_browser_open(self.driver)
        self.driver.get(self.product_link)
        #time.sleep(initial_wait)
        WebDriverWait(self.driver, initial_wait).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        try:
            self.driver.maximize_window()
        except WebDriverException as e:
            #print(e)
            pass
        title_xpath = self.__list_to_xPath_helper(titlels, list_of_tags)
        #titlestr = '//h1[contains(@class, ' + title + ')] | //h2[contains(@class, ' + title + ')] | //h3[contains(@class, ' + title + ')]| //span[contains(@class, ' + title + ')]'
        try:
            WebDriverWait(self.driver, finding_wait).until(
                EC.presence_of_all_elements_located((By.XPATH, title_xpath)))
        except TimeoutException:
            try:
                WebDriverWait(self.driver, extra_wait_param*finding_wait).until(
                    EC.presence_of_all_elements_located((By.XPATH, title_xpath)))
            except:
                pass
        except StaleElementReferenceException as e:
            #wait more time
            try:
                WebDriverWait(self.driver, extra_wait_param*finding_wait).until(
                    EC.presence_of_all_elements_located((By.XPATH, title_xpath)))
            except:
                print("StaleElementReferenceException", e)
        t = self.driver.find_elements(By.XPATH, title_xpath)
        if t:
            for i in t:
                if 0 < i.rect['x'] < self.__viewport_width and 0 < i.rect['y'] < self.__viewport_height:
                    titletxt = i.text
                    if (titletxt):
                        size = float(i.rect['height']) * float(i.rect['width'])
                        heapq.heappush(heap_of_titles, (-size, titletxt))
        while (heap_of_titles):
            title_res = heapq.heappop(heap_of_titles)
            if self._zero_shot_text_binary_classify(title_res[1], text_classifier_threshold):
                time.sleep(final_wait)
                #self.driver.close()
                return title_res[1]
        #self.driver.close()
        return 'Not found'

    #initial_wait is the initial wait tiem
    #finding_wait is the wait time until I find the corresponding elements on a webpage.
    #extra_wait_param is the multiple of wait time if a timeout occurs

    def match_price(self, initial_wait=8, finding_wait=3, final_wait=1, extra_wait_param=3):
        reli = []
        p = None
        span = None
        #self.driver = webdriver.Chrome()
        #self.driver.get(self.product_link)
        #self.driver.maximize_window()
        self.driver = self.__ensure_browser_open(self.driver)
        self.driver.get(self.product_link)
        #time.sleep(initial_wait)
        # Wait for the document to be fully loaded
        try:
            WebDriverWait(self.driver, initial_wait).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            try:
                WebDriverWait(self.driver, 2*initial_wait).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                return 'Not found'
        '''
        try:
            self.driver.maximize_window()
        except WebDriverException as e:
            #print(e)
            pass
        '''
        prices = ['"price"', '"Price"']
        #list_of_tags = ['div', 'span']
        list_of_tags = ['div', 'span', 'meta', 'data', 'strong', 'ins']
        prices_xpath = self.__list_to_xPath_helper(prices, list_of_tags)
        '''
        for i,price in enumerate(prices):
            if (i == 0):
                prices_xpath = '//*[contains(@class, ' + price + ')]'
            else:
                prices_xpath += ' or //*[contains(@class, ' + price + ')]'
        '''
        #for price in prices:
        try:
            WebDriverWait(self.driver, finding_wait).until(
                EC.presence_of_all_elements_located((By.XPATH, prices_xpath)))
            span = self.driver.find_elements(By.XPATH, prices_xpath)
        except TimeoutException:
            try:
                WebDriverWait(self.driver, extra_wait_param*finding_wait).until(
                    EC.presence_of_all_elements_located((By.XPATH, prices_xpath)))
                span = self.driver.find_elements(By.XPATH, prices_xpath)
            except:
                pass
                #print("timeout")
        except StaleElementReferenceException as e:
            #wait more time
            try:
                WebDriverWait(self.driver, extra_wait_param*finding_wait).until(
                    EC.presence_of_all_elements_located((By.XPATH, prices_xpath)))
                span = self.driver.find_elements(By.XPATH, prices_xpath)
            except:
                print("StaleElementReferenceException", e)
        # locate all elements that contains 'price'
        if span:
            for i in span:
                if 0 < i.rect['x'] < self.__viewport_width and 0 < i.rect['y'] < self.__viewport_height:
                    #WebDriverWait(i, 1).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'span')))
                    priceex = i.text
                    size = float(i.rect['height']) * float(i.rect['width'])
                    #Store decimals separately can be confusing
                    match_res_dec = re.search(self.__price_regex_dec, priceex)
                    if (match_res_dec):
                        heapq.heappush(reli, (-size, match_res_dec.group()))
                    #Some prices only contain integers
                    else:
                        match_res = re.search(self.__price_regex, priceex)
                        if match_res:
                            heapq.heappush(reli, (-size, match_res.group()))
        if (reli):
            pri = heapq.heappop(reli)
            time.sleep(final_wait)
            self.driver.close()
            return pri[1]
            #print(pri[1].group())
        time.sleep(final_wait)
        #self.driver.close()
        return 'Not found'

def main():
#----------------------------------------------------------Code for testing purposes-----------------------------------------------------------
    LINK_1 = "https://thomas-heaton.creator-spring.com/listing/film-camera-landscape-photogra?product=370&variation=6544&size=1920&srsltid=AfmBOoqb4Xi0LR6dZhlU6Be0HAFTWB_rimjBxyC1reas2KrUk22Zi4a6OBU&utm_content=YT3-8EXI96y5I9-Q7sQe3A-BIyeC-VhrLggM-dnOIjx84NxCADFRUfd7kTtZVkUWuR5Y0AT-YMYvkOfx3-vHCjZdmA&utm_term=UCfhW84xfA6gEc4hDK90rR1Q&utm_medium=product_shelf&utm_source=youtube"
    LINK_2 = "https://www.htltsupps.com/products/turk-builder?variant=45645992329429&country=US&currency=USD&utm_campaign=sag_organic&srsltid=AfmBOorymJd_yURPj1yzRtHzBnO9LCsrvmHTykzVRjkN0JNN8bcMuNJGN7s&utm_content=YT3-ISUGDlPne_hUsgGNGN0IwFvoUGFe4QwCHgVv4b3gQiFlAkrDLtCh2hS9q_3jXENPucx8rmkvv2s_RGhZyY9uCQ&utm_term=UCLqH-U2TXzj1h7lyYQZLNQQ&utm_medium=product_shelf&utm_source=youtube"
    LINK_3 = "https://www.ebay.com/itm/266718554926?_trkparms=amclksrc%3DITM%26aid%3D777008%26algo%3DPERSONAL.TOPIC%26ao%3D1%26asc%3D20230913095046%26meid%3D51e25bfb1d4643f795b4c510096fa44e%26pid%3D101831%26rk%3D1%26rkt%3D1%26itm%3D266718554926%26pmt%3D0%26noa%3D1%26pg%3D4375194%26algv%3DPersonalizedTopicsV2WithDynamicSizeRanker%26brand%3DNVIDIA&_trksid=p4375194.c101831.m47269&_trkparms=parentrq%3A286d891d1930ab1341bfc352ffffe802%7Cpageci%3A4a47ebce-a22d-11ef-9936-5e9dcb641f54%7Ciid%3A1%7Cvlpname%3Avlp_homepage"
    LINK_COOKIES = "https://store.insta360.com/product/one_x2?insrc=INRNP7I"
    LINK_4 = "https://www.mpb.com/en-us/product/smallhd-indie-7-monitor/sku-2799421"
    LINK_5 = "https://the617.club"
    LINK_6 = "https://www.amazon.com/gp/product/B014U596GO/ref=as_li_tl?ie=UTF8&tag=sousvideevery-20&camp=1789&creative=9325&linkCode=as2&creativeASIN=B014U596GO&linkId=892082d1782f22d10203abec5bed7935&th=1"
    LINK_7 = "https://www.ebay.com/itm/356144750186?_skw=leica+m9&epid=100164147&itmmeta=01JCPWJ6P4Y9373YBJ72A9V9FK&hash=item52ebe19e6a:g:X4wAAOSwu5RnC7Cc&itmprp=enc%3AAQAJAAAA4HoV3kP08IDx%2BKZ9MfhVJKm63WuYlvF0cVTRkbIK%2BWpKuEHrQeUsn0r7Bb9%2FnNfmHUh%2FiwN%2FfoFb3giIedd%2FsEh5i53WRrhq90AhSBPEM16f1ZHWGa3i7on3tCWqPBjQiArYYaIR28ov%2Fyc78v1nqN3riovXDGJRU63OdiK2mSQdclblOac%2FlTB9Y%2FT1YS1thhRxqqRujzi9BvKSYV9w1XaILsVl2GyCpdUrYO03CkJx6WrUuLZwmiUtVYd9pIy9B3BnPBTJsJmqMfE7uSX2OS5JRlGFZvBvHqvfs3pgn4dH%7Ctkp%3ABFBMluvI3OVk"
    LINK_8 = "https://www.capturelandscapes.com/photographer-month-thomas-heaton/"
    LINK_9 = "https://thomasheaton.co.uk/product/my-book/"
    LINK_10 = "https://store.dji.com/product/dji-rs-3?ch=launch-rs3-samholland&clickaid=X3zYImu0We91G3QjtfjeJM7ZOpzMZU12&clickpid=745444&clicksid=7f11750ff3a2407875d68a8470411788&from=dap_unique&pm=custom&utm_campaign=launch-rs3&utm_content=samholland&utm_medium=kol-affiliates&utm_source=yt&vid=116541"
    ex = GenericScraper(LINK_3)
    print(ex.match_price())
    title = ex.find_product_title()
    print(title)
    print(ex.find_product_image(product_title=title))

if __name__ == "__main__":
    main()

