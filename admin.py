import json
from google.appengine.ext import db
from models import *


def load_regions(year=2012, json_file='json/peoples.json'):
    data = ''
    with open(json_file) as json_data:
        data = json.load(json_data)

    q = db.GqlQuery("SELECT * FROM Region where year=%s" % year)
    results = q.fetch(1000)
    sum = 0
    while results:
        sum += len(results)
        db.delete(results)
        results = q.fetch(1000, len(results))

    mun_array = []
    reg_count_array = []
    mun_count_array = []
    count = 0
    for key in data:
        region_data = data[key]
        # search = Region.all().filter('title =', key).ancestor(db.Key.from_path('regions', 'default')).fetch(1)
        # if len(search) == 1:
        #     region = search[0]
        # else:
        region = Region(title=key,
                        region_type='region',
                        # count=region_data['count'],
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
            # search = Region.all().filter('title =', key_region).ancestor(region).fetch(1)
            # if len(search) == 1:
            #     raion = search[0]
            # else:

            raion = Region(title=key_region,
                           region_type='raion',
                           # count=raion_data['count'],
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
                # search = Region.all().filter('title =', key_raion).ancestor(raion).fetch(1)
                # if len(search) == 1:
                #     mun = search[0]
                # else:

                mun = Region(title=key_raion,
                             type='mun',
                             # count=mun_data['count'],
                             owner=raion,
                             parent=db.Key.from_path('regions', 'default'))
                # mun.put()
                count += 1

                mun_array.append(mun)
                mun_count_array.append(mun_data['count'])

                # logging.warning(mun)

    # logging.warning(len(mun_array))
    db.put(mun_array)
    db.put(reg_count_array)

    reg_count_array = []
    for i in range(len(mun_array)):
        reg_count = RegionCount(count=mun_count_array[i],
                                year=year,
                                region=mun_array[i])

        reg_count_array.append(reg_count)
    db.put(reg_count_array)