import threading
import UserAgents
import requests
from bs4 import BeautifulSoup
import re
import os
import traceback

server = 'http://www.mangabz.com/'
imgServer = 'http://image.mangabz.com/'


def get_searchList(search_text, page):
    headers = {
        'User-Agent': UserAgents.get_user_agent_phone()
    }
    url = '{0}/search?title={1}&page={2}'.format(server, search_text, page)
    html = requests.get(url, headers=headers).text

    soup = BeautifulSoup(html, 'html.parser')
    bookList = soup.find_all('a', class_='manga-item')
    results = []
    for book in bookList:
        temp = {}
        temp['url'] = '/info' + book['href']

        img = book.find('img')
        tag = soup.new_tag('div')
        tag['class'] = 'manga-right'

        for item in book.find_all('p'):
            item.name = 'div'
            tag.append(item)
        book.append(img)
        book.append(tag)
        # print(book)
        temp['html'] = ''.join(str(item) for item in book)
        results.append(temp)

    return results


def get_bookInfo(bookID):
    results = {}
    headers = {
        'User-Agent': UserAgents.get_user_agent_phone()
    }
    html = requests.get('{0}/{1}'.format(server, bookID), headers=headers).text
    soup = BeautifulSoup(html, 'html.parser')

    results['title'] = soup.find('p', class_='detail-main-title').text
    results['author'] = soup.find('p', class_='detail-main-subtitle').find('a').find('span').text
    results['content'] = soup.find('p', class_='detail-main-content').text + soup.find('p',
                                                                                       class_='detail-main-content').text
    results['imgUrl'] = soup.find('img', class_='detail-bar-bg')['src']

    detailList = []
    for item in soup.find('div', class_='detail-list').find_all('a'):
        detail = {}
        detail['url'] = item['href']
        detail['name'] = item.text.strip()
        detailList.append(detail)
    results['list'] = detailList
    results['list'].reverse()

    return results


def get_chapterImages(bookID, chapterID):
    results = {}
    images = []

    headers = {
        'User-Agent': UserAgents.get_user_agent_phone()
    }
    chapterUrl = server + '/m{0}'.format(chapterID)
    html = requests.get(chapterUrl, headers=headers, timeout=10).text

    urlNum = '1'
    spare = re.search(',\'[0-9].*?jpg', html).group().split('|')
    if spare is not None and len(spare) > 4 and spare[len(spare) - 3].isdigit() and int(spare[len(spare) - 3]) < 50:
        urlNum = spare[len(spare) - 3]
    else:
        urlNum = re.search('[0-9]\\.[0-9]\\.[0-9]/[0-9]*/', html).group()
        urlNum = urlNum.split('/')[1]

    imgsList = re.findall('[0-9]+?_[0-9]+', html)
    imgsList.sort(key=lambda x: int(str(x).split('_')[0]))

    type = '.jpg'

    if len(imgsList) > 0:
        checkImg = requests.get(imgServer + '{0}/{1}/{2}/'.format(urlNum, bookID, chapterID) + imgsList[0] + type)
        if checkImg.status_code == 404:
            type = '.png'

    for img in imgsList:
        img_url = imgServer + '{0}/{1}/{2}/'.format(urlNum, bookID, chapterID) + img + type
        images.append(img_url)

    results['imgs'] = images
    return results


if __name__ == '__main__':
    print(get_chapterImages('12818', '147738'))
