# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import selenium
from selenium import webdriver
import time
from selenium.webdriver.chrome.service import Service

#print_hi('PyCharm')
PATH = "C:/Program Files/chromedriver-win64/chromedriver.exe"
service = Service(executable_path=PATH)
#driver.get("www.plink.bio/@ziywang50/3519")
driver = webdriver.Chrome()
driver.get("www.google.com")
#input_element = driver.find_element(By.CLASS_NAME, "gLFyf")
#time.sleep(10)
driver.quit()
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
