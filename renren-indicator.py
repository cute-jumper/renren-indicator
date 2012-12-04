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

import urllib, urllib2, cookielib, datetime, json, glib, os, pynotify, hashlib, re, os
from bs4 import BeautifulSoup
from ConfigParser import ConfigParser

# App settings
app_dir = os.path.dirname(os.path.abspath(__file__)) # Remember to change here
app_icon = os.path.join(app_dir, 'renren-indicator.jpg')
app_setting_file = os.path.join(app_dir, '.user')
image = 'file://' + app_icon

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
        postdata = urllib.urlencode({'email':self.email,
                                     'password':self.password,
                                     })        
        req = urllib2.Request(url=posturl, data=postdata)
        html = urllib2.urlopen(req).read()
        # print html
        data = json.loads(html)
        print 'response:',data
        homeurl = data.get('homeUrl', None)
        if not homeurl:
            print 'Log in error!'
            exit(0)
        homepage = urllib2.urlopen(homeurl).read()
        print '[Message]: Log in successful!'
        return homepage        

    def send_notification(self, title, description):
        """send feed updates to notify-osd"""
        pynotify.init(title)
        n = pynotify.Notification(title, description, image)
        n.set_hint_string('x-canonical-append','')
        n.show()
            
    def parse_news(self, homepage):
        soup = BeautifulSoup(re.sub('(?<=charset=)gb2312|gbk|gb18030', 'utf-8', homepage, flags=re.I))
        ret = []
        for article in soup.find_all('article'):
            if 'a-feed' in article.get('class', []):
                title = article.h3.get_text(strip=True)
                description = ''
                for div in article.find_all('div'):
                    if 'content-main' in div.get('class', []) or 'content-main-big' in div.get('class', []):
                        description = div.get_text(strip=True)
                ret.append({'title': title, 'description': description})
        return ret
    def do_update(self):
        homepage = self.login()
        news = self.parse_news(homepage)
        for item in news:
            md5val = hashlib.md5(item['title'] + item['description']).hexdigest()
            if md5val not in self.cached:
                self.cached.append(md5val)
                self.send_notification(item['title'], item['description'])
                print 'title:', item['title']
                print 'description:', item['description']
                print

if __name__ == "__main__":
    import time, sys
    interval = 5 * 60
    if len(sys.argv) == 2:
        interval = int(sys.argv[1])
    print 'Update interval: %ds' %interval
    rd = RenrenIndicator(app_setting_file)
    while True:
        try:
            rd.do_update()
            time.sleep(interval)
        except KeyboardInterrupt:
            print '\n[Message]: Exit renren-indicator...'
            break
