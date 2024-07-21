from fastapi import FastAPI
from spider.nvd_spider import *
from es.es_util import search_by_cve_id

app = FastAPI()


@app.post('/nvd/crawl/all')
def nvd_crawl_all():
    crawl_all()
    # todo 添加阿里云爬虫的入口


@app.post('/nvd/crawl/by_time/start_time=<string:start_time>/end_time=<string:end_time>')
def nvd_crawl_by_time(start_time, end_time):
    crawl_by_time(start_time=start_time, end_time=end_time)


@app.get('/get/cve_id=<string:cve_id>')
def query_by_cve_id(cve_id):
    if len(cve_id.split('-')) != 3 and not cve_id.startswith('cve') and not cve_id.startswith('CVE'):
        print("输入的不是CVE字符串！")
        return
    result = search_by_cve_id(cve_id)
    # 代表cve的格式不正确
    if result.code == '500':
        print(result.message)
    else:
        print(result.data)


