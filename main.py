#!/usr/bin/env python
# -*- coding: utf-8 -*-


import webapp2
import jinja2
import urllib
import logging
import json
import random
import admin
from google.appengine.api.labs import taskqueue
from helpers import *


import sys  # models import
sys.path.append('/models')
from models import *

jinja_environment = jinja2.Environment(autoescape=True,
                                       loader=jinja2.FileSystemLoader("templates"))


# add filters for description tag
def nl2br(value):
    if hasattr(value, 'replace'):
        return value.replace('\n', '<br>\n')
    else:
        return ""

jinja_environment.filters['nl2br'] = nl2br


class BudgetHandler(webapp2.RequestHandler):
    def zero_level(self, budget_lines):
        # zero_level = [[line[0], get_float(line[5])] for line in table if (line[2] == "" or int(line[2]) == 0)]
        zero_level = [budget_line(line) for line in budget_lines if line.podrazdel == 0]
        return json.dumps(zero_level)

    def end_level(self, table):
        table_len = len(table)
        end_level = []
        for line_index in xrange(table_len):
            line = table[line_index]
            if line_index < table_len - 1 and\
                    (table[line_index+1][4] != "" or int(table[line_index+1][4]) != 0) and\
                    (table[line_index][4] == "" or int(table[line_index][4]) == 0):
                end_level.append([line[0], get_float(line[5]),0])
        return json.dumps(end_level)

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        self.template_values = {
        }


class MainHandler(BudgetHandler):
    def get(self):
        budgets = Budget.all().ancestor(main_key()).order('-created').fetch(300)
        self.template_values['budgets'] = budgets
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(self.template_values))


class BudgetPageHandler(BudgetHandler):
    def get(self, id):
        id = int(urllib.unquote(id))
        budget = Budget.by_id(id)

        self.template_values['budget'] = budget
        self.template_values['count'] = budget.region.count()
        self.template_values['zero_level'] = self.zero_level(budget.budget_lines)
        self.template_values['end_level'] = self.end_level(budget.table)
        template = jinja_environment.get_template('budget.html')
        self.response.out.write(template.render(self.template_values))

    def post(self, id=0):
        excel_table = self.request.get('excel_table')
        year = int(self.request.get('year'))
        description = self.request.get('description')

        region = self.request.get('region')
        raion = self.request.get('raion')
        mun = self.request.get('municipality')
        if region == '0':
            self.redirect('/upload?alert="Регион не выбран"')
        region_id = None
        if mun and mun != '0':
            region_id = mun
        elif raion and raion != '0':
            region_id = raion
        elif region and region != '0':
            region_id = region
        else:
            self.redirect('/upload?alert="Выберите регион!"')

        region = Region.by_id(region_id)
        if not region:
            self.redirect('/upload?alert="Регион не найден"')
        lines = excel_table.split('\n')
        table = [[word if word != "" else "0" for word in line.split('\t')] for line in lines if line != ""]
        if len(table) > 2 and len(table[0]) > 2:
            budget = Budget.all().filter('region =', region).filter('year =', year).get()
            logging.warning(budget)
            if not budget:
                budget = Budget(title=region.title,
                                region=region,
                                description=description,
                                table=table,
                                year=year,
                                type='rashod',
                                parent=main_key())
                budget.put()
            db.delete(budget.budget_lines)
            self.create_budget_lines(budget, table)
            self.redirect("/budget/"+str(budget.key().id()))
        else:
            self.redirect('/upload?alert=""')

    def create_budget_lines(self, budget, table):
        line_array = []
        for line in table:
            if len(line[0]) > 499:
                title = line[0][:500]
            else:
                title = line[0]
            budget_line = BudgetLine(budget=budget,
                                     title=title,
                                     line_type='',
                                     razdel=int(line[1]),
                                     podrazdel=int(line[2]),
                                     statya=int(line[3]),
                                     vid=int(line[4]),
                                     total=get_float(line[5]),
                                     total_sub=get_float(line[6]),
                                     # parent=budget
                                     )
            line_array.append(budget_line)
        db.put(line_array)


class UploadHandler(BudgetHandler):
    def get(self):
        alert = self.request.get('alert')
        if alert:
            self.template_values['alert'] = alert

        regions = Region.all().filter('owner = ', None).order('title').fetch(1000)
        self.template_values['regions'] = [{'title': x.title, 'id': x.key().id()} for x in regions]
        template = jinja_environment.get_template('upload.html')
        self.response.out.write(template.render(self.template_values))


class JsonTerrytoryList(webapp2.RequestHandler):
    def get(self):
        region = self.request.get('region')
        raion = self.request.get('raion')
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        if region and not raion:
            region = Region.by_id(region)
        elif raion:
            region = Region.by_id(raion)
        if region:
            childs = sorted(region.childs, key=lambda x: x.title)
            logging.warning(childs)
            self.response.out.write(json.dumps([{'title': x.title, 'id': x.key().id()} for x in childs]))


class JsonSubBudget(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        owner_id = self.request.get('owner_id')
        budget_id = self.request.get('budget_id')
        budget = Budget.by_id(budget_id)
        if not budget:
            self.response.out.write('')
        owner = BudgetLine.by_id(owner_id)
        if not owner:
            self.response.out.write('')
        sublines = BudgetLine.all().filter('budget = ', budget).filter('razdel = ', owner.razdel)\
            .order('podrazdel').order('statya').order('vid').fetch(1500)

        lines_count = sublines.count()
        result = []
        for i in range(lines_count-1):
            if sublines[i].vid == 0 and sublines[i+1] != 0:  # last line where vid == 0 and next is something else
                result.append(sublines[i])
        result = [budget_line(line) for line in result]
        self.response.out.write(json.dumps(result))


# class TaskHandler(webapp2.RequestHandler):
#     def get(self):
#         json_file = 'json/peoples.json'
#         with open(json_file) as json_data:
#             data = json.load(json_data)
#         for key in data:
#             taskqueue.add(url='/add_regions', params={'key': key}, queue_name='load-regions-queue')
#         self.redirect('/')

class RegionsHandler(webapp2.RequestHandler):
    def post(self):
        key = self.request.get('key')
        admin.load_regions(region_work=key)


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/upload', UploadHandler),
    ('/budget/(\d+)', BudgetPageHandler),
    ('/json_get_territory_list', JsonTerrytoryList),
    ('/json_get_subbudget', JsonSubBudget),
    ('/add_regions', RegionsHandler),
    # ('/add_task', TaskHandler),
], debug=True)
