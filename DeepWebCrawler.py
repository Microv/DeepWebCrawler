import re
import socks
import socket
import requests
import urllib2
import sys, getopt
from bs4 import BeautifulSoup

class DeepWebCrawler:

	pattern = '''href=["'](.[^"']+)["']'''
	domain_regex = r'[http,https]://(.+\.onion)'
	crawled_urls = []
	crawled_domains = []
	counter = 0
	quick_mode = False	
	seed = ''
	verbose = False
	output_filename = ''
	


	def __init__(self, seed, quick_mode=True, verbose=False):
		
		self.init_socket()
		
		self.seed = seed
		self.quick_mode = quick_mode
		self.verbose = verbose

		self.output_filename = 'crawled.txt'
		with open(self.output_filename, 'w') as f:
			f.write('Seed '+seed+'\n')
	

	def init_socket(self):
		# urllib2 uses the socket module's create_connection() function.
		# The way the DNS request is done won't work for our Tor connection,
		# so we need to jerry-rig our own create_connection() for urllib2
		def create_connection(addr, timeout=None, src=None):
			sock = socks.socksocket()
			sock.connect(addr)
			return sock

		# Set our proxy to TOR
		socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', 9050)
 		socket.socket = socks.socksocket
		socket.create_connection = create_connection # force the socket class to use our new create_connection()
		

	def req(self, url):
		if not (url.endswith('.onion') or url.endswith('/') or url.endswith('.html') or url.endswith('.php') or url.endswith('.asp') or url.endswith('.htm') or url.endswith('.aspx') or url.endswith('.xml') or url.endswith('.jsp') or url.endswith('.jspx') or url.endswith('.txt') or url.endswith('Main_Page')): 
			return ''
		proxy_support = urllib2.ProxyHandler({"socks5" : "127.0.0.1:9050"})
		opener = urllib2.build_opener(proxy_support) 
		opener.addheaders = [('User-agent', 'Mozilla/5.0')]
		if self.verbose:
			print ' [+] Opening URL...'
		return opener.open(url).read()


	def crawl(self, url, action=None, depth=0):

		if action == None:
			action = self.getTitle

		if self.verbose:	
			print ' [+] Crawling '+url
		self.crawled_urls.append(url)
		try:
			request = self.req(url)
		except Exception as e:
			if self.verbose:
				print ' [-] '+str(e)
			return
		if self.verbose:	
			print ' [+] URL is reachable'	
		
		infotolog = action(url, request)

		if '.onion' in url:	
			domain = re.search(self.domain_regex, url).group(1)
			if domain not in self.crawled_domains:
				self.crawled_domains.append(domain)
				self.counter += 1
				print ' [+] '+str(self.counter)+' domains crawled'
		else:
			domain = ''

		if len(infotolog) > 0: 
			log = infotolog+' @ '+domain+' @ Depth '+str(depth)
			with open(self.output_filename, "a") as f:
				f.write(log+'\n')
			if self.verbose:	
				print ' [+] Found '+log	

		for nexturl in re.findall(self.pattern, request, re.L):
			if nexturl in self.crawled_urls:
				continue
			new_domain = re.search(self.domain_regex, nexturl)
			if new_domain == None:
				continue
			new_domain = new_domain.group(1)	 
			if new_domain == domain:
				if url != nexturl and not self.quick_mode:
					self.crawl(nexturl, action, depth)
			else:
				self.crawl(nexturl, action, depth+1)	


	def getTitle(self, url, request):
		if '.onion' in url:	
			domain = re.search(self.domain_regex, url).group(1)
			if domain in self.crawled_domains:
				return ''

		title = re.search('<title>([^<]+)', request)
		if title == None:
			title = 'Unknown'
		else:
			title = title.group(1).strip()
		return title


	def grep(self, url, request):
		log = ''
		toSearch = self.toSearch.lower()
		for line in request.split('\n'):
			line = line.lower()
			if toSearch in line:
				log += line.strip()+' - '
		
		if len(log) > 0:
			return log[:-3]		
		else:
			return log


	def getWordsFile(self, url, request):
		if '.onion' not in url:	
			return ''
		else:
			domain = re.search(self.domain_regex, url).group(1) 	

		soup = BeautifulSoup(request)
		# kill all script and style elements
		for script in soup(["script", "style"]):
			script.extract()    # rip it out
		texts = re.sub('[ ,\n,\t,\W]+',' ',soup.get_text())
		
		with open(domain+'.txt', 'a') as f:
			f.write(texts) 
		return 'Keywords'						



def main():
	usage = 'Usage: '+sys.argv[0]+' [Options] {Action}' 
	help = usage+'\n'\
	+'OPTIONS:\n'+\
	'-h: Print this summary page\n'+\
	'-s <SEED>: Set seed to begin crawling\n'+\
	'-l: Disable Quick mode, the crawling will be more accurale but slow\n'+\
	'-v: Increase verbosity level\n'+\
	'ACTIONS\n'+\
	'-t: Get title of crawled pages\n'+\
	'-g <KEYWORD>: Search for KEYWORD in crawled pages\n'+\
	'-w: Get a word file for each site\n'+\
	'EXAMPLES:\n'+\
	'\t'+sys.argv[0]+' -v -t\n'+\
	'\t'+sys.argv[0]+' -v -g deepweb\n'+\
	'\t'+sys.argv[0]+' -w -v\n'+\
	'\t'+sys.argv[0]+' -s http://torlinkbgs6aabns.onion -t'

	try:
		opts, args = getopt.getopt(sys.argv[1:], "hs:lvtg:w")
	except getopt.GetoptError:
		print usage
		sys.exit(2)	

	seed = ''	
	action = 0
	verbose = False
	toSearch = ''
	quick_mode = True
	for opt, arg in opts:
		if opt == '-h':
			print help
			sys.exit()
		elif opt == '-s':
			seed = arg
		elif opt == '-l':
			quick_mode = False		
		elif opt == '-v':
			verbose = True	
		elif opt == '-t':
			action = 1
		elif opt == '-g':
			toSearch=arg
			action = 2
		elif opt == '-w':
			action = 3					
	
	if seed == '':
		seed = 'http://thehiddenwiki.org/'
		#seed = 'http://zqktlwi4fecvo6ri.onion/wiki/index.php/Main_Page'
		#seed = 'http://torlinkbgs6aabns.onion/'
		#seed = 'http://32rfckwuorlf4dlv.onion/'
		#seed = 'http://wikitjerrta4qgz4.onion/'
	
	Crawler = DeepWebCrawler(seed, quick_mode, verbose)			
	if action == 0:
		print usage
		sys.exit(2)
	elif action == 1:
		Crawler.crawl(seed, action=Crawler.getTitle)
	elif action == 2:
		Crawler.toSearch=toSearch					 			
		Crawler.crawl(seed, action=Crawler.grep)
	elif action == 3:
		Crawler.crawl(seed, action=Crawler.getWordsFile)
			


if __name__ == '__main__':
	main()
			