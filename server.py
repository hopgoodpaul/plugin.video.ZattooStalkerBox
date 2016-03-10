import json
import urllib
import urllib2
from urlparse import urlparse, parse_qs
import load_channels
import SocketServer
import socket
import SimpleHTTPServer
import string,cgi,time
from os import curdir, sep
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import config
import re
import threading

addon       = xbmcaddon.Addon()
addonname   = addon.getAddonInfo('name')
addondir    = xbmc.translatePath( addon.getAddonInfo('profile') ) 

portals = None;
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


class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        global portals, server;
        

        try:
            if re.match('.*channels-([0-9])\..*|.*channels\..*\?portal=([0-9])', self.path):

            	EXTM3U = "#EXTM3U\n";
            	
            	try:
                    data = '{ "name": "channel 1" , "number": "1", "name": "channel 2", "number": "2", "name": "channel 3", "number": "3" }';
                    data = json.loads(data.encode('utf-8'));

                    for i in data:
                        name 		= i["name"];
                        number 		= i["number"];
                        EXTM3U += '#EXTINF:-1, tvg-id="' + number + '" tvg-name="' + name + '", ' + name + '\n';
                        EXTM3U += 'http://localhost/live.m3u?\n\n';

            	except Exception as e:
                        EXTM3U += '#EXTINF:-1, tvg-id="Error" tvg-name="Error" tvg-logo="" group-title="Error", ' + str(e) + '\n';
                        EXTM3U += 'http://\n\n';
        	
        	
                self.send_response(200)
                self.send_header('Content-type',	'application/x-mpegURL')
                #self.send_header('Content-type',	'text/html')
                self.send_header('Connection',	'close')
                self.send_header('Content-Length', len(EXTM3U))
                self.end_headers()
                self.wfile.write(EXTM3U.encode('utf-8'))
                self.finish()
                
            elif 'live.m3u' in self.path:
				
				args = parse_qs(urlparse(self.path).query);
				cmd = args['channel'][0];
				tmp = args['tmp'][0];
				numportal = args['portal'][0];
				
				portal = portals[numportal];
				
				url = load_channels.retriveUrl(portal['mac'], portal['url'], portal['serial'], cmd, tmp);
				
				self.send_response(301)
				self.send_header('Location', url)
				self.end_headers()
				self.finish()
                
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
	global portals, server;
	
	server_enable = addon.getSetting('server_enable');
	port = int(addon.getSetting('server_port'));
	
	if server_enable != 'true':
		return;

	portals = { 
		'1' : config.portalConfig('1'), 
		'2' : config.portalConfig('2'), 
		'3' : config.portalConfig('3') };

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
	startServer();
	

        

