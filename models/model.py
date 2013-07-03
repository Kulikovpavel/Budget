from google.appengine.ext import db
import json
from helpers import *


class JsonProperty(db.TextProperty):
    def validate(self, value):
        return value

    def get_value_for_datastore(self, model_instance):
        result = super(JsonProperty, self).get_value_for_datastore(model_instance)
        result = json.dumps(result)
        return db.Text(result)

    def make_value_from_datastore(self, value):
        try:
            value = json.loads(str(value))
        except:
            pass
        return super(JsonProperty, self).make_value_from_datastore(value)


class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty(required = True)

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent=users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u
    @classmethod
    def by_email(cls, email):
        u = User.all().filter('email =', email).get()
        return u
    @classmethod
    def register(cls, name, email, pw ):
        pw_hash = make_pw_hash(email, pw)
        return User(parent = users_key(),
            name = name,
            pw_hash = pw_hash,
            email = email)

    @classmethod
    def login(cls, email, pw):
        u = cls.by_email(email)
        if u and valid_pw(email, pw, u.pw_hash):
            return u

class Region(db.Model):
    title = db.StringProperty()
    region_type = db.StringProperty()
    owner = db.SelfReferenceProperty(collection_name='childs')

    @classmethod
    def by_title(cls, title):
        r = Region.all().filter('title =', title).get()
        return r

    @classmethod
    def by_id(cls, id):
        return Region.get_by_id(int(id), parent=db.Key.from_path('regions', 'default'))

    def count(self, year=2012):
        c = RegionCount.all().filter('region = ', self).filter('year = ', year).get()
        if not c:
            c = RegionCount.all().filter('region = ', self).filter('year = ', 2012).get()
        if not c:
            return 1
        return c.count

class RegionCount(db.Model):
    count = db.IntegerProperty()
    year = db.IntegerProperty()
    region = db.ReferenceProperty(Region, collection_name='counts')


class Budget(db.Model):
    title = db.StringProperty()
    description = db.TextProperty()
    region = db.ReferenceProperty(Region, collection_name='budgets')
    table = JsonProperty()
    user = db.ReferenceProperty(User, collection_name='budgets')
    year = db.IntegerProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    type = db.StringProperty()
    @classmethod
    def by_id(cls, uid):
        return Budget.get_by_id(int(uid), parent=main_key())

class BudgetLine(db.Model):
    budget = db.ReferenceProperty(Budget,  collection_name='budget_lines')
    title = db.StringProperty()
    line_type = db.StringProperty()
    razdel = db.IntegerProperty()
    podrazdel = db.IntegerProperty()
    statya = db.IntegerProperty()
    vid = db.IntegerProperty()
    total = db.FloatProperty()
    total_sub = db.FloatProperty()  # subvention
    total_complete = db.FloatProperty()
    total_complete_sub = db.FloatProperty()

    @classmethod
    def by_id(cls, uid):
        return BudgetLine.get_by_id(int(uid))

class Comment(db.Model):
    text = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    picture = db.ReferenceProperty(Budget, collection_name='comments')
    owner = db.SelfReferenceProperty(collection_name='childs')
    user = db.ReferenceProperty(User,required=True,  collection_name='comments')
