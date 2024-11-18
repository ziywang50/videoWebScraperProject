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
import concurrent.futures
from io import BytesIO

#Class for scraping one product information from a generic website
class GenericScraper:
    def __init__(self, product_link):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")  # Ensure the new session starts maximized
        #Both decimals and integers
        self.__price_regex = re.compile('\s*(USD|EUR|GBP|CNY|KRW|JPY|€|£|¥|₩|\$)\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)|(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s?(USD|EUR|GBP|CNY|KRW|JPY|€|£|\$|¥|₩)')
        #force to have a decimal, which is the prioritized method
        self.__price_regex_dec = re.compile('\s*(USD|EUR|GBP|CNY|KRW|JPY|€|£|¥|₩|\$)\s?(\d{1,3}(?:[.,]\d{3})*\.\d{1,2})|(\d{1,3}(?:[.,]\d{3})*\.\d{1,2})\s?(USD|EUR|GBP|CNY|KRW|JPY|€|£|\$|¥|₩)')
        self.__url_regex = re.compile("^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(:\d+)?(\/[^\s]*)?$")
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
                #driver.get(self.product_link)
                #self.driver.get(self.product_link)
            elif browser_type.lower() == "firefox":
                driver = webdriver.Firefox()
                #driver.get(self.product_link)
                #self.driver.get(self.product_link)
            else:
                raise ValueError("Unsupported browser type!")
        return driver

    #Function to construct an xpath from one of the list of tags that contains a list of possible classes
    def __list_to_xPath_helper(self, li, list_of_tags=[]):
        #(//h1|//h2|//span)[contains(@class, 'active') or contains(@id,'main')]
        if len(li) == 0:
            return ''
        left, right = '', ''
        if not list_of_tags:
            left = './/*'
        elif len(list_of_tags) == 1:
            left = './/' + list_of_tags[0]
        else:
            for i,tag in enumerate(list_of_tags):
                if i==0:
                    left += '('
                else:
                    left += ' | '
                t = './/' + tag
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

    #Helper to push images in the heap. An image need to meet the similarity threshold to be pushed into the heap, where
    #similarity is defined to be the similarity of that image to the product title, computed using self._find_image_match_product_similarity
    #An image is greater if it has a greater size, and if the same size, compare their similariies.
    def __find_max_img_helper(self, driver, heap_of_images, product_title, finding_wait=3, extra_wait_param=3, similarity_threshold=0.2, max_webelements=10):
        try:
            WebDriverWait(driver, finding_wait).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'img')))
        except TimeoutException:
            pass
        # front_page_container = driver.find_element(By.CSS_SELECTOR, 'div.front-page')
        im = driver.find_elements(By.TAG_NAME, 'img')
        model, processor = self._load_clip_model()
        # print(im.get_attribute('src'))
        if len(im) > 2*max_webelements:
            im = im[:2*max_webelements]
        if im:
            for i in im:
                if i.rect['x'] < 2*self.__viewport_width and i.rect['y'] < 2*self.__viewport_height:
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
                            pdt_url = re.search(self.__url_regex, pdt_url)
                            if pdt_url:
                                similarity = self._find_image_match_product_similarity(model, processor, pdt_url.group(),
                                                                                       product_title)
                                if (similarity >= similarity_threshold):
                                    heapq.heappush(heap_of_images, (-img_size, -similarity, pdt_url))
                if len(heap_of_images) >= max_webelements:
                    return heap_of_images
                    # print("Image size is ", max_img_size, "with url ", max_img_url)
        # print(max_img_url)
        return heap_of_images

    #find the best valid url
    def __find_url_helper(self, string):
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        url = re.findall(regex, string)
        return url[0][0]

    #Load a new image by url or path
    def __load_image(self, image_path_or_url):
        if image_path_or_url.startswith("http"):
            # If the input is a URL, fetch the image
            image = Image.open(requests.get(image_path_or_url, stream=True).raw)
        else:
            # If it's a local file path, open the image from disk
            image = Image.open(image_path_or_url)
        return image
    # Function to open an image
    '''
    def __load_image(self, image_path_or_url):
        if image_path_or_url.startswith("http"):
            # If the input is a URL, fetch the image
            image = Image.open(requests.get(image_path_or_url, stream=True).raw)
        else:
            # If it's a local file path, open the image from disk
            image = Image.open(image_path_or_url)
        return image
    # Wrapper function to open an image with a timeout
    def __open_image_with_timeout(self, image_path, timeout=8):
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                try:
                    future = executor.submit(self.__load_image, image_path)
                    # Wait for the result, raise an exception if it times out
                    image = future.result(timeout=timeout)
                    return image
                except concurrent.futures.TimeoutError:
                    raise concurrent.futures.TimeoutError("")
        except:
            raise ("unexpected error")
    '''

    '''
    except concurrent.futures.TimeoutError:
        raise Exception(f"Opening the image took longer than {timeout} seconds")
    except Exception as e:
        # Handle other exceptions (e.g., file not found, invalid image format)
        raise e
    '''

    #Use zero_shot classification to check if the text represents a product.
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

    #A function that returns the similarity between the passed image and product_title.
    #Timeout if no response.
    def _find_image_match_product_similarity(self, model, processor, image_path_or_url, product_title, time_out=3):
        try:
            try:
                # Fetch the image data
                response = requests.get(image_path_or_url, timeout=time_out)  # Timeout to prevent hanging
                response.raise_for_status()  # Raise an error for HTTP issues

                # Load the image into a file-like object
                img_data = BytesIO(response.content)

                # Open the image
                image = Image.open(img_data)
                    # print(f"Image format: {img.format}, size: {img.size}, mode: {img.mode}")
                    # img.show()  # Display the image
            except requests.exceptions.RequestException as e:
                #print(f"Error fetching the image: {e}")
                return 0
            except Exception as e:
                #print(f"Error processing the image: {e}")
                return 0

            # Resize image to fit within the model's expected input size (224x224 for CLIP)
            image = image.resize((224, 224))  # Resize to 224x224 (adjust depending on model's requirement)

        except (FileNotFoundError, UnidentifiedImageError) as e:
            #print(f"Image load error: {e}")
            return 0

        try:
            # Preprocess the image and text (title)
            inputs = processor(text=[product_title], images=image, return_tensors="pt", padding=True, truncation=True)

            # Get image and text embeddings
            with torch.no_grad():
                outputs = model(**inputs)

            # Compute cosine similarity between image and text embeddings
            image_embeds = outputs.image_embeds
            text_embeds = outputs.text_embeds
            similarity = torch.cosine_similarity(image_embeds, text_embeds)

            return similarity.item()

        except (ValueError, RuntimeError) as e:
            #print(f"Error during inference: {e}")
            return 0

# --------------------------------------------End of functions to apply CLIP models----------------------------------------------------

    #Function that retrieves the largest product image that matches the text (similarity greater than similarity_threshold)
    #initial_wait is the initial wait tiem
    #finding_wait is the wait time until I find the corresponding elements on a webpage.
    def find_product_image(self, product_title, initial_wait=5, finding_wait=3, extra_wait_param=2, final_wait=1, similarity_threshold=0.2):
        self.driver = self.__ensure_browser_open(self.driver)
        self.driver.get(self.product_link)
        try:
            self.driver.maximize_window()
        except WebDriverException as e:
            #print(e)
            pass
        time.sleep(initial_wait)
        try:
            # For example, we wait for a button with 'accept' or 'agree' text to appear
            accept_button = WebDriverWait(self.driver, initial_wait).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow')]"))
            )

            # Click the "Accept" button
            accept_button.click()
            #print("Cookies popup accepted.")

        except Exception as e:
            #print("No cookies popup appeared or there was an issue:", e)
            pass
        heap_of_images = []
        images = ['"product_image"', '"ProductImage"', '"productImage"', '"product-image"', '"product-header"', '"product_header"']
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
            heap_of_images = self.__find_max_img_helper(self.driver, heap_of_images, product_title, finding_wait, extra_wait_param, similarity_threshold)
        else:
            model, processor = self._load_clip_model()
            for web_element in product_im_class_li:
                #case when current element is an image
                if web_element.tag_name == "img":
                    e_img_size = float(web_element.get_attribute('width')) * float(web_element.get_attribute('height'))
                    e_img_url = web_element.get_attribute('src')
                    if not e_img_url:
                        e_img_url = web_element.get_attribute("srcset")
                        pdt_links = e_img_url.split(' ')
                        # Check if image-text similarity is greater than threshold
                        for pdt_url in pdt_links:
                            pdt_url = re.search(self.__url_regex, pdt_url)
                            if pdt_url:
                                similarity = self._find_image_match_product_similarity(model, processor,
                                                                                       pdt_url.group(),
                                                                                       product_title)
                                if (similarity >= similarity_threshold):
                                    heapq.heappush(heap_of_images, (-img_size, -similarity, pdt_url))
                    else:
                        e_similarity = self._find_image_match_product_similarity(model, processor, e_img_url, product_title)
                    # Check if image-text similarity is greater than threshold
                        if (e_similarity >= similarity_threshold and e_img_size and e_img_url and e_similarity):
                            heapq.heappush(heap_of_images, (-e_img_size, -e_similarity, e_img_url))
                heap_of_images = self.__find_max_img_helper(web_element, heap_of_images, product_title, finding_wait, extra_wait_param, similarity_threshold)
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

    #A function that retrieves the best text from webpage. Text need to be the largest product-related
    #initial_wait is the initial wait tiem
    #finding_wait is the wait time until I find the corresponding elements on a webpage.
    #extra_wait_param is the multiple of wait time if a timeout occurs
    def find_product_title(self, initial_wait=5, finding_wait=3, final_wait=1, extra_wait_param=3, text_classifier_threshold=0.7):
        self.driver = self.__ensure_browser_open(self.driver)
        self.driver.get(self.product_link)
        time.sleep(initial_wait)
        try:
            self.driver.maximize_window()
        except WebDriverException as e:
            # print(e)
            pass
            # Wait for the cookies popup to be visible (adjust the selector based on your page's structure)
        try:
            # For example, we wait for a button with 'accept' or 'agree' text to appear
            accept_button = WebDriverWait(self.driver, initial_wait).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow')]"))
            )

            # Click the "Accept" button
            accept_button.click()
            #print("Cookies popup accepted.")

        except Exception:
            #print("No cookies popup appeared or there was an issue:", e)
            pass
        t = None
        heap_of_titles = []
        titlels = ['"title"', '"Title"', '"name"', '"Name"', '"header"', '"Header"', '"Heading"', '"heading"',
                   '"product"', '"Product"']
        list_of_tags = ['h1', 'h2', 'h3', 'span']
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
                #print(self.__viewport_width, self.__viewport_height)
                if i.rect['x'] < 2*self.__viewport_width and i.rect['y'] < 2*self.__viewport_height:
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

    #Finds the matching price. Finds the element with the largest size that has text matches a price regular expression
    #initial_wait is the initial wait tiem
    #finding_wait is the wait time until I find the corresponding elements on a webpage.
    #extra_wait_param is the multiple of wait time if a timeout occurs
    def match_price(self, initial_wait=5, finding_wait=3, final_wait=1, extra_wait_param=3):
    #Code for cookie popup
        reli = []
        p = None
        span = None
        #self.driver = webdriver.Chrome()
        #self.driver.get(self.product_link)
        #self.driver.maximize_window()
        self.driver = self.__ensure_browser_open(self.driver)
        self.driver.get(self.product_link)
        time.sleep(initial_wait)
        # Wait for the cookies popup to be visible (adjust the selector based on your page's structure)
        try:
            # For example, we wait for a button with 'accept' or 'agree' text to appear
            accept_button = WebDriverWait(self.driver, initial_wait).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow')]"))
            )

            # Click the "Accept" button
            accept_button.click()
            #print("Cookies popup accepted.")

        except Exception:
            #print("No cookies popup appeared or there was an issue:", e)
            pass
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
        list_of_tags_simple = ['span']
        prices_xpath = self.__list_to_xPath_helper(prices, list_of_tags)
        prices_xpath_simple = self.__list_to_xPath_helper(prices, list_of_tags_simple)
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
            except TimeoutException:
                try:
                    #Use a simpler xpath if timeout
                    span = self.driver.find_elements(By.XPATH, prices_xpath_simple)
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
                if i.rect['x'] < 2*self.__viewport_width and i.rect['y'] < 2*self.__viewport_height:
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
            #self.driver.close()
            return pri[1]
            #print(pri[1].group())
        time.sleep(final_wait)
        #self.driver.close()
        return 'Not found'

def main():
#----------------------------------------------------------Code for testing purposes-----------------------------------------------------------
    LINK_1 = "https://www.amazon.ca/Hasselblad-X2D-100C-Mirrorless-Digital/dp/B0BYQJJYF7?crid=28CPVU64ZDILM&keywords=x2d&qid=1686387291&sprefix=x2d,aps,104&sr=8-1&ufe=app_do:amzn1.fos.fe67de69-a579-4370-9bc8-5e38fc5a3bcc&linkCode=sl1&tag=fototripper0c-20&linkId=86a81fe2a5d2c15add7be3644a718716&language=en_CA&ref_=as_li_ss_tl"
    LINK_2 = "https://www.htltsupps.com/products/turk-builder?variant=45645992329429&country=US&currency=USD&utm_campaign=sag_organic&srsltid=AfmBOorymJd_yURPj1yzRtHzBnO9LCsrvmHTykzVRjkN0JNN8bcMuNJGN7s&utm_content=YT3-ISUGDlPne_hUsgGNGN0IwFvoUGFe4QwCHgVv4b3gQiFlAkrDLtCh2hS9q_3jXENPucx8rmkvv2s_RGhZyY9uCQ&utm_term=UCLqH-U2TXzj1h7lyYQZLNQQ&utm_medium=product_shelf&utm_source=youtube"
    LINK_3 = "https://www.ebay.com/itm/266718554926?_trkparms=amclksrc%3DITM%26aid%3D777008%26algo%3DPERSONAL.TOPIC%26ao%3D1%26asc%3D20230913095046%26meid%3D51e25bfb1d4643f795b4c510096fa44e%26pid%3D101831%26rk%3D1%26rkt%3D1%26itm%3D266718554926%26pmt%3D0%26noa%3D1%26pg%3D4375194%26algv%3DPersonalizedTopicsV2WithDynamicSizeRanker%26brand%3DNVIDIA&_trksid=p4375194.c101831.m47269&_trkparms=parentrq%3A286d891d1930ab1341bfc352ffffe802%7Cpageci%3A4a47ebce-a22d-11ef-9936-5e9dcb641f54%7Ciid%3A1%7Cvlpname%3Avlp_homepage"
    LINK_COOKIES = "https://store.insta360.com/product/one_x2?insrc=INRNP7I"
    LINK_4 = "https://www.mpb.com/en-us/product/smallhd-indie-7-monitor/sku-2799421"
    LINK_5 = "https://neewer.com/products/neewer-tl120c-rgb-tube-light-with-app-2-4g-dmx-control-66604594?_pos=1&_sid=25a15ce10&_ss=r&ref=AnthonyGallo"
    LINK_6 = "https://www.amazon.com/gp/product/B014U596GO/ref=as_li_tl?ie=UTF8&tag=sousvideevery-20&camp=1789&creative=9325&linkCode=as2&creativeASIN=B014U596GO&linkId=892082d1782f22d10203abec5bed7935&th=1"
    LINK_7 = "https://www.ebay.com/itm/356144750186?_skw=leica+m9&epid=100164147&itmmeta=01JCPWJ6P4Y9373YBJ72A9V9FK&hash=item52ebe19e6a:g:X4wAAOSwu5RnC7Cc&itmprp=enc%3AAQAJAAAA4HoV3kP08IDx%2BKZ9MfhVJKm63WuYlvF0cVTRkbIK%2BWpKuEHrQeUsn0r7Bb9%2FnNfmHUh%2FiwN%2FfoFb3giIedd%2FsEh5i53WRrhq90AhSBPEM16f1ZHWGa3i7on3tCWqPBjQiArYYaIR28ov%2Fyc78v1nqN3riovXDGJRU63OdiK2mSQdclblOac%2FlTB9Y%2FT1YS1thhRxqqRujzi9BvKSYV9w1XaILsVl2GyCpdUrYO03CkJx6WrUuLZwmiUtVYd9pIy9B3BnPBTJsJmqMfE7uSX2OS5JRlGFZvBvHqvfs3pgn4dH%7Ctkp%3ABFBMluvI3OVk"
    LINK_8 = "https://www.capturelandscapes.com/photographer-month-thomas-heaton/"
    LINK_9 = "https://thomasheaton.co.uk/product/my-book/"
    LINK_10 = "https://store.dji.com/product/dji-rs-3?ch=launch-rs3-samholland&clickaid=X3zYImu0We91G3QjtfjeJM7ZOpzMZU12&clickpid=745444&clicksid=7f11750ff3a2407875d68a8470411788&from=dap_unique&pm=custom&utm_campaign=launch-rs3&utm_content=samholland&utm_medium=kol-affiliates&utm_source=yt&vid=116541"
    LINK_11 = "https://store.google.com/config/pixel_8a?hl=en-US&selections=eyJwcm9kdWN0RmFtaWx5IjoiY0dsNFpXeGZPR0U9In0%3D&utm_medium=affiliate_publisher&utm_source=CJ&utm_campaign=GS5348525&utm_content=3586864&CJPID=3586864&CJAID=14460385&dclid=CjkKEQiAxea5BhDd-dLTqu7Ox5oBEiQAqc3-Vqi5ed6H7lxBp3P1XuCjBaeLt53fpiWOmYAvI6po94Dw_wcB&pli=1"
    LINK_12 = "https://www.johnlewis.com/chanel-chance-eau-fraiche-eau-de-parfum-spray/p110479834?size=100ml&istCompanyId=33b56d18-9e28-47e3-815d-8d995bdbeaad&istFeedId=2fd0a202-4923-4f80-971e-8e154c05afed&istItemId=lwqawqwrx&istBid=t&irclickid=wPuVXoWhyxyKTPw2A70VbTfEUkCQ2XUtyXFWTw0&irgwc=1&tmcampid=99&s_afcid=af_116548_Content"
    LINK_13 = "https://www.smokingdadbbq.com/product/complete-double-indirect-setup-guide"
    LINK_14 = "https://www.lttstore.com/products/beanie?variant=39499864080487&country=US&currency=USD&utm_campaign=sag_organic&srsltid=AfmBOoq3d0XOuWSxHD6BP_OL1pkbKczmyjHbo1lkjFKInXNuKG0GzHd7TVQ&utm_content=YT3-61NNpZv4HRfDh8OlSK_DOlJ06ZOUwRKiUc5U2pH5FkJ8dR4J2PiQ9QVpr1yUv4IRVVy1lb_SmBRclvLzG9CRmQ&utm_term=UCXuqSBlHAE6Xw-yeJA0Tunw&utm_medium=product_shelf&utm_source=youtube"
    LINK_15 = "https://www.gregdoucette.com/collections/htlt-core-concepts"
    ex = GenericScraper(LINK_15)
    print(ex.match_price())
    title = ex.find_product_title()
    print(title)
    print(ex.find_product_image(product_title=title))

if __name__ == "__main__":
    main()
    #main()

