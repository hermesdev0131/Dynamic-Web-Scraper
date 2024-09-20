  # Refer Selenium with python documentation for details.

from selenium import webdriver
from selenium.webdriver.common.keys import Keys   # keys class keys in document i.e RETURN, F1, ALT etc.
from selenium.webdriver.common.by import By       # By class locate element within document.
import time



driver = webdriver.Chrome()     # Instance of chrome webdriver is created.
driver.get("http:/www.python.org") # driver.get method will navigate page by URL.
assert "Python" in driver.title  # Assertion to confirm title has word python in it.
elem = driver.find_element(By.NAME, "q")
elem.clear()
elem.send_keys("pycon")
elem.send_keys(Keys.RETURN)
assert "No results found." not in driver.page_source
time.sleep(6)
driver.close()