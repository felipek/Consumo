from django.shortcuts import render_to_response
from django.http import HttpResponse
import Consumo
import demjson

def list(request):
	"""List method - list all available carriers."""
	list = Consumo.carrier_classes().keys()
	return HttpResponse(demjson.encode(list), mimetype="application/json")

def carrier(request, carrier):
	"""Carrier method (carrier): gets general info."""
	username = None
	password = None

	if request.GET.has_key("username"):
		username = request.GET["username"]
	if request.GET.has_key("password"):
		password = request.GET["password"]

	carriers = Consumo.carrier_classes()
	if not carriers.has_key(carrier):
		return HttpResponseNotFound("<h1>Unknown carrier</h1>")
	
	obj = carriers[carrier][1]

	try:
		server = obj(username, password)
		server.parse()

		return HttpResponse(demjson.encode(server.data()),
			mimetype="application/json")
	except Consumo.ConsumoException, e:
		# FIXME: better error handling (authentication!).
		return HttpResponse(demjson.encode(e), status = 500)
