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
from framework import app, db, scheduler, path_data, socketio, check_api
from framework.util import Util
from system.model import ModelSetting as SystemModelSetting

# 패키지
# 로그
package_name = __name__.split('.')[0]
logger = get_logger(package_name)

from .model import ModelSetting, ModelItem
from .logic import Logic
from .logic_normal import LogicNormal

#########################################################


#########################################################
# 플러그인 공용                                       
#########################################################
blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

menu = {
    'main' : [package_name, u'봇 다운로드 - AV'],
    'sub' : [
        ['setting', u'설정'], ['list', u'목록'], ['log', u'로그']
    ],
    'category' : 'torrent'
}

plugin_info = {
    'version' : '0.1.0.0',
    'name' : 'bot_downloader_av',
    'category_name' : 'torrent',
    'developer' : 'soju6jan',
    'description' : u'텔레그램 봇으로 수신한 정보로 AV 다운로드',
    'home' : 'https://github.com/soju6jan/bot_downloader_av',
    'more' : '',
}

def plugin_load():
    Logic.plugin_load()

def plugin_unload():
    Logic.plugin_unload()

def process_telegram_data(data):
    LogicNormal.process_telegram_data(data)



#########################################################
# WEB Menu 
#########################################################
@blueprint.route('/')
def home():
    return redirect('/%s/list' % package_name)

@blueprint.route('/<sub>')
@login_required
def first_menu(sub): 
    logger.debug('DETAIL %s %s', package_name, sub)
    if sub == 'setting':
        arg = ModelSetting.to_dict()
        arg['package_name']  = package_name
        arg['scheduler'] = str(scheduler.is_include(package_name))
        arg['is_running'] = str(scheduler.is_running(package_name))
        ddns = SystemModelSetting.get('ddns')
        arg['rss_api'] = '%s/%s/api/rss' % (ddns, package_name)
        if SystemModelSetting.get_bool('auth_use_apikey'):
            arg['rss_api'] += '?apikey=%s' % SystemModelSetting.get('auth_apikey')
        return render_template('%s_setting.html' % package_name, sub=sub, arg=arg)
    elif sub == 'list':
        arg = {'package_name' : package_name}
        arg['is_torrent_info_installed'] = False
        try:
            import torrent_info
            arg['is_torrent_info_installed'] = True
        except Exception as e: 
            pass
        arg['ddns'] = SystemModelSetting.get('ddns')
        arg['show_log'] = ModelSetting.get_bool('show_log')
        arg['show_poster'] = ModelSetting.get('show_poster')
        return render_template('%s_list.html' % package_name, arg=arg)
    elif sub == 'log':
        return render_template('log.html', package=package_name)
    return render_template('sample.html', title='%s - %s' % (package_name, sub))

#########################################################
# For UI 
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
@login_required
def ajax(sub):
    try:
        # 설정
        if sub == 'setting_save':
            ret = ModelSetting.setting_save(request)
            return jsonify(ret)
        elif sub == 'scheduler':
            go = request.form['scheduler']
            logger.debug('scheduler :%s', go)
            if go == 'true':
                Logic.scheduler_start()
            else:
                Logic.scheduler_stop()
            return jsonify(go)
        elif sub == 'reset_db':
            LogicNormal.reset_last_index()
            ret = Logic.reset_db()
            return jsonify(ret)
        elif sub == 'one_execute':
            ret = Logic.one_execute()
            return jsonify(ret)
        
        elif sub == 'reset_last_index':
            ret = LogicNormal.reset_last_index()
            return jsonify(ret)

        # 목록
        elif sub == 'web_list':
            ret = ModelItem.web_list(request)
            return jsonify(ret)
        elif sub == 'add_download':
            db_id = request.form['id']
            ret = LogicNormal.add_download(db_id)
            return jsonify(ret)
        elif sub == 'remove':
            ret = ModelItem.remove(request.form['id'])
            return jsonify(ret)
        elif sub == 'share_copy':
            ret = LogicNormal.share_copy(request)
            return jsonify(ret)

        # 예고편 URL 가져오기
        elif sub == 'get_extra_content_url':
            ctype = request.form['ctype']
            code = request.form['code']
            ret = LogicNormal.get_extra_content_url(ctype, code)
            return jsonify(ret)
    except Exception as e:
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())  
        return jsonify('fail')   


#########################################################
# API
#########################################################
@blueprint.route('/api/<sub>', methods=['GET', 'POST'])
@check_api
def api(sub):
    try:
        if sub == 'add_download':
            db_id = request.args.get('id')
            ret1 = LogicNormal.add_download(db_id)
            return jsonify(ret1)
        elif sub == 'rss':
            ret = ModelItem.api_list(request)
            data = []
            for item in ret:
                entity = {}
                entity['title'] = '[%s] %s' % (item.code, item.filename)
                entity['link'] = item.magnet
                entity['created_time'] = item.created_time
                data.append(entity)
            logger.debug(ret)
            logger.debug(data)
            from framework.common.rss import RssUtil
            xml = RssUtil.make_rss(package_name, data)
            return Response(xml, mimetype='application/xml')
    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())
