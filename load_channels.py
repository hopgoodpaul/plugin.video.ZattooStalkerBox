import sys
import urllib
import json
import os
import urlparse
import re, uuid
from time import time
from datetime import datetime
import math
import urllib2
import hashlib
from xml.dom import minidom
import server
import xbmc

key = None;
mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()));
sn = None;
device_id = None;
device_id2 = None;
signature = None;

cache_version = '3'

def is_json(myjson):
  try:
    json_object = json.loads(myjson)
  except ValueError, e:
    return False
  return True

def setMac(nmac):
	global mac;
	
	if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", nmac.lower()):
		mac = nmac;

def getMac():
	global mac;
	return mac;
	
	
def setSerialNumber(serial):
	global sn, device_id, device_id2, signature;
	
	if serial == None:
		return;
	
	elif serial['custom'] == False:
		sn = hashlib.md5(mac).hexdigest().upper()[13:];
		device_id = hashlib.sha256(sn).hexdigest().upper();
		device_id2 = hashlib.sha256(mac).hexdigest().upper();
		signature = hashlib.sha256(sn + mac).hexdigest().upper();
	
	elif serial['custom'] == True:
		sn = serial['sn'];
		device_id = serial['device_id'];
		device_id2 = serial['device_id2'];
		signature = serial['signature'];

def handshake(url):
	global key;
	
	if key != None:
		return;
	
	info = retrieveData(url, values = {
		'type' : 'stb', 
		'action' : 'handshake',
		'JsHttpRequest' : '1-xml'})
		
	key = info['js']['token']
	
	getProfile(url);
	

def getProfile(url):
	global sn, device_id, device_id2, signature;
	
	values = {
		'type' : 'stb', 
		'action' : 'get_profile',
		'hd' : '1',
		'ver' : 'ImageDescription:%200.2.18-r11-pub-254;%20ImageDate:%20Wed%20Mar%2018%2018:09:40%20EET%202015;%20PORTAL%20version:%204.9.14;%20API%20Version:%20JS%20API%20version:%20331;%20STB%20API%20version:%20141;%20Player%20Engine%20version:%200x572',
		'num_banks' : '1',
		'stb_type' : 'MAG254',
		'image_version' : '218',
		'auth_second_step' : '0',
		'hw_version' : '2.6-IB-00',
		'not_valid_token' : '0',
		'JsHttpRequest' : '1-xml'}

	if sn != None:
		values['sn'] = sn;
		values['device_id'] = device_id;
		values['device_id2'] = device_id2;
		values['signature'] = signature;


	info = retrieveData(url, values);


def retrieveData(url, values ):
	global key, mac;
		
	url += '/stalker_portal'
	load = '/server/load.php'
	refer = '/c/'
	timezone = 'America%2FChicago';

	user_agent 	= 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 1812 Mobile Safari/533.3';
	
	if key != None:
		headers 	= { 
			'User-Agent' : user_agent, 
			'Cookie' : 'mac=' + mac + '; stb_lang=en; timezone=' + timezone,
			'Referer' : url + refer,
			'Accept' : '*/*',
			'Connection' : 'Keep-Alive',
			'X-User-Agent' : 'Model: MAG254; Link: Ethernet',
			'Authorization' : 'Bearer ' + key };
	
	else:
		headers 	= { 
			'User-Agent' : user_agent, 
			'Cookie' : 'mac=' + mac+ '; stb_lang=en; timezone=' + timezone,
			'Referer' : url + refer,
			'Accept' : '*/*',
			'Connection' : 'Keep-Alive',
			'X-User-Agent' : 'Model: MAG254; Link: Ethernet' };

	
	data = urllib.urlencode(values);
	req = urllib2.Request(url + load, data, headers);
	resp = urllib2.urlopen(req).read().decode("utf-8");
	
	if not is_json(resp):
		req = urllib2.Request(url + load + '?' + data, headers=headers);
		resp = urllib2.urlopen(req).read().decode("utf-8");

	if not is_json(resp):
		raise Exception(resp)

	info = json.loads(resp)

	return info;


def getGenres(portal_mac, url, serial, path):	
	global key, cache_version;
	
	now = time();
	portalurl = "_".join(re.findall("[a-zA-Z0-9]+", url));
	portalurl = path + '/' + portalurl + '-genres';
	
	setMac(portal_mac);
	setSerialNumber(serial);
	
	if not os.path.exists(path): 
		os.makedirs(path);
	
	if os.path.exists(portalurl):
		#check last time
		with open(portalurl) as data_file: data = json.load(data_file);
		
		if 'version' not in data or data['version'] != cache_version:
			clearCache(url, path);
			
		else:
			time_init = float(data['time']);
			# update 12h
			if ((now - time_init) / 3600) < 12:
				return data;
	
	handshake(url);
	
	info = retrieveData(url, values = {
		'type' : 'itv', 
		'action' : 'get_genres',
		'JsHttpRequest' : '1-xml'})
		
	
	results = info['js']
	
	data = '{ "version" : "' + cache_version + '", "time" : "' + str(now) + '", "genres" : {  \n'

	for i in results:
		alias 	= i["alias"]
		id 		= i["id"]
		title 	= i['title']
		
		data += '"'+ id +'" : {"alias":"'+ alias +'", "title":"'+ title +'"}, \n'

	
	data = data[:-3] + '\n}}'

	with open(portalurl, 'w') as f: f.write(data.encode('utf-8'));
	
	return json.loads(data.encode('utf-8'));
	
def getVoD(portal_mac, url, serial, path):	
	now = time();
	portalurl = "_".join(re.findall("[a-zA-Z0-9]+", url));
	portalurl = path + '/' + portalurl + '-vod';
	
	setMac(portal_mac);
	setSerialNumber(serial);
	
	if not os.path.exists(path):
		os.makedirs(path)
	
	if os.path.exists(portalurl):
		#check last time
		with open(portalurl) as data_file: data = json.load(data_file);
	
		if 'version' not in data or data['version'] != cache_version:
			clearCache(url, path);
			
		else:
			time_init = float(data['time']);
			# update 12h
			if ((now - time_init) / 3600) < 12:
				return data;
	
	handshake(url);
	
	data = '{ "version" : "' + cache_version + '", "time" : "' + str(now) + '", "vod" : [  \n'
	
	page = 1;
	pages = 0;
	total_items = 1.0;
	max_page_items = 1.0;
	
	while True:
		info = retrieveData(url, values = {
			'type' : 'vod', 
			'action' : 'get_ordered_list',
			'sortby' : 'added',
			'not_ended' : '0',
			'p' : page,
			'fav' : '0',
			'JsHttpRequest' : '1-xml'})
		
		total_items = float(info['js']['total_items']);
		max_page_items = float(info['js']['max_page_items']);
		pages = math.ceil(total_items/max_page_items);
		
		results = info['js']['data']


		for i in results:
			name 	= i["name"]
			cmd 	= i['cmd']
			logo 	= i["screenshot_uri"]
		
			data += '{"name":"'+ name +'", "cmd":"'+ cmd +'", "logo":"'+ logo +'"}, \n'

		page += 1;
		if page > pages or page == 10:
			break;

	data = data[:-3] + '\n]}'

	with open(portalurl, 'w') as f: f.write(data.encode('utf-8'));
	
	return json.loads(data.encode('utf-8'));


def orderChannels(channels):
      	n_data = {};
      	for i in channels:	
      		number 		= i["number"];
      		n_data[int(number)] = i;
      	
      	ordered = sorted(n_data);
      	data = {};
      	for i in ordered:	
      		data[i] = n_data[i];
      		
      	return data.values();


def getAllChannels(portal_mac, url, serial, path):

	added = False;
	
	now = time();
	
	portalurl = "_".join(re.findall("[a-zA-Z0-9]+", url));
	portalurl = path + '/' + portalurl
	
	setMac(portal_mac);
	setSerialNumber(serial);
	
	if not os.path.exists(path):
		os.makedirs(path)

	if os.path.exists(portalurl):
		#check last time
		with open(portalurl) as data_file: data = json.load(data_file);
	
		if 'version' not in data or data['version'] != cache_version:
			clearCache(url, path);
			
		else:
			time_init = float(data['time']);
			# update 12h
			if ((now - time_init) / 3600) < 12:
				return data;
	
	handshake(url);
	
	genres = getGenres(portal_mac, url, serial, path);
	genres = genres["genres"];
	
	info = retrieveData(url, values = {
		'type' : 'itv', 
		'action' : 'get_all_channels',
		'JsHttpRequest' : '1-xml'})
	
	
	results = info['js']['data'];

	data = '{ "version" : "' + cache_version + '", "time" : "' + str(now) + '", "channels" : { \n'

	for i in results:
		id 		= i["id"]
		number 	= i["number"]
		name 	= i["name"]
		cmd 	= i['cmd']
		logo 	= i["logo"]
		tmp 	= i["use_http_tmp_link"]
		genre_id 	= i["tv_genre_id"];
		
		genre_title = genres[genre_id]['title'];
		
		_s1 = cmd.split(' ');	
		_s2 = _s1[0];
		if len(_s1)>1:
			_s2 = _s1[1];
		
		added = True;
		data += '"' + id + '": {"number":"'+ number +'", "name":"'+ name +'", "cmd":"'+ cmd +'", "logo":"'+ logo +'", "tmp":"'+ str(tmp) +'", "genre_id":"'+ str(genre_id) +'", "genre_title":"'+ genre_title +'"}, \n'


	page = 1;
	pages = 0;
	total_items = 0;
	max_page_items = 0;

	while True:
		# retrieve adults
		info = retrieveData(url, values = {
			'type' : 'itv', 
			'action' : 'get_ordered_list',
			'genre' : '10',
			'p' : page,
			'fav' : '0',
			'JsHttpRequest' : '1-xml'})
	
		total_items = float(info['js']['total_items']);
		max_page_items = float(info['js']['max_page_items']);
		pages = math.ceil(total_items/max_page_items);
	
		results = info['js']['data']

		for i in results:
			id 		= i["id"]
			number 	= i["number"]
			name 	= i["name"]
			cmd 	= i['cmd']
			logo 	= i["logo"]
			tmp 	= i["use_http_tmp_link"]
			genre_id 	= i["tv_genre_id"];
			genre_title = genres[genre_id]['title'];
		
			data += '"' + id + '": {"number":"'+ number +'", "name":"'+ name +'", "cmd":"'+ cmd +'", "logo":"'+ logo +'", "tmp":"'+ str(tmp) +'", "genre_id":"'+ str(genre_id) +'", "genre_title":"'+ genre_title +'"}, \n'
			
			added = True;

		page += 1;
		if page > pages:
			break;
	

	if not added:
		data = data + '\n}}';
	else:
		data = data[:-3] + '\n}}';

	
	with open(portalurl, 'w') as f: f.write(data.encode('utf-8'));
	
	return json.loads(data.encode('utf-8'));

def getEPG(path, guide, channels):	
    global cache_version;
    
    now = time();
    portalurl = path + '/zattoo-epg.xml';
    
    clearCache('zattoo-epg.xml', path);
    
    if not os.path.exists(path):
        os.makedirs(path);

    if os.path.exists(portalurl):
        #check last time
        xmldoc = minidom.parse(portalurl);

        itemlist = xmldoc.getElementsByTagName('tv');

        version = itemlist[0].attributes['cache-version'].value;

        if version != cache_version:
            clearCache('zattoo-epg.xml', path);

        else:
            time_init = float(itemlist[0].attributes['cache-time'].value);
            # update 2h
            if ((now - time_init) / 3600) < 2:
                return xmldoc.toxml(encoding='utf-8');
        
    doc = minidom.Document();
    base = doc.createElement('tv');
    base.setAttribute("cache-version", cache_version);
    base.setAttribute("cache-time", str(now));
    base.setAttribute("generator-info-name", "ZattooStalkerBox Plugin");
    base.setAttribute("generator-info-url", "http://www.xmltv.org/");
    doc.appendChild(base)
    
    title = None
    
    for c in guide['channels']:
        channelID = c['cid']
        
        c_entry = doc.createElement('channel');
        c_entry.setAttribute("id", str(channelID));
        base.appendChild(c_entry)
        
        
        for group in channels['channel_groups']:
            for channelInfo in group['channels']:
                if channelID == channelInfo['cid']:
                    title = channelInfo['title']
                    dn_entry = doc.createElement('display-name');
                    dn_entry_content = doc.createTextNode(title);
                    dn_entry.appendChild(dn_entry_content);
                    c_entry.appendChild(dn_entry);
        
        for program in c['programs']:
        
            start_time 	= datetime.fromtimestamp(int(program['s']));
            stop_time	= datetime.fromtimestamp(int(program['e']));
            
            pg_entry = doc.createElement('programme');
            pg_entry.setAttribute("start", start_time.strftime('%Y%m%d%H%M%S -0000'));
            pg_entry.setAttribute("stop", stop_time.strftime('%Y%m%d%H%M%S -0000'));
            pg_entry.setAttribute("channel", str(channelID));
            base.appendChild(pg_entry);
            
            t_entry = doc.createElement('title');
            #t_entry.setAttribute("lang", "en");
            t = program['t']
            if t is not None:
                t.encode('ascii', 'ignore')
            else:
                t = ""
            t_entry_content = doc.createTextNode(t);
            t_entry.appendChild(t_entry_content);
            pg_entry.appendChild(t_entry);
            
            d_entry = doc.createElement('desc');
            #d_entry.setAttribute("lang", "en");
            et = program['et']
            if et is not None:
                et.encode('ascii', 'ignore')
            else:
                et = ""
            d_entry_content = doc.createTextNode(et);
            d_entry.appendChild(d_entry_content);
            pg_entry.appendChild(d_entry);
            
            
    #xbmc.log(doc.toxml(encoding='utf-8'))
    with open(portalurl, 'w') as f: f.write(doc.toxml(encoding='utf-8'));
    
    return doc.toxml(encoding='utf-8');
    



def retriveUrl( url, channel):
	
	#setMac(portal_mac);
	#setSerialNumber(serial);
		
	#if 'matrix' in channel:
	#	return retrieve_matrixUrl(url, channel);
		
	#else:
    return retrive_defaultUrl(url, channel);
		
	
		
def retrive_defaultUrl(url, channel):
    	
    cmd = channel;
    s = cmd.split(' ');
    url = s[0];
    
    if len(s)>1:
        url = s[1];
    zapi = server.ZapiSession('/Users/paulhopgood/Documents/')
    zapi.init_session('paulhopgood@gmail.com', 'v1p3rdns')
    params = {'cid': url, 'stream_type': 'hls'}
    resultData = zapi.exec_zapiCall('/zapi/watch', params)
    if resultData is not None:
        url = resultData['stream']['watch_urls'][0]['url']
        xbmc.log(url)
	return url;


def retrieve_matrixUrl(url, channel):

	channel = channel.split('/');
	channel = channel[len(channel) -1];
	
	url += '/stalker_portal/server/api/matrix.php?channel=' + channel + '&mac=' + mac;
	
	# RETRIEVE THE 1 EXTM3U
	request = urllib2.Request(url)
	response  = urllib2.urlopen(request);
	data = response.read().decode("utf-8");

	_s1 = data.split(' ');	
	data = _s1[0];
	if len(_s1)>1:
		data = _s1[len(_s1) -1];
	
	return data;



def retriveVoD(portal_mac, url, serial, video):
	
	setMac(portal_mac);
	setSerialNumber(serial);
		
	s = video.split(' ');
	url = s[0];
	if len(s)>1:
		url = s[1];

	
	url = url.replace('TOMTOM:', 'http://');
	

	# RETRIEVE THE 1 EXTM3U
	request = urllib2.Request(url)
	response  = urllib2.urlopen(request);
	url = response.geturl();


	# RETRIEVE THE 1 EXTM3U
	request = urllib2.Request(url)
	#request.get_method = lambda : 'HEAD'
	response  = urllib2.urlopen(request);
	data = response.read().decode("utf-8");
	data = data.splitlines();
	data = data[len(data) - 1];
	
	# RETRIEVE THE 2 EXTM3U
	url = response.geturl().split('?')[0];
	url_base = url[: -(len(url) - url.rfind('/'))]
	return url_base + '/' + data;

def clearCache(url, path):
	
	portalurl = "_".join(re.findall("[a-zA-Z0-9]+", url));
	
	for root, dirs, files in os.walk(path):
		for file in files:
			if file.startswith(portalurl):
				os.remove(root + '/' + file);


def main(argv):

      if argv[0] == 'load':
      	#getAllChannels(argv[1], argv[2], None, argv[4]);
      	data = getAllChannels(argv[1], argv[2], json.loads(argv[3]), argv[4]);
      	
      	
      elif argv[0] == 'genres':
      	getGenres(argv[1], argv[2], None, argv[3]);

      elif argv[0] == 'vod':
      	getVoD('', argv[1], argv[2]);
      	
      elif argv[0] == 'channel':     	
      	url = retriveUrl(argv[1], argv[2], json.loads(argv[3]), argv[4], argv[5]);
      	print url
	
      elif argv[0] == 'vod_url':
      	url = retriveVoD('', argv[1], argv[2]);
      	print url
      	
      elif argv[0] == 'cache':
      	clearCache(argv[1], argv[2]);
      	
      elif argv[0] == 'profile':
      	handshake(argv[1]);
      	
      elif argv[0] == 'epg':
      	url = getEPG(argv[1], argv[2], json.loads(argv[3]), argv[4]);
      	#print url



if __name__ == "__main__":
   main(sys.argv[1:])


