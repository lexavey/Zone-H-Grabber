from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import InvalidSessionIdException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
import os,base64,math,sys
from pathlib import Path
from lxml import etree
import argparse
 
parser = argparse.ArgumentParser(description="Zone-H Grabber",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("nick", help="Nickname to scrapped")
args = parser.parse_args()

SELENIUM_SESSION_FILE = './selenium_session'
def build_driver():
    options = webdriver.ChromeOptions()
    options.set_capability("loggingPrefs", {'performance': 'ALL'})
    options.headless = True
    options.add_argument('--disable-gpu')
    options.add_argument("--disable-infobars")
    options.add_argument("--enable-file-cookies")
    options.add_argument("--incognito")

    if os.path.isfile(SELENIUM_SESSION_FILE):
        session_file = open(SELENIUM_SESSION_FILE)
        session_info = session_file.readlines()
        session_file.close()

        executor_url = session_info[0].strip()
        session_id = session_info[1].strip()

        driver = webdriver.Remote(command_executor=executor_url, options=options)
        # prevent annoying empty chrome windows
        driver.close()
        driver.quit() 

        # attach to existing session
        driver.session_id = session_id
        return driver

    # driver = webdriver.Chrome(options=options, port=SELENIUM_PORT)
    driver = webdriver.Remote(
      command_executor='http://127.0.0.1:4444/wd/hub',
      options=options
    )

    session_file = open(SELENIUM_SESSION_FILE, 'w')
    session_file.writelines([
        driver.command_executor._url,
        "\n",
        driver.session_id,
        "\n",
    ])
    session_file.close()

    return driver


Path("result").mkdir(parents=True, exist_ok=True)

def parse(s,txt):
    tree = etree.HTML(txt)
    sv=open('result/'+s+'.txt', 'a')
    for a in tree.xpath('//a[contains(text(),\''+s+'\')]/following::td[6]'):
        sv.write(a.text.strip()+"\n")
        print(a.text.strip())


def scrap(nick):
    try:
        print("Starting program")
        driver = build_driver()
        driver.get("http://zone-h.org/archive/notifier="+nick)
    except (InvalidSessionIdException,WebDriverException) as e:
        print("Error : "+str(e))
        print("Retry")
        os.remove(SELENIUM_SESSION_FILE)
        driver = build_driver()
        driver.get("http://zone-h.org/archive/notifier="+nick)
        pass
    
    
    try:
        ele_total_notification = driver.find_element("xpath", '//*[@id="FullPart"]/p/b[1]')
    except NoSuchElementException:
        def is_captcha():
            try:
                ele_total_notification = driver.find_element("xpath", '//*[@id="FullPart"]/p/b[1]')
                return False
            except NoSuchElementException:
                return True
                pass
        def start():
            html_source_code = driver.execute_script("return document.body.innerHTML;")
            ele_captcha = driver.find_element("xpath", '//*[@id=\"cryptogram\"]')
            # get the captcha as a base64 string
            img_captcha_base64 = driver.execute_async_script("""
                var ele = arguments[0], callback = arguments[1];
                ele.addEventListener('load', function fn(){
                  ele.removeEventListener('load', fn, false);
                  var cnv = document.createElement('canvas');
                  cnv.width = this.width; cnv.height = this.height;
                  cnv.getContext('2d').drawImage(this, 0, 0);
                  callback(cnv.toDataURL('image/jpeg').substring(22));
                }, false);
                ele.dispatchEvent(new Event('load'));
                """, ele_captcha)
            
            # save the captcha to a file
            with open(r"captcha.jpg", 'wb') as f:
                f.write(base64.b64decode(img_captcha_base64))
            print('please open captcha.jpg')
            user_input = input('Type captcha here: ')
            print('submit captcha : '+user_input)
            driver.find_element("name", 'captcha')
            driver.find_element("name", 'captcha').send_keys(user_input)
            driver.find_element("name", 'captcha').submit()
        while is_captcha():
            start()
            
        print('Captcha done, scrapping now')
        exit()
        pass
    total_notification = ele_total_notification.text.strip()
    total_page = math.ceil(int("".join(filter(str.isdigit, total_notification)))/25)
    if total_page>=50:
        total_page=50
    print('total notification '+total_notification)
    for p in range(1,total_page+1):
        print("http://zone-h.org/archive/notifier="+nick+"/page="+str(p))
        driver.get("http://zone-h.org/archive/notifier="+nick+"/page="+str(p))
        html_source_code = driver.execute_script("return document.body.innerHTML;")
        parse(nick,html_source_code)
    driver.close()
    os.remove(SELENIUM_SESSION_FILE)

if __name__ == '__main__':
    try:
        scrap(args.nick)
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
