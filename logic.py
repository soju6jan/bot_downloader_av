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
        'db_version' : '1',         
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


        'fc2_receive' : 'True',
        'fc2_allow_duplicate' : 'True',
        'fc2_auto_download' : '0',
        'fc2_torrent_program' : '',
        'fc2_path' : '',
        'fc2_option_mode' : '1',
        'fc2_option_filter' : '',
        'fc2_option_label' : '',
        'fc2_option_genre' : '',
        'fc2_option_performer' : '',
        'fc2_allow_duplicate2' : '0',


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
            from plugin import plugin_info
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
            db_version = ModelSetting.get('db_version')
            
               
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())