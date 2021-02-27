# -*- coding: utf-8 -*-
#from .plugin import blueprint, menu, plugin_load, plugin_unload, plugin_info
from .plugin import P
blueprint = P.blueprint
menu = P.menu
plugin_info = P.plugin_info
plugin_load = P.logic.plugin_load
plugin_unload = P.logic.plugin_unload
process_telegram_data = P.logic.process_telegram_data
