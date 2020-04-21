# -*- coding: utf-8 -*-
# @Time    : 2020-04-18 00:04
# @Author  : li
# @File    : main.py

from sprite import Settings, CrawlerRunner

if __name__ == "__main__":
    settings = Settings(values={
        "MAX_DOWNLOAD_NUM": 1,
        "WORKER_NUM": 1,
        "DELAY": 20,
        "LOG_FILE_PATH": "test_spider_one.log",
        "JOB_DIR": "/Users/liyong/projects/open_source/sprite/examples/test_spider_one",
        "LONG_SAVE": True,
    })
    crawler_runner = CrawlerRunner(settings=settings,
                                   crawler_manage_path="examples/test_spider_one/test_crawler_config.py")
    crawler_runner.start()
