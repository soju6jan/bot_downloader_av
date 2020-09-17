# -*- coding: utf-8 -*-
#########################################################
# python
import os
import datetime
import traceback
import urllib
import re, time
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
                    msg += '폴더 : %s\n' % ret.dirname
                    msg += '크기 : %s\n' % Util.sizeof_fmt(ret.total_size)
                    
                    url = '%s/%s/api/add_download?id=%s' % (SystemModelSetting.get('ddns'), package_name, ret.id)
                    if SystemModelSetting.get_bool('auth_use_apikey'):
                        url += '&apikey=%s' % SystemModelSetting.get('auth_apikey')
                    if app.config['config']['is_sjva_server']:
                        msg += '\n' + ret.magnet + '\n'
                    else:
                        msg += '\n➕ 다운로드 추가\n<%s>\n' % url
                    #msg += '\n➕ 다운로드 추가\n<%s>\n' % url
                    
                    poster = ret.poster if ModelSetting.get_bool('show_poster_notify') else None
                    import framework.common.notify as Notify
                    Notify.send_message(msg, image_url=poster, message_id='bot_downloader_av_receive')
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
            msg += '%s/%s/list\n' % (SystemModelSetting.get('ddns'), package_name)
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
    


         
    @staticmethod
    def scheduler_function():
        LogicNormal.scheduler_function_torrent_check()
        #LogicNormal.scheduler_function_share_retry()

    @staticmethod
    def scheduler_function_torrent_check():
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
                                # 2020-07-20 웨스턴 폴더명 조건
                                if flag_download and item.av_type == 'western': 
                                    ret = LogicNormal.check_option('%s_option_foldername_filter' % item.av_type, item.dirname)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'0. 폴더명 - %s : %s\n' % (item.dirname, flag_download)
                                if flag_download:
                                    ret = LogicNormal.check_option('%s_option_filter' % item.av_type, item.filename)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'1. 파일명 - %s : %s\n' % (item.filename, flag_download)
                                if flag_download:
                                    ret = LogicNormal.check_option('%s_option_label' % item.av_type, item.code)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'2. 레이블 - %s : %s\n' % (item.code, flag_download)
                                if flag_download:
                                    ret = LogicNormal.check_option('%s_option_genre' % item.av_type, item.genre)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'3. 장르 - %s : %s\n' % (item.genre, flag_download)
                                if flag_download:
                                    ret = LogicNormal.check_option('%s_option_performer' % item.av_type, item.performer)
                                    if ret is not None:
                                        flag_download = not ret
                                        item.log += u'4. 배우 - %s : %s\n' % (item.performer, flag_download)
                            else:
                                flag_download = False
                                item.log += u'%s\n' % flag_download
                                if not flag_download and item.av_type == 'western': 
                                    ret = LogicNormal.check_option('%s_option_foldername_filter' % item.av_type, item.dirname)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'0. 폴더명 - %s : %s\n' % (item.dirname, flag_download)
                                if not flag_download:
                                    ret = LogicNormal.check_option('%s_option_filter' % item.av_type, item.filename)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'1. 파일명 - %s : %s\n' % (item.filename, flag_download)
                                if not flag_download:
                                    ret = LogicNormal.check_option('%s_option_label' % item.av_type, item.code)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'2. 레이블 - %s : %s\n' % (item.code, flag_download)
                                if not flag_download:
                                    ret = LogicNormal.check_option('%s_option_genre' % item.av_type, item.genre)
                                    if ret is not None:
                                        flag_download = ret
                                        item.log += u'3. 장르 - %s : %s\n' % (item.genre, flag_download)
                                if not flag_download:
                                    ret = LogicNormal.check_option('%s_option_performer' % item.av_type, item.performer)
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


                        item.log += u'7. 다운여부 : %s' % (flag_download)    

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
                match = re.search(condition, value)
                if match:
                    return True
            return False
        return None   

    #########################################################
    # 구드공 관련
    #########################################################
    @staticmethod
    def add_copy(item, my_remote_path):
        try:
            from gd_share_client.logic_user import LogicUser
        except:
            return {'ret':'no_plugin'}
        ret = LogicUser.instance.add_copy(item.folderid, item.filename, package_name, '', item.total_size, item.file_count, remote_path=my_remote_path)
        return ret

    @staticmethod
    def share_copy(req):
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

            ret = LogicNormal.add_copy(item, my_remote_path)
            if ret['ret'] == 'success':
                item.download_status = 'true_manual_gdrive_share'
                item.share_copy_time = datetime.datetime.now()
                db.session.commit()
            return ret
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def process_gd(item):
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
                ret = LogicNormal.add_copy(item, my_remote_path)
                if ret['ret'] == 'success':
                    item.download_status = 'true_gdrive_share'
                    item.share_copy_time = datetime.datetime.now()
                    item.save()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    
    """
    @staticmethod
    def scheduler_function_share_retry():
        try:
            item_list = ModelItem.get_share_incompleted_list()
            logger.debug('scheduler_function_share_retry : %s', len(item_list))
            for item in item_list:
                LogicNormal.process_gd(item)
                time.sleep(10)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    """
