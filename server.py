import json
import urllib
import urllib2
from urlparse import urlparse, parse_qs
import load_channels
import SocketServer
import socket
import SimpleHTTPServer
import string,cgi,time
import os
from os import curdir, sep
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import config
import re
import threading
import base64
import traceback
import datetime

addon       = xbmcaddon.Addon()
addonname   = addon.getAddonInfo('name')
addondir    = xbmc.translatePath( addon.getAddonInfo('profile') ) 

#portals = None;
server = None;


class TimeoutError(RuntimeError):
    pass

class AsyncCall(object):
    def __init__(self, fnc, callback = None):
        self.Callable = fnc
        self.Callback = callback

    def __call__(self, *args, **kwargs):
        self.Thread = threading.Thread(target = self.run, name = self.Callable.__name__, args = args, kwargs = kwargs)
        self.Thread.start()
        return self

    def wait(self, timeout = None):
        self.Thread.join(timeout)
        if self.Thread.isAlive():
            raise TimeoutError()
        else:
            return self.Result

    def run(self, *args, **kwargs):
        self.Result = self.Callable(*args, **kwargs)
        if self.Callback:
            self.Callback(self.Result)

def watchURL(cmd):
    zapi = ZapiSession(xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8'))
    zapi.init_session(addon.getSetting('username'), addon.getSetting('password'))
    params = {'cid': cmd, 'stream_type': 'hls'}
    resultData = zapi.exec_zapiCall('/zapi/watch', params)
    url = ""
    if resultData is not None:
        if addon.getSetting('hack') == 'true':
            url = resultData['stream']['watch_urls'][0]['url']
            matching = "zattoo-hls-live.akamaized.net"
            new_str = "zba1-0-hls-live.zahs.tv"
            url = url.replace(matching, new_str)
        else:
            url = resultData['stream']['watch_urls'][0]['url']
    return url

class AsyncMethod(object):
    def __init__(self, fnc, callback=None):
        self.Callable = fnc
        self.Callback = callback

    def __call__(self, *args, **kwargs):
        return AsyncCall(self.Callable, self.Callback)(*args, **kwargs)

def Async(fnc = None, callback = None):
    if fnc == None:
        def AddAsyncCallback(fnc):
            return AsyncMethod(fnc, callback)
        return AddAsyncCallback
    else:
        return AsyncMethod(fnc, callback)

class ZapiSession:
    ZAPI_AUTH_URL = 'https://zattoo.com'
    ZAPI_URL = 'http://zattoo.com'
    CACHE_ENABLED = False
    CACHE_FOLDER = None
    COOKIE_FILE = None
    ACCOUNT_FILE = None
    HttpHandler = None
    Username = None
    Password = None
    AccountData = None

    def __init__(self, cacheFolder):
        if cacheFolder is not None:
            self.CACHE_ENABLED = True
            self.CACHE_FOLDER = cacheFolder
            self.COOKIE_FILE = os.path.join(cacheFolder, 'session.cache')
            self.ACCOUNT_FILE = os.path.join(cacheFolder, 'account.cache')
        self.HttpHandler = urllib2.build_opener()
        self.HttpHandler.addheaders = [('Content-type', 'application/x-www-form-urlencoded'),('Accept', 'application/json')]
    
    def init_session(self, username, password):
        self.Username = username
        self.Password = password
        return (self.CACHE_ENABLED and self.restore_session()) or self.renew_session()
        
    def restore_session(self):
        if os.path.isfile(self.COOKIE_FILE) and os.path.isfile(self.ACCOUNT_FILE):
            with open(self.ACCOUNT_FILE, 'r') as f:
                accountData = json.loads(base64.b64decode(f.readline()))
            if accountData['success'] == True:
                self.AccountData = accountData
                with open(self.COOKIE_FILE, 'r') as f:
                    self.set_cookie(base64.b64decode(f.readline()))
                return True
        return False
        
    def extract_sessionId(self, cookieContent):
        if cookieContent is not None:
            return re.search("beaker\.session\.id\s*=\s*([^\s;]*)", cookieContent).group(1)
        return None
    
    def persist_accountData(self, accountData):
        with open(self.ACCOUNT_FILE, 'w') as f:
            f.write(base64.b64encode(json.dumps(accountData)))
    
    def persist_sessionId(self, sessionId):
        with open(self.COOKIE_FILE, 'w') as f:
            f.write(base64.b64encode(sessionId))
    
    def set_cookie(self, sessionId):
        self.HttpHandler.addheaders.append(('Cookie', 'beaker.session.id=' + sessionId))
    
    def request_url(self, url, params):
        try:
            response = self.HttpHandler.open(url, urllib.urlencode(params) if params is not None else None)
            if response is not None:
                sessionId = self.extract_sessionId(response.info().getheader('Set-Cookie'))
                if sessionId is not None:
                    self.set_cookie(sessionId)
                    if self.CACHE_ENABLED:
                        self.persist_sessionId(sessionId)
                return response.read()
        except Exception:
            pass
        return None
    
    def exec_zapiCall(self, api, params, context='default'):
        url = self.ZAPI_AUTH_URL + api if context == 'session' else self.ZAPI_URL + api
        content = self.request_url(url, params)
        if content is None and context != 'session' and self.renew_session():
            content = self.request_url(url, params)
        if content is None:
            return None
        try:
            resultData = json.loads(content)
            if resultData['success'] == True:
                return resultData
        except Exception:
            pass
        return None
    
    def fetch_appToken(self):
        handle = urllib2.urlopen(self.ZAPI_URL + '/')
        html = handle.read()
        return re.search("window\.appToken\s*=\s*'(.*)'", html).group(1)
    
    def announce(self):
        api = '/zapi/session/hello'
        params = {"client_app_token" : self.fetch_appToken(),
                  "uuid"    : "d7512e98-38a0-4f01-b820-5a5cf98141fe",
                  "lang"    : "en",
                  "format"	: "json"}
        resultData = self.exec_zapiCall(api, params, 'session')
        return resultData is not None
    
    def login(self):
        api = '/zapi/account/login'
        params = {"login": self.Username, "password" : self.Password}
        accountData = self.exec_zapiCall(api, params, 'session')
        if accountData is not None:
            self.AccountData = accountData
            if self.CACHE_ENABLED:
                self.persist_accountData(accountData)
            return True
        return False		
    
    def renew_session(self):
        return self.announce() and self.login()


class MyHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        if 'live.m3u' in self.path:
            args = parse_qs(urlparse(self.path).query);
            cmd = args['channel'][0];   
            url = watchURL(cmd)
            self.send_response(301)
            self.send_header('Location', url)
            self.end_headers()
    
    
    def do_GET(self):
        global server;
        #global portals
        try:
            if re.match('.*channels-([0-9])\..*|.*channels\..*', self.path):
                host = self.headers.get('Host');
                
                EXTM3U = "#EXTM3U\n";
                counting = 0
                try:
                    date = datetime.datetime.now()
                    if date is None: date = datetime.date.today()
                    else: date = date.date()
                    
                    fromTime = int(time.mktime(date.timetuple()))
                    toTime = fromTime + 3600
                    zapi = ZapiSession(xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8'))
                    zapi.init_session(addon.getSetting('username'), addon.getSetting('password'))
                    api = '/zapi/v2/cached/channels/%s?details=False' % (zapi.AccountData['account']['power_guide_hash'])
                    guide = '/zapi/v2/cached/program/power_guide/' + zapi.AccountData['account']['power_guide_hash'] + '?end=' + str(toTime) + '&start=' + str(fromTime)
                    xbmc.log(str(guide))
                    channels = zapi.exec_zapiCall(api, None)
                    guided = zapi.exec_zapiCall(guide, None)
                    xbmc.log(str(guided))
                    
                    for group in channels['channel_groups']:
                        for channeling in group['channels']:
                            title = channeling['title']
                            cid = channeling['cid']
                            parameters = urllib.urlencode( { 'channel' : cid });
                            EXTM3U += '#EXTINF:-1, tvg-id="' + str(counting) + '" tvg-name="' + title + '", '+ title +' \n';
                            EXTM3U += 'http://' + host +'/live.m3u?' + parameters + '\n\n';
                            counting += 1
                        
                except Exception as e:
                        EXTM3U += '#EXTINF:-1, tvg-id="Error" tvg-name="Error" tvg-logo="" group-title="Error", ' + str(e) + '\n';
                        EXTM3U += 'http://\n\n';

                self.send_response(200)
                self.send_header('Content-type',	'application/x-mpegURL')
                self.send_header('Connection',	'close')
                self.send_header('Content-Length', len(EXTM3U))
                self.end_headers()
                self.wfile.write(EXTM3U.encode('utf-8'))
                self.finish()
                
            elif 'live.m3u' in self.path:
                
                args = parse_qs(urlparse(self.path).query);
                cmd = args['channel'][0];
                url = watchURL(cmd)
                self.send_response(301)
                self.send_header('Location', url)
                self.end_headers()

                
            elif 'epg.xml' in self.path:
				
				args = parse_qs(urlparse(self.path).query);
				numportal = args['portal'][0];
				
				portal = portals[numportal];
				
				try:
					xml = load_channels.getEPG(portal['mac'], portal['url'], portal['serial'], addondir);
				except Exception as e:
					xml  = '<?xml version="1.0" encoding="ISO-8859-1"?>'
					xml += '<error>' + str(e) + '</error>';
					
				
				self.send_response(200)
				self.send_header('Content-type',	'txt/xml')
				self.send_header('Connection',	'close')
				self.send_header('Content-Length', len(xml))
				self.end_headers()
				self.wfile.write(xml)
				self.finish()
                 
            elif 'stop' in self.path:
				msg = 'Stopping ...';
            	
				self.send_response(200)
				self.send_header('Content-type',	'text/html')
				self.send_header('Connection',	'close')
				self.send_header('Content-Length', len(msg))
				self.end_headers()
				self.wfile.write(msg.encode('utf-8'))
				server.socket.close();
                
            elif 'online' in self.path:
				msg = 'Yes. I am.';
            	
				self.send_response(200)
				self.send_header('Content-type',	'text/html')
				self.send_header('Connection',	'close')
				self.send_header('Content-Length', len(msg))
				self.end_headers()
				self.wfile.write(msg.encode('utf-8'))

            
            else:
            	self.send_error(400,'Bad Request');
            	
        except IOError:
            self.send_error(500,'Internal Server Error ' + str(IOError))
        





@Async
def startServer():
    global server;
    server_enable = addon.getSetting('server_enable');
    port = int(addon.getSetting('server_port'));
    
    if server_enable != 'true':
        return;
        
    try:
        server = SocketServer.TCPServer(('', port), MyHandler);
        server.serve_forever();
        
    except KeyboardInterrupt:
        
        if server != None:
            server.socket.close();


def serverOnline():
	
	port = addon.getSetting('server_port');
	
	try:
		url = urllib.urlopen('http://localhost:' + str(port) + '/online');
		code = url.getcode();
		
		if code == 200:
			return True;
	
	except Exception as e:
		return False;

	return False;


def stopServer():
	
	port = addon.getSetting('server_port');
	
	try:
		url = urllib.urlopen('http://localhost:' + str(port) + '/stop');
		code = url.getcode();

	except Exception as e:
		return;

	return;

if __name__ == '__main__':
    xbmc.log("trying to start the server")
    startServer();
    xbmc.log("server started")
	

        
