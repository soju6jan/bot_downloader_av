# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback

# third-party
from flask import Blueprint, request, Response, send_file, render_template, redirect, jsonify, session, send_from_directory 
from flask_socketio import SocketIO, emit, send
from flask_login import login_user, logout_user, current_user, login_required

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler, path_data, socketio, check_api, SystemModelSetting
from framework.util import Util
from plugin import get_model_setting, Logic, default_route, PluginUtil

# 패키지
# 로그

class P(object):
    package_name = __name__.split('.')[0]
    logger = get_logger(package_name)
    blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
    menu = { 
        'main' : [package_name, u'봇 다운로드 - AV'],
        'sub' : [
            ['receive', u'수신'], ['broadcast', u'방송'], ['log', u'로그']
        ], 
        'category' : 'torrent',
        'sub2' : {
            'receive' : [
                ['setting', u'설정'], ['list', u'수신 목록']
            ],
            'broadcast' : [
                ['setting', u'설정'], ['list', u'방송 목록']
            ]
        }
    }  
    plugin_info = {
        'version' : '0.2.0.0',
        'name' : 'bot_downloader_av',
        'category_name' : 'torrent',
        'developer' : 'soju6jan',
        'description' : u'AV 토렌트 수신 & 방송 처리',
        'home' : 'https://github.com/soju6jan/bot_downloader_av',
        'more' : '',
    }
    ModelSetting = get_model_setting(package_name, logger)
    logic = None
    module_list = None
    home_module = 'torrent'
   


def initialize():
    try:
        app.config['SQLALCHEMY_BINDS'][P.package_name] = 'sqlite:///%s' % (os.path.join(path_data, 'db', '{package_name}.db'.format(package_name=P.package_name)))
        PluginUtil.make_info_json(P.plugin_info, __file__)
        ###############################################
        from .logic_receive_av import LogicReceiveAV
        P.module_list = [LogicReceiveAV(P)]
        if app.config['config']['is_server'] == False and app.config['config']['is_debug'] == False:
            del P.menu['sub'][1]
        #else:
        #    from .logic_vod import LogicVod
        #    P.module_list.append(LogicVod(P)) 
        ###############################################
        P.logic = Logic(P)
        default_route(P)
    except Exception as e: 
        P.logger.error('Exception:%s', e)
        P.logger.error(traceback.format_exc())

initialize()

