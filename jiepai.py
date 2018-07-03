import os
from urllib.parse import urlencode

import pymongo as pymongo
import requests
from requests.exceptions import RequestException
import re
import json
from bs4 import BeautifulSoup
from config import *
from hashlib import  md5
from multiprocessing import Pool

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]
#urlencode 把字典转成url后缀形式
#注意把字符串转成json，前后的""在匹配的时候也不要保留，同时中间的变量名不能有转义\可用replace去掉\
#group(n)代表正则表达式第n个括号内容
#html的content是二进制，图片用，而text是原始字符
#pool相当于生成所有的参数然后多进程循环
#brew services start mongodb  启动mongodb  或者mongod？
#用完后brew services stop mongodb
#mongo
#[x*20 for x in range(11)]生成一个列表

def get_html(offset,keyword):
    data={
        'offset': offset,
        'format': 'json',
        'keyword': '街拍',
        'autoload': 'true',
        'count': '20',
        'cur_tab': 1
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'
    }
    try:
        response = requests.get('https://www.toutiao.com/search_content/?'+urlencode(data), headers=headers)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        return None

def get_url(text):
    pattern = re.compile('"article_url": "(.*?)"',re.S)
    results=re.findall(pattern, text)
    return results
    #print(results)

def get_detail(url):

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        return None

def parse_page(text,url):
    soup = BeautifulSoup(text,'lxml')
    title = soup.select('title')[0].get_text()
    #print(title)
    img_pattern=re.compile('gallery: JSON.parse\\("(.*?)"\\),',re.S)
    #gallery = soup.select('gallery')[0].get_text()
    #print(gallery)
    result = re.search(img_pattern,text)
    #print(result.group(1))
    if result:
        #print(type(result.group(1)))
        temp=result.group(1).replace("\\","")
        #print(temp)
        data=json.loads(temp)
        #print(type(data))
        if data and 'sub_images' in data.keys():
            sub_images=data.get('sub_images')
            images=[item.get('url') for item in sub_images]
            return {
                'title':title,
                'images':images,
                'url':url
            }


def save_to_mongo(text):
    if db[MONGO_TABEL].insert(text):
        print('储存成功',text)
        return True
    return False

def download_img(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            save_img(response.content) #content 返回二进制内容，而text返回网页内容
        return None
    except RequestException:
        print('请求图片出错')
        return None

def save_img(text):
    #0 ，1，2 分别和后面的format对应
    file='{0}/{1}.{2}'.format(os.getcwd(),md5(text).hexdigest(),'jpg')
    if not os.path.exists(file):
        with open(file,'wb') as f:
            f.write(text)
            f.close()

def main(index):

    html = get_html(index,'街拍')
    results = get_url(html)
    #print(results)
    for result in results:
        htmlx=get_detail(result)
        #print(htmlx)
        page = parse_page(htmlx,result)
        #print(page)
        save_to_mongo(page)
        for img in page['images']:
            download_img(img)




if __name__=='__main__':
    groups = [x*20 for x in range(11)]
    #print(groups)
    pool=Pool()

    pool.map(main,groups)
