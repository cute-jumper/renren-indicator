#! /usr/bin/env python
#-*- coding: utf-8 -*-
# author: qjp
# date: <2012-12-04 Tue>

# Configuration format
'''
[user info]
username = foo@bar.com
password = guesswhat
realname = superman
'''

import urllib, urllib2, cookielib, datetime, json, glib, os, pynotify, hashlib, re
from bs4 import BeautifulSoup
from ConfigParser import ConfigParser

# App settings
app_dir = os.path.dirname(os.path.abspath(__file__)) # Remember to change here
app_icon = os.path.join(app_dir, 'renren-indicator.jpg')
app_setting_file = os.path.join(app_dir, '.user')
app_icon_file = 'file://' + app_icon
app_cache_dir = os.path.join(app_dir, 'cache')
if not os.path.exists(app_cache_dir):
    os.mkdir(app_cache_dir)
    print '[Message]: mkdir', app_cache_dir

class RenrenIndicator(object):
    def __init__(self, fn):
        self.cached = []
        # Parse user information
        if not os.path.exists(fn):
            print "Configuration file not exist! Please create one."
            exit(0)
        parser = ConfigParser()
        parser.read(fn)
        self.email, self.password, self.realname = parser.get('user info', 'username'), parser.get('user info', 'password'), parser.get('user info', 'realname')
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)
        
    def login(self):
        homepage = urllib2.urlopen('http://www.renren.com/home').read()
        if homepage.find(self.realname) != -1:
            print '[Message]: update'
            return homepage
        now = datetime.datetime.now()
        timestamp = str(now.year) + str(now.month) + str(now.day) + str(now.hour) + str(now.second) + str(now.microsecond/1000)
        posturl = 'http://www.renren.com/ajaxLogin/login?1=1&uniqueTimestamp=' + timestamp
        data = self.get_response(posturl)
        while data.get('failCode', 0) == 512:
            print "Failed, try to retrieve the verification code..."
            data = self.get_response(posturl, need_icode=True)
        homeurl = data.get('homeUrl', None)
        if not homeurl or data.get('code') != True:
            print 'Log in error!'
            exit(0)
        homepage = urllib2.urlopen(homeurl).read()
        print '[Message]: Log in successful!'
        return homepage        
    def get_response(self, posturl, need_icode=None):
        if need_icode:
            import random, cStringIO
            from PIL import Image
            icode_url = 'http://icode.renren.com/getcode.do?t=web_login&rnd=%f' %(random.random())
            img = Image.open(cStringIO.StringIO(urllib2.urlopen(icode_url).read()))
            img.show()
            postdata = urllib.urlencode({'email':self.email,
                                         'password':self.password,
                                         'icode': raw_input("Verification code: "),
                                         # Can not omit the following parameter!!!
                                         'captcha_type': 'web_login',
                                         })
        else:
            postdata = urllib.urlencode({'email':self.email,
                                         'password':self.password,
                                         })        
        req = urllib2.Request(url=posturl, data=postdata)
        html = urllib2.urlopen(req).read()
        data = json.loads(html)
        return data 

    def send_notification(self, title, description, image):
        """send feed updates to notify-osd"""
        pynotify.init(title)
        n = pynotify.Notification(title, description, image)
        n.set_hint_string('x-canonical-append','')
        n.show()
            
    def parse_news(self, homepage):
        soup = BeautifulSoup(re.sub('(?<=charset=)gb2312|gbk|gb18030', 'utf-8', homepage, flags=re.I))
        ret = []
        for article in soup.find_all('article'):
            if 'a-feed' in article.get('class', []) and article.h3:
                title = article.h3.get_text(strip=True)
                description = ''
                for div in article.find_all('div'):
                    attr = div.get('class', None)
                    if attr and ('content-main' in attr or 'content-main-big' in attr or 'rich-content-new' in attr):
                        description = div.get_text(strip=True)
                for img in article.aside.find_all('img'):
                    try:
                        print "[Message]: Try to use `title' in <img>..."
                        image_name = img['title'] + ".jpg"
                    except KeyError:
                        print "[Message]: Try to use `data-name' in <figure>..."
                        image_name = article.aside.figure['data-name'] + ".jpg"
                    image_path = os.path.join(app_cache_dir, image_name)
                    if not os.path.exists(image_path):
                        print '[Message]: Get image for', image_name
                        urllib.urlretrieve(img['src'], image_path)
                ret.append({'title': title, 'description': description, 'image': image_path})
        # sys.exit(0)
        return ret
    def do_update(self):
        homepage = self.login()
        news = self.parse_news(homepage)
        for item in reversed(news):
            md5val = hashlib.md5(item['title'] + item['description']).hexdigest()
            if md5val not in self.cached:
                self.cached.append(md5val)
                self.send_notification(item['title'], item['description'], item['image'])
                print 'title:', item['title']
                print 'description:', item['description']
                print 'image path:', item['image']
                print

if __name__ == "__main__":
    import time, sys
    interval = 5 * 60
    if len(sys.argv) == 2:
        interval = int(sys.argv[1])
    print '[Message]: Update interval = %ds' %interval
    rd = RenrenIndicator(app_setting_file)
    while True:
        try:
            rd.do_update()
            time.sleep(interval)
        except KeyboardInterrupt:
            print '\n[Message]: Exit renren-indicator...'
            break
