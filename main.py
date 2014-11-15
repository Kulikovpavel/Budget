#!/usr/bin/env python
# -*- coding: utf-8 -*-

import webapp2
import jinja2
import urllib
import logging
import json
import admin
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
    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        self.template_values = {}

    def zero_level(self, budget_lines):
        zero_level = [budget_line(line) for line in budget_lines if line.podrazdel == 0]
        return json.dumps(zero_level)

    def chart_data(self, budgets):
        names_list = [line.title+" "+str(line.year) for line in budgets]
        count_list = [budget.region.count(budget.year) for budget in budgets]
        first_line = ["Раздел"] + names_list
        result = [] + [first_line]
        razdels = ["Общегосударственные вопросы",
                   "Национальная оборона",
                   "Национальная безопасность и правоохранительная деятельность",
                   "Национальная экономика",
                   "Жилищно-коммунальное хозяйство",
                   "Охрана окружающей среды",
                   "Образование",
                   "Культура и кинематография",
                   "Здравоохранение",
                   "Социальная политика",
                   "Физическая культура и спорт",
                   "Средства массовой информации",
                   "Обслуживание государственного и муниципального долга",
                   "Межбюджетные трансферты бюджетам субъектов Российской Федерации и муниципальных образований общего характера",
                   "Численность населения"]

        for i in range(len(razdels)):
            last_elem = i == len(razdels) - 1  # true if last element - for count
            razdel_num = i + 1
            chart_line = [] + [razdels[i]]
            for budget in budgets:
                if last_elem:
                    total = budget.region.count(budget.year)
                else:
                    budget_line = BudgetLine.all().filter('budget =', budget).filter('razdel =', razdel_num).filter('podrazdel =', 0).get()
                    if budget_line is None:
                        total = 0
                        sub = 0
                    else:
                        total = budget_line.total
                        sub = budget_line.total_sub  # subvention
                    # chart_line.append([total, sub])
                chart_line.append(total)
            result.append(chart_line)
        return json.dumps(result), json.dumps(count_list)


class MainHandler(BudgetHandler):
    def get(self):
        region_id = self.request.get('region')
        if region_id:
            region = Region.by_id(region_id)
        else:
            region = None
        if region:
            budgets = Budget.all().ancestor(main_key()).filter('region =', region).order('year').fetch(300)
        else:
            budgets = Budget.all().ancestor(main_key()).order('-created').fetch(300)
        self.template_values['budgets'] = budgets
        self.template_values['flag_region'] = True if region else False
        self.template_values['chart_data'], self.template_values['count_list'] = self.chart_data(budgets)
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(self.template_values))


class BudgetPageHandler(BudgetHandler):
    def get(self, id):
        id = int(urllib.unquote(id))
        budget = Budget.by_id(id)

        self.template_values['budget'] = budget
        self.template_values['count'] = budget.region.count(budget.year)
        zero_level_lines = BudgetLine.all().filter('budget =', budget).filter('podrazdel = ', 0).order('razdel').fetch(1000)
        self.template_values['zero_level'] = self.zero_level(zero_level_lines)
        self.template_values['lines'] = json.dumps([table_line(line) for line in zero_level_lines])
        # self.template_values['end_level'] = self.end_level(budget.table)
        self.template_values['end_level'] = []
        self.template_values['table_headers'] = ["Наименование", "Раздел", "Подраздел", "Вид", "Статья", "Всего (тыс.р.)", "Субвенции (тыс.р.)"]
        template = jinja_environment.get_template('budget.html')
        self.response.out.write(template.render(self.template_values))

    def post(self, id=0):
        excel_table = self.request.get('excel_table')
        link = self.request.get('link')
        year = int(self.request.get('year'))
        password = self.request.get('password')

        region = self.request.get('region')
        raion = self.request.get('raion')
        mun = self.request.get('municipality')
        if region == '0':
            self.upload_alert_redirect('Регион не выбран')
            return
        region_id = None
        if mun and mun != '0':
            region_id = mun
        elif raion and raion != '0':
            region_id = raion
        elif region and region != '0':
            region_id = region
        else:
            self.upload_alert_redirect('Выберите регион')
            return
        region = Region.by_id(region_id)
        if not region:
            self.upload_alert_redirect('Регион не найден')
            return
        excel_table = excel_table.replace('\r','')
        lines = excel_table.split('\n')
        table = [[word if word != "" else "0" for word in line.split('\t')] for line in lines if line != ""]
        if len(table) > 2 and len(table[0]) > 2:
            budget = Budget.all().filter('region =', region).filter('year =', year).get()
            if not budget:
                budget = Budget(title=region.title,
                                region=region,
                                password=make_salt(15),  # random letters
                                table=table,
                                year=year,
                                type='rashod',
                                link=link,
                                parent=main_key())
                budget.put()
            else:
                # logging.warning('Current password - %s, budget - %s' % (password, budget.password))
                if budget.password is None:
                    budget.password = make_salt(15)
                    budget.put()
                if password == budget.password:
                    budget.table = table
                    budget.put()
                else:
                    logging.warning("Wrong password! " + str(budget.key().id()))
                    self.upload_alert_redirect('Бюджет существует, введите пароль под кнопкой')
                    return
            budget.create_budget_lines(table)
            self.redirect("/budget/"+str(budget.key().id()))
        else:
            self.upload_alert_redirect('Таблица неверная')

    def upload_alert_redirect(self, alert):
        params = {'alert': alert}
        encoded_params = urllib.urlencode(params)
        self.redirect('/upload?'+encoded_params)


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
        owner = BudgetLine.by_id(owner_id, budget)
        if owner is None:
            self.response.out.write('')
        sublines = BudgetLine.all().ancestor(budget).filter('budget = ', budget).filter('razdel = ', owner.razdel).order('podrazdel').order('statya').order('vid').fetch(1500)

        lines_count = len(sublines)
        result = []
        for i in range(lines_count-1):
            # logging.warning(sublines[i].title + sublines[i].vid)
            if sublines[i].vid == 0 and sublines[i+1].vid != 0:  # last line where vid == 0 and next is something else
                result.append(sublines[i])
        result = [budget_line(line) for line in result]

        result_dict = {'result': result, 'sublines': [table_line(line) for line in sublines]}
        self.response.out.write(json.dumps(result_dict))


class RegionsHandler(webapp2.RequestHandler):
    def post(self):
        key = self.request.get('key')
        admin.load_regions(region_work=key)

class ChangesHandler(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('changes.html')
        self.response.out.write(template.render())

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/upload', UploadHandler),
    ('/budget/(\d+)', BudgetPageHandler),
    ('/json_get_territory_list', JsonTerrytoryList),
    ('/json_get_subbudget', JsonSubBudget),
    ('/add_regions', RegionsHandler),
    ('/changes', ChangesHandler)
], debug=True)
