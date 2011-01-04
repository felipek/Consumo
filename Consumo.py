#!/usr/bin/python
# Consumo Scraper
#
# Software to extract usage data from brazilian carriers.
# Please do *NOT* use it for illegal purposes.
#
# Patches & fixes: Felipe Kellermann <felipek@nyvra.net>
# $Revision$

from BeautifulSoup import BeautifulSoup
from UserDict import UserDict
import urllib2
import re
import getopt
import sys
import inspect


__version__ = "1.0"


class ConsumoException(Exception):
	"""Consumo exception."""


class ConsumoField(UserDict):
	"""Consumo field represents a piece of content with a name+label."""
	def __init__(self, name, value, label = None):
		UserDict.__init__(self)
		self["name"] = name
		self["value"] = value
		if label is not None:
			self["label"] = label


class ConsumoAbstract:
	"""Abstract carrier implementation. Carriers MUST subclass this class."""
	def __init__(self, baseurl, username = None, password = None):
		cookie = urllib2.HTTPCookieProcessor()
		debug = urllib2.HTTPHandler()
		self._opener = urllib2.build_opener(debug, cookie)
		self._baseurl = baseurl
		self._data = { 'info' : [], 'consume' : [] }

		self.setUsername(username)
		self.setPassword(password)

		urllib2.install_opener(self._opener)

		# Both attributes are required: parse (method) & version (string).
		try:
			getattr(self, 'parse') and getattr(self, 'version')
		except:
			raise NotImplementedError

		# Adds first field: carrier + version.
		name = self.__class__.__name__[7:].lower()
		self._data['info'].append(ConsumoField('carrier', u'%s-%s' %
			(name, self.__class__.version)))

	def request(self, handler, url = '', data = None):
		"""Method used to request server/carrier data."""
		final = self._baseurl + '/' + url

		request = urllib2.Request(final)
		request.add_header('User-Agent', "Consumo/%s" % __version__)
		request.add_header('Accept-Encoding', 'gzip')
		if data is not None:
			request.add_data(data)
		descriptor = self._opener.open(request)
		data = descriptor.read()
		descriptor.close()

		soup = BeautifulSoup(data)
		handler(soup)

	def setUsername(self, username):
		"""Sets a username (often this is not just the 'username')."""
		self._username = username

	def setPassword(self, password):
		"""Sets a password."""
		self._password = password

	def data(self):
		"""Returns raw data containing server/carrier data."""
		return self._data


class ConsumoVivo(ConsumoAbstract):
	"""Carrier: Vivo."""
	version = "1.0"

	def __init__(self, username, password):
		base = 'https://servicos.vivo.com.br/meuvivo/appmanager/portal'
		ConsumoAbstract.__init__(self, base, username, password)

	# Handler: login.
	def _parseLogin(self, soup):
		box = soup.find('div', { 'class' : 'boxDadosConteudo floatLeft' })
		if box is None:
			raise ConsumoException("Password/username problem")
		else:
			boxd = box.findAll('dd')
			self._data['info'].append(ConsumoField('linha', boxd[0].text))
			self._data['info'].append(ConsumoField('plano', boxd[2].text))
			self._data['info'].append(ConsumoField('protoclo', boxd[3].text))
			self._data['info'].append(ConsumoField('data', boxd[4].text))

		box = soup.find('span', { 'class' : 'txtLaranja txtGrande'})
		if box is not None:
			self._data['info'].append(ConsumoField('pontos', box.text))

	# Handler: trafego.
	def _parseTrafego(self, soup):
		boxTrafego = soup.find('div', { 'class' : 'conteudoTrafego'})
		if boxTrafego is not None:
			for node in boxTrafego.findAll('b'):
				data = re.split('trafegados no (.*): ([^ ]*)', node.text)
				if len(data) == 4:
					consume = data[2].replace(',', '.')
					field = ConsumoField("consume", consume, data[1])
					self._data["consume"].append(field)

	# Handler: saldo.
	def _parseSaldo(self, soup):
		saldo = soup.find('td', { 'class' : 'txtAzul volTd' })
		if saldo is not None and len(saldo.text) > 0:
			self._data['info'].append(ConsumoField('saldo', saldo.text))
	
	def parse(self):
		# Login.
		url = 'vivoLogin?_nfpb=true&_windowLabel=login_1&' + \
			'login_1_actionOverride=%2Fbr%2Fcom%2Fvivo%2Fvol%2Fportal%2Flogin%2FdoLogin'
		data = "ddd=%s&linha=%s&senhaIni=senha&senha=%s&login_1%%7BactionForm.captcha%%7D:" % \
			(self._username[:2], self._username[2:], self._password)
		self.request(self._parseLogin, url, data)

		# Trafego.
		url = 'vivo?_nfpb=true&_pageLabel=pages_consultarTrafegoDados_page&_nfls=false'
		self.request(self._parseTrafego, url)

		# Saldo.
		url = 'vivo?_nfpb=true&_pageLabel=pages_consultarSaldoParcial_page&_nfls=false'
		self.request(self._parseSaldo, url)


def carrier_classes():
	"""Returns a list of carriers (name, class name, class object)."""
	carriers = {}
	classes = inspect.getmembers(sys.modules[__name__], inspect.isclass)
	for name, obj in classes:
		if issubclass(obj, ConsumoAbstract) and getattr(obj, 'parse', None):
			symbol = name[7:].lower()
			carriers[symbol] = [name, obj]

	return carriers


def usage():
	"""Returns usage message."""

	return "Usage: %s -l || -c <carrier> -u <username> -p <password>\n" \
		"-l\t--list\t\tLists available carriers\n" \
		"-c\t--carrier\tUses a specific <carrier>\n" \
		"-u\t--username\tUses username <username>\n" \
		"-p\t--password\tUses password <password>\n" \
		"-h\t--help\t\tThis help" % __name__


def main():
	carrier = None
	username = None
	password = None

	try:
		opts, args = getopt.getopt(sys.argv[1:], "hlc:u:p:",
			["list", "carrier=", "username=", "password="])
		for option, value in opts:
			if option in ('-h', '--help'):
				print usage()
				sys.exit(0)
			elif option in ('-l', '--list'):
				carriers = carrier_classes()
				for carrier in carriers.keys():
					print "%s - %s - %s" % (carrier,
						carriers[carrier][0], carriers[carrier][1].version)
				sys.exit(0)
			elif option in ('-u', '--username'):
				username = value
			elif option in ('-p', '--password'):
				password = value
			elif option in ('-c', '--carrier'):
				carrier = value

	except getopt.GetoptError, e:
		print e
		print usage()

	if carrier == None or username == None or password == None:
		print "Error: missing arguments (either list carrier or use a carrier)."
		print usage()
		sys.exit(1)

	carriers = carrier_classes()
	if carriers.has_key(carrier):
		obj_carrier = carriers[carrier][1]

		obj = obj_carrier(username, password)
		obj.parse()
		print obj.data()
	else:
		print "Unknown carrier: %s (use -l to get the carriers list)" % carrier

if __name__ == '__main__':
	main()
