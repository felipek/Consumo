Consumo Framework
=================

Consumo is a simple and straightforward framework to create snippets of
web scrapers to obtain data from brazilian mobile phone carriers.  This
project was NOT created to be used for illegal purposes.  Please use it
at your own risk.

Components
----------

### Python Framework

Base class: `ConsumoAbstract`.
Subclass this base class to create new scrapers.

### UNIX CLI

The Python module can also be used as a UNIX program.
Here is the command line interface:

    $ Consumo.py -h
    Usage: __main__ -l || -c <carrier> -u <username> -p <password>
    -l  --list       Lists available carriers
    -c  --carrier    Uses a specific <carrier>
    -u  --username   Uses username <username>
    -p  --password   Uses password <password>
    -h  --help	     This help

### Web service (Django)

The project also contains a very tiny Web service (REST) interface.
All the Web service stuff is abstracted away via a Django module.
Only two methods are supported:

* `consumo/list` to list all the available carriers.
* `consumo/<carrier>` to request a given carrier data.

Two parameters are required: `username` and `password`.
This Web service might change in the feature.
