#!/usr/bin/python
# coding: utf-8
# Consumo Scraper
#
# Software to extract usage data from brazilian carriers.
# Please do *NOT* use it for illegal purposes.
#
# Patches & fixes: Felipe Kellermann <felipek@nyvra.net>
# $Revision$

from BeautifulSoup import BeautifulSoup
from UserDict import UserDict
from string import Template
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
		self._opener = urllib2.build_opener(cookie)
		self._baseurl = baseurl
                self._data = { 'info': [], 'consume': [], 'financial': [], 'extra': [] }

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
		self._data['extra'].append(ConsumoField('Carrier', u'%s-%s' %
			(name, self.__class__.version)))

	def request(self, handler, url = '', data = None):
		"""Method used to request server/carrier data."""
		final = self._baseurl + '/' + url

		request = urllib2.Request(final)
		request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_5; de-de) AppleWebKit/534.15+ (KHTML, like Gecko) Version/5.0.3 Safari/533.19.4')
		if data is not None:
			request.add_data(data)
		descriptor = self._opener.open(request)
		data = descriptor.read()
		descriptor.close()

		soup = BeautifulSoup(data)
		handler(soup)

	def setUsername(self, username):
		"""Sets a username (often this is not just the 'username')."""
		if username.startswith('0'):
			username = username[1:]
		self._username = username

	def setPassword(self, password):
		"""Sets a password."""
		self._password = password

	def data(self):
		"""Returns raw data containing server/carrier data."""
		return self._data

        def printData(self):
            print '\nAccount Information:'
            self.printCategory(self._data['info'])
            print '\nConsumption Information:'
            self.printCategory(self._data['consume'])
            print '\nFinancial Information:'
            self.printCategory(self._data['financial'])
            print '\nExtra Information:'
            self.printCategory(self._data['extra'])

        def printCategory(self, cat):
            for item in cat:
                print item['name'] + ': ', item['value']


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
			self._data['info'].append(ConsumoField('Linha', boxd[0].text))
			self._data['info'].append(ConsumoField('Plano', boxd[2].text))
			self._data['info'].append(ConsumoField('Protocolo', boxd[3].text))
			self._data['info'].append(ConsumoField('Data', boxd[4].text))

		box = soup.find('span', { 'class' : 'txtLaranja txtGrande'})
		if box is not None:
			self._data['info'].append(ConsumoField('Pontos', box.text))

	# Handler: trafego.
	def _parseTrafego(self, soup):
		data = []
		boxTrafego = soup.find('div', { 'class' : 'conteudoTrafego'})
		if boxTrafego is not None:
			for node in boxTrafego.findAll('b'):
				data = re.split('trafegados no (.*): ([^ ]*)', node.text)
				if len(data) == 4:
					consume = data[2].replace(',', '.')
					field = ConsumoField('Consumo de dados', consume, 'Consumo (Mb)')
					self._data['consume'].append(field)

		if len(data) == 0:
			field = ConsumoField('consume', 'Temp. indisponivel', 'Consumo (Mb)')
			self._data['consume'].append(field)

        def _parseAccountHistory(self, soup):
          invoiceUrl = Template(self._baseurl + "/vivo?_nfpb=true&_windowLabel=suaConta_1&\
suaConta_1_actionOverride=%2Fbr%2Fcom%2Fvivo%2Fvol%2Fportlets%2Fsuaconta%2FconsultarImagemArquivoFatura&\
suaConta_1{actionForm.cicloSelecionado}=$date&suaConta_1{actionForm.formatoArquivo}=PDF")
            
          lines = soup.findAll('tr')
          if lines is not None:
              for row in lines[1:]:
                cols = row.findAll('td', limit=4)
                if len(cols) == 4:
                    content = Template(u'\n\tMês: $month\n\tValor: R$$ $value\n\tSituação: $status\n\tBoleto: $invoice\n')
                    fileUrl = invoiceUrl.substitute(date=cols[1].text)
                    self._data['financial'].append(ConsumoField('Invoice', content.substitute(month=cols[0].text, value=cols[2].text, status=cols[3].text, invoice=fileUrl)))

	# Handler: saldo.
	def _parseSaldo(self, soup):
		saldo = soup.find('td', { 'class' : 'txtAzul volTd' })
		if saldo is not None and len(saldo.text) > 0:
			self._data['info'].append(ConsumoField('Saldo', saldo.text, 'Saldo Estimado'))
		else:
			self._data['info'].append(ConsumoField('Saldo', 'Temp. indisponivel', 'Saldo Estimado'))
	
	def parse(self):
                # Login.
		url = 'vivoLogin?_nfpb=true&_windowLabel=login_1&' + \
			'login_1_actionOverride=%2Fbr%2Fcom%2Fvivo%2Fvol%2Fportal%2Flogin%2FdoLogin'
		data = "ddd=%s&linha=%s&senhaIni=senha&senha=%s&login_1%%7BactionForm.captcha%%7D:" % \
			(self._username[:2], self._username[2:], self._password)
		self.request(self._parseLogin, url, data)

	        # Account payment history
                url = 'vivo?_nfpb=true&_pageLabel=pages_gerencieSuaConta_page&_nfls=false'
                self.request(self._parseAccountHistory, url)

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
		"-h\t--help\t\tThis help" % sys.argv[0]


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
		obj.printData()
	else:
		print "Unknown carrier: %s (use -l to get the carriers list)" % carrier

if __name__ == '__main__':
	main()
