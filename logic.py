# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import time
import threading

# third-party

# sjva 공용
from framework import db, scheduler, path_app_root
from framework.job import Job
from framework.util import Util

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelItem
from .logic_normal import LogicNormal
#########################################################

class Logic(object):
    db_default = {
        'db_version' : '3',         
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

        # 구드공 연동
        #'remote_path' : '',
        'censored_remote_path' : '',
        'uncensored_remote_path' : '',
        'western_remote_path' : '',
        'share_receive_option' : '0',
    }

    @staticmethod
    def db_init():
        try:
            for key, value in Logic.db_default.items():
                if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
                    db.session.add(ModelSetting(key, value))
            db.session.commit()
            
            Logic.migration()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        
    @staticmethod
    def plugin_load():
        try:
            logger.debug('%s plugin_load', package_name)
            Logic.db_init()
            if ModelSetting.query.filter_by(key='auto_start').first().value == 'True':
                Logic.scheduler_start()
            # 편의를 위해 json 파일 생성
            from .plugin import plugin_info
            Util.save_from_dict_to_json(plugin_info, os.path.join(os.path.dirname(__file__), 'info.json'))
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def plugin_unload():
        try:
            logger.debug('%s plugin_unload', package_name)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def scheduler_start():
        try:
            logger.debug('%s scheduler_start' % package_name)
            job = Job(package_name, package_name, ModelSetting.get('interval'), Logic.scheduler_function, u"Bot 다운로드 - AV", False)
            scheduler.add_job_instance(job)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def scheduler_stop():
        try:
            logger.debug('%s scheduler_stop' % package_name)
            scheduler.remove_job(package_name)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
           

    @staticmethod
    def scheduler_function():
        try:
            LogicNormal.scheduler_function()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def reset_db():
        try:
            db.session.query(ModelItem).delete()
            db.session.commit()
            return True
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False


    @staticmethod
    def one_execute():
        try:
            if scheduler.is_include(package_name):
                if scheduler.is_running(package_name):
                    ret = 'is_running'
                else:
                    scheduler.execute_job(package_name)
                    ret = 'scheduler'
            else:
                def func():
                    time.sleep(2)
                    Logic.scheduler_function()
                threading.Thread(target=func, args=()).start()
                ret = 'thread'
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret = 'fail'
        return ret

    """
    @staticmethod
    def process_telegram_data(data):
        try:
            logger.debug(data)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    """

    @staticmethod
    def migration():
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
               
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())