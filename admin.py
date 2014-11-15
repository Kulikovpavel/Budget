import json
from google.appengine.api import taskqueue
from google.appengine.ext import db
import logging
from models import *


# !!! Important !!!
# to add regions in test base run this in admin console
#   import admin
#   admin.add_tasks_regions()

def add_tasks_regions():
    json_file = 'json/peoples.json'
    with open(json_file) as json_data:
        data = json.load(json_data)
    for key in data:
        taskqueue.add(url='/add_regions', params={'key': key}, queue_name='load-regions-queue')


def load_regions(year=2012, json_file='json/peoples.json', region_work=''):
    logging.warning("LOAD REGIONS START as %s" % region_work)

    with open(json_file) as json_data:
        data = json.load(json_data)

    mun_array = []
    reg_count_array = []
    mun_count_array = []
    count = 0

    for key in data:
        if region_work != '' and key != region_work:
            continue
        region_data = data[key]
        region = Region(title=key,
                        region_type='region',
                        parent=db.Key.from_path('regions', 'default'))
        region.put()

        reg_count = RegionCount(count=region_data['count'],
                                year=year,
                                region=region)
        reg_count_array.append(reg_count)

        for key_region in region_data:
            if key_region == 'count':
                continue
            raion_data = region_data[key_region]

            raion = Region(title=key_region,
                           region_type='raion',
                           owner=region,
                           parent=db.Key.from_path('regions', 'default'))
            raion.put()

            reg_count = RegionCount(count=raion_data['count'],
                                    year=year,
                                    region=raion)
            reg_count_array.append(reg_count)

            for key_raion in raion_data:
                if key_raion == 'count':
                    continue
                mun_data = raion_data[key_raion]

                mun = Region(title=key_raion,
                             type='mun',
                             owner=raion,
                             parent=db.Key.from_path('regions', 'default'))
                count += 1
                mun_array.append(mun)
                mun_count_array.append(mun_data['count'])
        logging.warning(count)

    put_array(mun_array)
    put_array(reg_count_array)

    reg_count_array = []
    for i in range(len(mun_array)):
        reg_count = RegionCount(count=mun_count_array[i],
                                year=year,
                                region=mun_array[i])
        reg_count_array.append(reg_count)
    put_array(reg_count_array)


def reg_count_save(year, region, count, reg_count_array):  # puts count in count entities list
    reg_count = db.GqlQuery("SELECT * FROM RegionCount where year=%s and region=%s" % year, region)
    if not reg_count:
        reg_count = RegionCount(count=count,
                                year=year,
                                region=region)
    else:
        reg_count.count = count
    reg_count_array.append(reg_count)


def load_counts(year=2012, json_file='json/peoples.json'):
    with open(json_file) as json_data:
        data = json.load(json_data)
    if not data:
        return

    # q = db.GqlQuery("SELECT * FROM RegionCount where year=%s" % year)  # deletion all previous count
    # results = q.fetch(1000)
    # sum = 0
    # while results:
    #     sum += len(results)
    #     db.delete(results)
    #     results = q.fetch(1000, len(results))
    #     logging.warning(sum)

    reg_count_array = []
    count = 0
    for key in data:
        region_data = data[key]
        region = Region.all().filter('title =', key).ancestor(db.Key.from_path('regions', 'default')).get()
        if not region:
            logging.warning('region %s not found' % key)
        else:
            reg_count_save(year, region, region_data['count'], reg_count_array)

        for key_region in region_data:
            if key_region == 'count':
                continue
            raion_data = region_data[key_region]
            raion = Region.all().filter('title =', key_region).filter('owner =', region).get()
            if not raion:
                logging.warning('raion %s not found' % key_region)
            else:
                reg_count_save(year, raion, raion_data['count'], reg_count_array)

            for key_raion in raion_data:
                if key_raion == 'count':
                    continue
                mun_data = raion_data[key_raion]
                mun = Region.all().filter('title =', key_raion).filter('owner =', raion).get()
                if not mun:
                    logging.warning('mun %s not found' % key_raion)
                else:
                    reg_count_save(year, mun, mun_data['count'], reg_count_array)
                    count += 1
        logging.warning("count = %s" % count)
    put_array(reg_count_array)


def put_array(array):
    logging.warning("len of array is %s" % len(array))
    db.put(array)
    return
    # for i in range(len(array)/1000 + 1):
    #     if (i+1)*1000-1 > len(array):
    #         last = len(array)-1
    #     else:
    #         last = (i+1)*1000-1
    #     logging.warning(i)
    #     db.put(array[i*1000:last])