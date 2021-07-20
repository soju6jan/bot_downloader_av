# -*- coding: utf-8 -*-
#########################################################
# python
import os, sys, traceback, re, json, threading, datetime, time
# third-party
import requests
# third-party
from flask import request, render_template, jsonify, Response
from sqlalchemy import or_, and_, func, not_, desc
# sjva 공용
from framework import app, db, scheduler, path_data, socketio, SystemModelSetting, py_urllib, Util
from framework.common.util import headers
from framework.common.plugin import LogicModuleBase, default_route_socketio
from tool_base import ToolBaseNotify

# 패키지
from .plugin import P
from .model import ModelItem
package_name = P.package_name
logger = P.logger
ModelSetting = P.ModelSetting
sub_name = 'receive'

#########################################################
class LogicReceiveAV(LogicModuleBase):
    db_default = {
        'db_version' : '4',         
        'interval' : '30',
        'auto_start' : 'False',
        'web_page_size': '20',
        'telegram_invoke_action' : '1', 
        'receive_send_notify' : 'False', 
        'result_send_notify' : 'False',
        'show_poster' : 'False',
        'show_log' : 'True',
        'last_id' : '-1', 
        'show_poster_notify' : 'False',

        'censored_receive' : 'True',
        'censored_allow_duplicate' : 'True',
        'censored_auto_download' : '0',
        'censored_torrent_program' : '',
        'censored_path' : '',
        'censored_option_mode' : '1',
        'censored_option_filter' : '',
        'censored_option_label' : '',
        'censored_option_genre' : '',
        'censored_option_performer' : '',
        'censored_allow_duplicate2' : '0',
        'censored_option_meta' : '0',
        'censored_option_min_size' : '0',
        'censored_option_max_size' : '0',
        'censored_option_file_count_min' : '0',
        'censored_option_file_count_max' : '0',
        'censored_option_server_id_mod' : '',

        'uncensored_receive' : 'True',
        'uncensored_allow_duplicate' : 'True',
        'uncensored_auto_download' : '0',
        'uncensored_torrent_program' : '',
        'uncensored_path' : '',
        'uncensored_option_mode' : '1',
        'uncensored_option_filter' : '',
        'uncensored_option_label' : '',
        'uncensored_option_genre' : '',
        'uncensored_option_performer' : '',
        'uncensored_allow_duplicate2' : '0',
        'uncensored_option_min_size' : '0',
        'uncensored_option_max_size' : '0',
        'uncensored_option_server_id_mod' : '',

        'western_receive' : 'True',
        'western_allow_duplicate' : 'True',
        'western_auto_download' : '0',
        'western_torrent_program' : '',
        'western_path' : '',
        'western_option_mode' : '1',
        'western_option_filter' : '',
        'western_option_label' : '',
        'western_option_genre' : '',
        'western_option_performer' : '',
        'western_allow_duplicate2' : '0',
        'western_option_min_size' : '0',
        'western_option_max_size' : '0',
        'western_option_foldername_filter' : '',
        'western_option_server_id_mod' : '',

        # 구드공 연동
        #'remote_path' : '',
        'censored_remote_path' : '',
        'uncensored_remote_path' : '',
        'western_remote_path' : '',
        'share_receive_option' : '0',

        # db_version 4체크에서 초기값 
        'receive_db_version' : '5',
        'receive_auto_start' : 'False',
        'receive_interval': '30',
    }
    
    def __init__(self, P):
        super(LogicReceiveAV, self).__init__(P, 'list', scheduler_desc='봇 다운로드 AV - 수신')
        self.name = sub_name


    def process_menu(self, sub, req):
        arg = P.ModelSetting.to_dict()
        arg['sub'] = self.name
        if sub == 'setting':
            arg['scheduler'] = str(scheduler.is_include(self.get_scheduler_name()))
            arg['is_running'] = str(scheduler.is_running(self.get_scheduler_name()))
            arg['rss_api'] = '%s/%s/api/%s/rss' % (SystemModelSetting.get('ddns'), package_name, self.name)
            arg['rss_api'] = Util.make_apikey(arg['rss_api'])
            return render_template('{package_name}_{module_name}_{sub}.html'.format(package_name=package_name, module_name=self.name, sub=sub), arg=arg)
        elif sub == 'list':
            arg['is_torrent_info_installed'] = False
            try:
                import torrent_info
                arg['is_torrent_info_installed'] = True
            except: pass
            arg['ddns'] = SystemModelSetting.get('ddns')
            arg['show_log'] = ModelSetting.get_bool('show_log')
            arg['show_poster'] = ModelSetting.get('show_poster')
            return render_template('{package_name}_{module_name}_{sub}.html'.format(package_name=package_name, module_name=self.name, sub=sub), arg=arg)
        return render_template('sample.html', title='%s - %s' % (package_name, sub))


    def process_ajax(self, sub, req):
        if sub == 'reset_last_index':
            ModelSetting.set('last_id', '-1')
            return jsonify(True)
        elif sub == 'web_list':
            ret = ModelItem.web_list(request)
            #logger.debug(ret)
            #logger.debug(json.dumps(ret, indent=4))
            return jsonify(ret)
        elif sub == 'add_download':
            db_id = request.form['id']
            ret = self.add_download(db_id)
            return jsonify(ret)
        elif sub == 'remove':
            ret = ModelItem.remove(request.form['id'])
            return jsonify(ret)
        elif sub == 'share_copy':
            ret = self.share_copy(request)
            return jsonify(ret)
        #elif sub == 'get_extra_content_url':
        #    ctype = request.form['ctype']
        #    code = request.form['code']
        #    ret = self.get_extra_content_url(ctype, code)
        #    return jsonify(ret)


    def process_api(self, sub, req):
        if sub == 'add_download':
            db_id = request.args.get('id')
            ret = self.add_download(db_id)
            return jsonify(ret)
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

    
    def scheduler_function(self):
        self.scheduler_function_torrent_check()
        #self.scheduler_function_share_retry()

    
    def process_telegram_data(self, data, target=None):
        try:
            ret = ModelItem.process_telegram_data(data)
            logger.debug(data)
            #ret = None
            if ret is not None:
                if ModelSetting.get_bool('receive_send_notify'):
                    msg = '😉 AV 정보 수신\n'
                    msg += '제목 : [%s] %s (%s)\n' % (ret.code, ret.title, ret.date)
                    msg += '파일 : %s\n' % ret.filename
                    msg += '폴더 : %s\n' % ret.dirname
                    msg += '크기 : %s\n' % Util.sizeof_fmt(ret.total_size)
                    
                    url = '%s/%s/api/%s/add_download?id=%s' % (SystemModelSetting.get('ddns'), package_name, self.name, ret.id)
                    if SystemModelSetting.get_bool('auth_use_apikey'):
                        url += '&apikey=%s' % SystemModelSetting.get('auth_apikey')
                    if app.config['config']['is_server']:
                        msg += '\n' + ret.magnet + '\n'
                    else:
                        msg += '\n➕ 다운로드 추가\n<%s>\n' % url
                    #msg += '\n➕ 다운로드 추가\n<%s>\n' % url
                    
                    poster = ret.poster if ModelSetting.get_bool('show_poster_notify') else None
                    ToolBaseNotify.send_message(msg, image_url=poster, message_id='bot_downloader_av_receive')
                self.invoke()
                try:
                    if app.config['config']['is_server']:
                        from tool_expand import TorrentProcess
                        TorrentProcess.receive_new_data(ret, package_name)
                except: pass
        except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
         
    

    def reset_db(self):
        db.session.query(ModelItem).delete()
        db.session.commit()
        ModelSetting.set('last_id', '-1')
        return True

    def migration(self):
        try:
            if ModelSetting.get('db_version') == '1':
                import sqlite3
                db_file = os.path.join(path_app_root, 'data', 'db', '%s.db' % package_name)
                connection = sqlite3.connect(db_file)
                cursor = connection.cursor()
                query = 'ALTER TABLE %s_item ADD server_id INT' % (package_name)
                cursor.execute(query)
                connection.close()
                ModelSetting.set('db_version', '2')
                db.session.flush()
            if ModelSetting.get('db_version') == '2':
                import sqlite3
                db_file = os.path.join(path_app_root, 'data', 'db', '%s.db' % package_name)
                connection = sqlite3.connect(db_file)
                cursor = connection.cursor()
                query = 'ALTER TABLE %s_item ADD folderid VARCHAR' % (package_name)
                cursor.execute(query)
                query = 'ALTER TABLE %s_item ADD folderid_time DATETIME' % (package_name)
                cursor.execute(query)
                query = 'ALTER TABLE %s_item ADD share_copy_time DATETIME' % (package_name)
                cursor.execute(query)
                query = 'ALTER TABLE %s_item ADD share_copy_complete_time DATETIME' % (package_name)
                cursor.execute(query)
                connection.close()
                ModelSetting.set('db_version', '3')
                db.session.flush()
            if ModelSetting.get('db_version') == '3':
                ModelSetting.set('receive_auto_start', ModelSetting.get('auto_start'))
                ModelSetting.set('receive_interval', ModelSetting.get('interval'))
                ModelSetting.set('db_version', '4')
                db.session.flush()
            if ModelSetting.get('receive_db_version') == '4':
                ModelSetting.set('receive_auto_start', ModelSetting.get('auto_start'))
                ModelSetting.set('receive_interval', ModelSetting.get('interval'))
                ModelSetting.set('receive_db_version', '5')
                db.session.flush()
               
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    #########################################################
    

    #########################################################
    # 다운로드 조건 판단
    #########################################################
    def scheduler_function_torrent_check(self):
        try:
            last_id = ModelSetting.get_int('last_id')
            flag_first = False
            if last_id == -1:
                flag_first = True
                # 최초 실행은 -1로 판단하고, 봇을 설정안했다면 0으로
                query = db.session.query(ModelItem) \
                    .filter(ModelItem.created_time > datetime.datetime.now() + datetime.timedelta(days=-7))
                items = query.all()
            else:
                query = db.session.query(ModelItem) \
                    .filter(ModelItem.id > last_id )
                items = query.all()

            # 하나씩 판단....
            logger.debug('New Feed.. last_id:%s count :%s', last_id, len(items))
            for item in items:
                
                try:
                    flag_download = False
                    item.download_status = ''
                    item.downloader_item_id = None
                    item.log = ''

                    option_auto_download = ModelSetting.get('%s_auto_download' % item.av_type)
                    if option_auto_download == '0':
                        item.download_status = 'no'
                    else:
                        # censored - 메타 조건만..
                        flag_download = True

                        if flag_download and item.av_type == 'censored':
                            if ModelSetting.get('censored_option_meta') == '1' and item.meta_type == 'ama':
                                flag_download = False
                                item.log += u'0. censored mode : False\n'
                            if ModelSetting.get('censored_option_meta') == '2' and item.meta_type == 'dvd':
                                flag_download = False
                                item.log += u'0. censored mode : False\n'
                        
                        if flag_download:
                            
                            mode = 'blacklist' if ModelSetting.get('%s_option_mode' % item.av_type) == '0' else 'whitelist'
                            item.log += u'1. 모드 - %s. 다운여부 : ' % (mode)
                            if mode == 'blacklist':
                                flag_download = True
                                item.log += u'%s\n' % flag_download
                                # 2020-07-20 웨스턴 폴더명 조건
                                if flag_download and item.av_type == 'western': 
                                    ret = self.check_option('%s_option_foldername_filter' % item.av_type, item.dirname)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'0. 폴더명 - %s : %s\n' % (item.dirname, flag_download)
                                if flag_download:
                                    ret = self.check_option('%s_option_filter' % item.av_type, item.filename)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'1. 파일명 - %s : %s\n' % (item.filename, flag_download)
                                if flag_download:
                                    ret = self.check_option('%s_option_label' % item.av_type, item.code)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'2. 레이블 - %s : %s\n' % (item.code, flag_download)
                                if flag_download:
                                    ret = self.check_option('%s_option_genre' % item.av_type, item.genre)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'3. 장르 - %s : %s\n' % (item.genre, flag_download)
                                if flag_download:
                                    ret = self.check_option('%s_option_performer' % item.av_type, item.performer)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'4. 배우 - %s : %s\n' % (item.performer, flag_download)
                                
                            else:
                                flag_download = False
                                item.log += u'%s\n' % flag_download
                                if not flag_download and item.av_type == 'western': 
                                    ret = self.check_option('%s_option_foldername_filter' % item.av_type, item.dirname)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'0. 폴더명 - %s : %s\n' % (item.dirname, flag_download)
                                if not flag_download:
                                    ret = self.check_option('%s_option_filter' % item.av_type, item.filename)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'1. 파일명 - %s : %s\n' % (item.filename, flag_download)
                                if not flag_download:
                                    ret = self.check_option('%s_option_label' % item.av_type, item.code)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'2. 레이블 - %s : %s\n' % (item.code, flag_download)
                                if not flag_download:
                                    ret = self.check_option('%s_option_genre' % item.av_type, item.genre)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'3. 장르 - %s : %s\n' % (item.genre, flag_download)
                                if not flag_download:
                                    ret = self.check_option('%s_option_performer' % item.av_type, item.performer)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'4. 배우 - %s : %s\n' % (item.performer, flag_download)

                        if flag_download:# and item.av_type == 'censored':
                            try:
                                option_min_size = float(str(ModelSetting.get('%s_option_min_size' % item.av_type))) * (2 ** 30)
                                option_max_size = float(str(ModelSetting.get('%s_option_max_size' % item.av_type))) * (2 ** 30)
                                if option_min_size != 0 and item.total_size < option_min_size:
                                    flag_download = False
                                    item.log += u'5. 최소크기 - %s : %s\n' % (Util.sizeof_fmt(item.total_size, suffix='B'), flag_download)
                                if option_max_size != 0 and item.total_size > option_max_size:
                                    flag_download = False
                                    item.log += u'5. 최대크기 - %s : %s\n' % (Util.sizeof_fmt(item.total_size, suffix='B'), flag_download)
                                if flag_download:
                                    item.log += u'5. 크기 - %s : %s\n' % (Util.sizeof_fmt(item.total_size, suffix='B'), flag_download)
                            except Exception as e: 
                                logger.error('Exception:%s', e)
                                logger.error(traceback.format_exc())

                        if flag_download and item.av_type == 'censored':
                            file_count = ModelSetting.get_int('censored_option_file_count_min')
                            if file_count != 0 and item.file_count < file_count:
                                flag_download = False
                                item.log += u'6. 파일 수 min - %s : %s\n' % (item.file_count, flag_download)
                        if flag_download and item.av_type == 'censored':
                            file_count = ModelSetting.get_int('censored_option_file_count_max')
                            if file_count != 0 and item.file_count > file_count:
                                flag_download = False
                                item.log += u'6. 파일 수 max - %s : %s\n' % (item.file_count, flag_download)

                        if flag_download:
                            flag_download = self.check_option_server_id_mod(item)
                            
                        item.log += u'8. 다운여부 : %s' % (flag_download)    

                        #다운로드
                        if flag_download:
                            if option_auto_download == '1':
                                import downloader
                                downloader_item_id = downloader.Logic.add_download2(item.magnet, ModelSetting.get('%s_torrent_program' % item.av_type), ModelSetting.get('%s_path' % item.av_type), request_type=package_name, request_sub_type='', server_id='av_%s_%s_%s' % (item.server_id, item.file_count, item.total_size) )['downloader_item_id']
                                item.downloader_item_id = downloader_item_id
                                item.download_status = 'true'
                            else:
                                item.download_status = 'true_only_status'
                        else:
                            if option_auto_download == '1':
                                item.download_status = 'false'
                            else:
                                item.download_status = 'false_only_status'
                        
                    if ModelSetting.get_bool('result_send_notify'):
                        self.send_telegram_message(item)
                    item.download_check_time =  datetime.datetime.now()
                    db.session.add(item)
                    logger.debug('%s - %s %s', item.code, flag_download, item.log)
                except Exception as e: 
                    logger.error('Exception:%s', e)
                    logger.error(traceback.format_exc())

            new_last_id = last_id
            if flag_first and len(items) == 0:
                new_last_id = '0'
            else:
                if len(items) > 0:
                    new_last_id = '%s' % items[len(items)-1].id
            if new_last_id != last_id:
                ModelSetting.set('last_id', str(new_last_id))
            db.session.commit()

        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    def check_option(self, option, value):
        if value is None:
            return None
        condition_list = ModelSetting.get_list(option, '|')
        if condition_list:
            for condition in condition_list:
                if value.replace(' ', '').lower().find(condition.lower()) != -1:
                    return True
                match = re.search(condition, value)
                if match:
                    return True
            return False
        return None   
    
    def check_option_server_id_mod(self, item):
        try:
            #server_id_mod = ModelSetting.get('%s_server_id_mod' % item.av_type)
            server_id_mod_list = ModelSetting.get_list('%s_option_server_id_mod' % item.av_type, '|')
            if len(server_id_mod_list) == 0:
                return True
            else:
                for server_id_mod in server_id_mod_list:
                    tmp = server_id_mod.split('_')
                    if item.server_id % int(tmp[0]) == int(tmp[1]):
                        item.log += u'7. server_id_mod 조건 일치. 다운:On. server_id:%s 조건:%s\n' % (item.server_id, server_id_mod)
                        return True
                    
                item.log += u'7. server_id_mod 조건 불일치. 다운:Off. server_id:%s 조건:%s\n' % (item.server_id, server_id_mod)
                return False
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return True


    def send_telegram_message(self, item):
        try:
            msg = '😉 봇 다운로드 - AV 처리결과\n'
            msg += '제목 : [%s] %s (%s)\n' % (item.code, item.title, item.date)
            msg += '파일 : %s\n' % item.filename

            if item.download_status == 'true':
                status_str = '✔조건일치 - 요청'
            elif item.download_status == 'false':
                status_str = '⛔패스 '
            elif item.download_status == 'no':
                status_str = '자동 다운로드 사용안함'
            elif item.download_status == 'true_only_status':
                status_str = '✔조건일치 - 상태만'
            elif item.download_status == 'false_only_status':
                status_str = '⛔조건불일치 - 상태만'

            msg += '결과 : %s\n' % status_str
            msg += '%s/%s/list\n' % (SystemModelSetting.get('ddns'), package_name)
            msg += '로그\n' + item.log
            ToolBaseNotify.send_message(msg, message_id='bot_downloader_av_result')
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    #########################################################



    #########################################################
    # ajax 처리
    #########################################################
    def add_download(self, db_id):
        try:
            import downloader
            item = ModelItem.get_by_id(db_id)
            downloader_item_id = downloader.Logic.add_download2(item.magnet, ModelSetting.get('%s_torrent_program' % item.av_type), ModelSetting.get('%s_path' % item.av_type), request_type=package_name, request_sub_type='', server_id='av_%s_%s_%s' % (item.server_id, item.file_count, item.total_size) )['downloader_item_id']
            item.downloader_item_id = downloader_item_id
            item.download_status = item.download_status.replace('|manual', '')
            item.download_status = '%s|manual' % item.download_status
            db.session.commit()
            return True
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    
   

    #########################################################
    # api 처리
    #########################################################
    def add_download_api(self, req):
        ret = {}
        try:
            import downloader
            url = req.args.get('url')
            result = downloader.Logic.add_download2(url, ModelSetting.get('torrent_program'), ModelSetting.get('path'), request_type=package_name, request_sub_type='api')
            return result
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['log'] = str(e)
        return ret
    

    


    #########################################################
    # 구드공 관련
    #########################################################

    def add_copy(self, item, my_remote_path):
        try:
            from gd_share_client.logic_user import LogicUser
        except:
            return {'ret':'no_plugin'}
        ret = LogicUser.instance.add_copy(item.folderid, item.filename, package_name, item.server_id, item.total_size, item.file_count, remote_path=my_remote_path)
        return ret


    def share_copy(self, req):
        try:
            db_id = req.form['id']
            item = db.session.query(ModelItem).filter_by(id=db_id).with_for_update().first()

            try:
                from gd_share_client.logic_user import LogicUser
            except:
                return {'ret':'fail', 'log':u'구글 드라이브 공유 플러그인이 설치되어 있지 않습니다.'}
            my_remote_path = ModelSetting.get('%s_remote_path' % item.av_type)
            if my_remote_path == '':
                return {'ret':'fail', 'log':u'리모트 경로가 설정되어 있지 않습니다.'} 

            ret = self.add_copy(item, my_remote_path)
            if ret['ret'] == 'success':
                item.download_status = 'true_manual_gdrive_share'
                item.share_copy_time = datetime.datetime.now()
                db.session.commit()
            return ret
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    

    def process_gd(self, item):
        try:
            share_receive_option = ModelSetting.get('share_receive_option')
            if share_receive_option == '0':
                pass
            try:
                from gd_share_client.logic_user import LogicUser
            except:
                logger.debug('not installed.. rclone expand')
                return
            my_remote_path = ModelSetting.get('%s_remote_path' % item.av_type)
            if my_remote_path == '':
                return
            if share_receive_option == '1' or (share_receive_option == '2' and item.download_status == 'true_only_status'):
                ret = self.add_copy(item, my_remote_path)
                if ret['ret'] == 'success':
                    item.download_status = 'true_gdrive_share'
                    item.share_copy_time = datetime.datetime.now()
                    item.save()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    
    #########################################################
    # 기타
    #########################################################
    def invoke(self):
        try:
            logger.debug('invoke')
            telegram_invoke_action = ModelSetting.get('telegram_invoke_action')
            if telegram_invoke_action == '0':
                return False
            elif telegram_invoke_action == '1':
                if scheduler.is_include(self.get_scheduler_name()):
                    if scheduler.is_running(self.get_scheduler_name()):
                        return False
                    else:
                        scheduler.execute_job(self.get_scheduler_name())
                        return True
            elif telegram_invoke_action == '2':
                P.logic.one_execute(self.name)
                return True
            else:
                return False
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    