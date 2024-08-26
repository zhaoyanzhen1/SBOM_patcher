import time

from pymongo import MongoClient
from elasticsearch import Elasticsearch
import queue
from threading import Thread
from es.es_util import establish_es_index
from Constants.dbConstants import mongo_url, es_url
from mongoDB.mongoUtils import query_by_updated_time

collection_to_index = {'mergedCVE': 'merged_cve'}
collection = 'mergedCVE'
index = 'merged_cve'

# 连接到MongoDB
client = MongoClient(mongo_url)
db = client['local']
# 连接到es
es = Elasticsearch(es_url)

# 定义线程数和队列
NUM_THREADS = 5

data_queue = queue.Queue()


def get_from_mongo(time=None):
    db_data = query_by_updated_time(time, collection)
    print(f'共有{len(db_data)}条数据')
    print(f'所有的数据为:{db_data}')

    for doc in db_data:
        data_queue.put(doc)


def write_to_es():
    _index = index
    while True:
        doc_with_id = data_queue.get()  # 从队列获取数据
        if doc_with_id is None:
            break  # 遇到特殊标记，停止循环

        cve_id = doc_with_id['No']
        doc = {
            'No': cve_id,
            'title': doc_with_id['title'],
            'description': doc_with_id['description'],
            'score': doc_with_id['score'],
            'cve_published_time': doc_with_id['cve_published_time'],
            'cve_modified_time': doc_with_id['cve_modified_time'],
            'crawl_time': doc_with_id['merge_time'],
            'source_urls': doc_with_id['source_urls'],
            'affected_software': doc_with_id['affected_software'],
            'third_party_list': doc_with_id['third_party_list'] if 'third_party_list' in doc_with_id else None,
            'vendor_list': doc_with_id['vendor_list'] if 'vendor_list' in doc_with_id else None,
            'exploit_list': doc_with_id['exploit'] if 'exploit' in doc_with_id else None,
            'patch_list': doc_with_id['patch_list'] if 'patch_list' in doc_with_id else None,
            'debian_list': doc_with_id['debian_list'] if 'debian_list' in doc_with_id else None,
            'advisories_list': doc_with_id['advisories_list'] if 'advisories_list' in doc_with_id else None,
            'github_advisories_patches': doc_with_id['github_advisories_patches'] if 'github_advisories_patches' in doc_with_id else None,
        }
        body = {
            "query": {
                "term": {"No": cve_id}
                # "match_all": {}
            }
        }
        # 查找是否存在该文档，如果存在则是更新，否则是插入
        result = es.search(index=_index, body=body)
        hits = result["hits"]["hits"]
        # 更新
        if hits:
            doc_id = result['hits']['hits'][0]['_id']
            response = es.update(index=_index, id=doc_id, body={"doc": doc})
        else:
            response = es.index(index=_index, document=doc)
        print(response['result'])
        data_queue.task_done()


def transfer_to_es(time=None):
    # 如果没有索引创建已有索引
    if not es.indices.exists(index=index):
        print("没有对应的索引，正在创建")
        establish_es_index()
        print("创建索引完成")

    # 创建并启动获取数据线程
    producer_thread = Thread(target=get_from_mongo, args=(time,))
    producer_thread.start()

    # 创建并启动消费数据线程
    consumer_threads = []
    for _ in range(NUM_THREADS):
        thread = Thread(target=write_to_es)
        consumer_threads.append(thread)
        thread.start()

    # 等待生产者线程生产完毕
    producer_thread.join()

    # 向队列中放入None，通知消费者线程退出
    for _ in range(NUM_THREADS):
        data_queue.put(None)

    # 等待消费者线程完成
    for thread in consumer_threads:
        thread.join()

# if __name__ == "__main__":
#     for collection, index in collection_to_index.items():
#         mongo_data = get_from_mongo(collection)
#         write_to_es(index, mongo_data)
