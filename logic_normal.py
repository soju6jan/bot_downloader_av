# -*- coding: utf-8 -*-
#########################################################
# python
import os
import datetime
import traceback
import urllib

# third-party
from sqlalchemy import desc
from sqlalchemy import or_, and_, func, not_
from guessit import guessit

# sjva 공용
from framework import app, db, scheduler, path_app_root
from framework.job import Job
from framework.util import Util
from system.logic import SystemLogic
from framework.common.torrent.process import TorrentProcess
from system.model import ModelSetting as SystemModelSetting

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelItem


#########################################################
class LogicNormal(object):
    @staticmethod
    def process_telegram_data(data):
        try:
            ret = ModelItem.process_telegram_data(data)
            logger.debug(data)
            #ret = None
            if ret is not None:
                if ModelSetting.get_bool('receive_send_notify'):
                    msg = '😉 AV 정보 수신\n'
                    msg += '제목 : [%s] %s (%s)\n' % (ret.code, ret.title, ret.date)
                    msg += '파일 : %s\n' % ret.filename
                    
                    url = '%s/%s/api/add_download?id=%s' % (SystemModelSetting.get('ddns'), package_name, ret.id)
                    if SystemModelSetting.get_bool('auth_use_apikey'):
                        url += '&apikey=%s' % SystemModelSetting.get('auth_apikey')
                    msg += '\n➕ 다운로드 추가\n%s\n' % url
                    
                    import framework.common.notify as Notify
                    Notify.send_message(msg, image_url=ret.poster, message_id='bot_downloader_av_receive')
                LogicNormal.invoke()
                TorrentProcess.receive_new_data(ret, package_name)
        except Exception, e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())

                
        
    @staticmethod
    def send_telegram_message(item):
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
            msg += '%s/%s/list\n' % (SystemLogic.get_setting_value('ddns'), package_name)
            msg += '로그\n' + item.log
            import framework.common.notify as Notify
            Notify.send_message(msg, message_id='bot_downloader_av_result')
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())



    @staticmethod
    def reset_last_index():
        try:
            ModelSetting.set('last_id', '-1')
            return True
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    
    @staticmethod
    def invoke():
        try:
            logger.debug('invoke')
            telegram_invoke_action = ModelSetting.get('telegram_invoke_action')
            if telegram_invoke_action == '0':
                return False
            elif telegram_invoke_action == '1':
                if scheduler.is_include(package_name):
                    if scheduler.is_running(package_name):
                        return False
                    else:
                        scheduler.execute_job(package_name)
                        return True
            elif telegram_invoke_action == '2':
                from .logic import Logic
                Logic.one_execute()
                return True
            else:
                return False
        except Exception, e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())




    # 토렌트
    @staticmethod
    def add_download(db_id):
        try:
            import downloader
            item = ModelItem.get_by_id(db_id)
            downloader_item_id = downloader.Logic.add_download2(item.magnet, ModelSetting.get('%s_torrent_program' % item.av_type), ModelSetting.get('%s_path' % item.av_type), request_type=package_name, request_sub_type='')['downloader_item_id']
            item.downloader_item_id = downloader_item_id
            item.download_status = item.download_status.replace('|manual', '')
            item.download_status = '%s|manual' % item.download_status
            db.session.commit()
            return True
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False
    


         

    @staticmethod
    def scheduler_function():
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
                            if ModelSetting.get('censored_option_meta') == '1' and item.meta_type == 'javdb':
                                flag_download = False
                                item.log += u'0. censored mode : False\n'
                            if ModelSetting.get('censored_option_meta') == '2' and item.meta_type == 'dmm':
                                flag_download = False
                                item.log += u'0. censored mode : False\n'
                        
                        if flag_download:
                            
                            mode = 'blacklist' if ModelSetting.get('%s_option_mode' % item.av_type) == '0' else 'whitelist'
                            item.log += u'1. 모드 - %s. 다운여부 : ' % (mode)
                            if mode == 'blacklist':
                                flag_download = True
                                item.log += u'%s\n' % flag_download
                                if flag_download:
                                    ret = LogicNormal.check_option('%s_option_label' % item.av_type, item.code)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'1. 레이블 - %s : %s\n' % (item.code, flag_download)
                                if flag_download:
                                    ret = LogicNormal.check_option('%s_option_genre' % item.av_type, item.genre)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'2. 장르 - %s : %s\n' % (item.genre, flag_download)
                                if flag_download:
                                    ret = LogicNormal.check_option('%s_option_performer' % item.av_type, item.performer)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'3. 배우 - %s : %s\n' % (item.performer, flag_download)
                            else:
                                flag_download = False
                                item.log += u'%s\n' % flag_download
                                if not flag_download:
                                    ret = LogicNormal.check_option('%s_option_label' % item.av_type, item.code)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'1. 레이블 - %s : %s\n' % (item.code, flag_download)
                                if not flag_download:
                                    ret = LogicNormal.check_option('%s_option_genre' % item.av_type, item.genre)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'2. 장르 - %s : %s\n' % (item.genre, flag_download)
                                if not flag_download:
                                    ret = LogicNormal.check_option('%s_option_performer' % item.av_type, item.performer)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'3. 배우 - %s : %s\n' % (item.performer, flag_download)
                        item.log += u'4. 다운여부 : %s' % (flag_download)    
                        #다운로드
                        if flag_download:
                            if option_auto_download == '1':
                                import downloader
                                downloader_item_id = downloader.Logic.add_download2(item.magnet, ModelSetting.get('%s_torrent_program' % item.av_type), ModelSetting.get('%s_path' % item.av_type), request_type=package_name, request_sub_type='')['downloader_item_id']
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
                        LogicNormal.send_telegram_message(item)
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

    
    @staticmethod
    def check_option(option, value):
        if value is None:
            return None
        condition_list = ModelSetting.get_list(option)
        if condition_list:
            for condition in condition_list:
                if value.replace(' ', '').lower().find(condition.lower()) != -1:
                    return True
            return False
        return None   

