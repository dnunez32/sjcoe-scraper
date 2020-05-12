import requests
from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import time
from concurrent.futures import ThreadPoolExecutor

usernames = [] #Usernames scraped from sjcoe.org
urlsToHarvest = []
validDepartmentUrls = []
numberOfPagesToCrawl = 0
crawlCounter = 0
"""
accepts a crawl counter to assist in formatting xpath
returns xpath to next button
"""
def getXPath(crawlCounter):
    return '/html/body/form/div[3]/main/div[2]/div/div[1]/div/div[2]/div[2]/table/tbody/tr[22]/td/a[{counter}]'.format(counter = str(crawlCounter))

"""
accepts source of web page and hasPageNumber flag which lets us know whether or not
we need to try and obtain the number of pages to scrape. This is ran when viewing a
department's first page primarily
"""
def parseData(source,pageNumber, hasPageNumber = False):
    try:
        soup = BeautifulSoup(source, 'html.parser')

        if hasPageNumber:
            departmentHeader = soup.select('div > h1')
            if departmentHeader[0] != '':
                department = departmentHeader[0].getText().strip()
                print("[*] Harvesting users within", department)
        paginationControl = soup.find('td', attrs={'colspan': '5'})

        # Get all rows within pagination control
        table = soup.find('table', attrs={'id': 'ctl00_ContentPlaceHolder1_staffList'})
        rows = table.find_all('tr')

        print(str(len(rows) - 2), "Emails found on Page #", str(pageNumber))

        for row in rows:
            cols = row.find_all('td')
            parsedLine = re.findall('\S+@\S+', str(cols[0]))  # First Column
            if len(parsedLine) != 0:
                if "mailto:" in parsedLine[0] and "@sjcoe.net" in parsedLine[0]:  # Has email in line
                    emailAddress = parsedLine[0].strip().split('mailto:')[1].split('@')[0]  # Parse accordingly
                    if emailAddress[0] != '':
                        usernames.append(emailAddress)
        if not hasPageNumber:
            xpathResults = paginationControl.find_all('a')[-1]
            numberOfPagesToCrawl = int(xpathResults.get_text())
            print("Number of Pages:", str(numberOfPagesToCrawl))

    except IndexError:
        print("Number of Pages: 1")
        return True

    return False
"""
accepts a url to check if department has usernames to obtain
"""
def isValidDepartment(url):
    response = requests.get(url, stream=True) #Visit site
    if not "No Records Found!" in response.text: #Look in source for text
        print("[*] - Valid Department Url: ", url)
        validDepartmentUrls.append(url) #Add url to valid department lisst


def startScraping():
    #Setup selenium web driver
    options = webdriver.ChromeOptions()
    options.add_argument("headless") #Dont Show Browser
    options.add_argument('log-level=3') #Only show errors
    driver = webdriver.Chrome(executable_path=r"chromedriver.exe",options=options) #Path to Driver



    url = 'https://sjcoe.org/ourteam.aspx?deptID={departmentId}'

    #determine valid departments to crawl
    print("[*] - Enumerating valid department URLs")
    for i in range(1,100):
        urlsToHarvest.append(url.format(departmentId=str(i)))

    with ThreadPoolExecutor(max_workers=15) as executor:
       for departmentUrl in urlsToHarvest:
           executor.submit(isValidDepartment(departmentUrl))

    #validDepartmentUrls = ['https://sjcoe.org/ourteam.aspx?deptID=5']

    print("Valid department urls: ", validDepartmentUrls)

    print("[*] {validDepartments} Departments Found".format(validDepartments=len(validDepartmentUrls)))

    with ThreadPoolExecutor(max_workers=15) as executor:
        for validUrl in validDepartmentUrls:
            numberOfPagesToCrawl = 0
            crawlCounter = 1
            driver.get(validUrl)
            try:
                isSinglePage = parseData(driver.page_source, crawlCounter, hasPageNumber=False)
                if not isSinglePage:
                    next_button = driver.find_element_by_xpath(getXPath(crawlCounter))
                    while next_button or crawlCounter > numberOfPagesToCrawl:
                        # Wait for table to load
                        time.sleep(1)
                        next_button = driver.find_element_by_xpath(getXPath(crawlCounter))
                        next_button.click()
                        crawlCounter += 1
                        time.sleep(1)
                        isSinglePage = parseData(driver.page_source, crawlCounter, hasPageNumber=True)

            except NoSuchElementException:
                print("[*] Moving to next department")
                continue

    print("[*] - Found " + str(len(usernames)) + " Usernames")
    saveUsernames(usernames)
"""
accepts a list of usernames to save to usernames.txt
"""
def saveUsernames(usernames):
    try:
        with open("usernames.txt", "w") as outfile:
            outfile.write("\n".join(usernames))
        print("[*] Usernames output to usernames.txt")
    except:
        print("[*] Error occurred writing users to usernames.txt")

if __name__ == "__main__":
    startScraping()