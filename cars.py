import requests
from bs4 import BeautifulSoup
import re

logging = True

base_url='https://www.carsguide.com.au'

'''
    Terminology

    a 'make' is like a manufacturer e.g. Holden, Ford
    a 'model' is for example Holden Commodore, Ford Mustang

'''

class Make:
    def __init__(self, name, url):
        self.name = name
        self.url = url

class Model:
    def __init__(self, name, url, make):
        self.model_name = name
        self.model_url = url
        assert(type(make) is Make)
        self.make = make

class Build(Model):
    def __init__(self, model, year, build_description, body_type, specs, identifier, build_url):
        assert(type(model) is Model)
        super(Build, self).__init__(model.model_name, model.model_url, model.make)
        self.year = year
        self.build_description = build_description
        self.body_type = body_type
        self.specs = specs
        self.identifier = identifier
        self.build_url = build_url

def get_makes():
    '''
    return -- a list of Make objects containing the name and URL for all makes of cars on carsguide.com.au
    '''
    url = base_url + '/holden/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text,'lxml')
    makes=soup.findAll('span',{'class':'field-content'})

    makes=list(map(lambda x: Make(name=x.text, url=base_url + x.find_all()[0]['href']), makes))
    return makes

def get_models(make):
    ''''
    return -- a list of Model objects - all models for the given make of car
    '''
    url = make.url
    response = requests.get(url)
    soup = BeautifulSoup(response.text,'lxml')
    models_div = soup.find('div', {'class':'cg-model-other-model'})
    models = models_div.findAll('span',{'class':'model-name'})
    models = list(map(lambda x: Model(name=x.text, url=base_url+x.parent['href'],make=make),models))
    return models

def get_years(model):
    '''
    return dictionary e.g. {'2018':'https://www.carsguide.com.au/abarth/124/price/2018'}
    '''
    url = model.model_url
    response = requests.get(url)
    soup = BeautifulSoup(response.text,'lxml')
    url = base_url + soup.find_all('a', {'data-gtm-category':'pricing and spec'})[0]['href']
    response = requests.get(url)
    soup = BeautifulSoup(response.text,'lxml')
    years = soup.findAll('td',{'data-label':'Year'})
    years = list(map(lambda x: {'year':x.text,'href':base_url + x.parent['onclick'].replace('location=','').replace("'",'')}, years))
    return years

def get_builds(model, year):
    '''
    year is a dict e.g. {'year':'2018','href':'https://www.carsguide.com.au/abarth/124/price/2018'}
    '''
    url = year['href']
    response = requests.get(url)
    soup = BeautifulSoup(response.text,'lxml')
    div = soup.find('div', {'id': 'pricingspecstablelist'})
    children = div.find_all(recursive=False)
    builds = []
    i=0
    while i < len(children):
        # get body type
        body_type = children[i].text
        i+=1
        # get specs
        tbody = children[i].find_all(recursive=False)[1]
        i+=1
        rows = tbody.find_all(recursive=False)
        for row in rows:
            build_url = base_url + row['onclick'].replace('location=','').replace("'",'')
            match = re.search("id=.+'", row['onclick'])
            identifier = None
            if match is not None:
                identifier = match.group(0).replace('id=','').replace("'","")
            td = row.find_all(recursive=False)
            build_description = td[0].text
            items = td[1].find_all(recursive=False)
            specs = []
            for item in items:
                if item.find_all() == []: specs.append(item.text)
                else: specs.append(item.find_all('span', class_=lambda x: x!='hidden-xs')[0].text)
            build = Build(model, year, build_description, body_type, specs, identifier, build_url)
            builds.append(build)
    return builds


models = {} # key=Make.name, value=[Model]
model_years = {} # key=(Make.name,Model.model_name), value={'year':'2011','href':'http://...'}
builds = {} # key=(Make.name,Model.model_name,year)

makes = get_makes()

def get_all_models():
    for make in makes:
        if logging: print('Getting models for make: ' + make.name)
        models[make.name] = get_models(make)

def get_all_builds():
    for make, models_ in models.items():
        for model in models_:
            try: years = get_years(model)
            except: pass
            model_years[(make,model.model_name)] = years
            for year in years:
                print('Getting builds for ' + make + ', ' + model.model_name + ' ' + year['year'])
                blds = get_builds(model, year)
                for b in blds:
                    url = b.build_url
                    response = requests.get(url)
                    soup = BeautifulSoup(response.text,'lxml')
                    summary_blocks = soup.find_all('div', {'class':'summaryBlock'})
                    for block in summary_blocks:
                        text = block.text.strip().replace('(combined)','')
                        if re.search('\d+(\.\d+)?\s*L\s*/\s*\d+(\.\d+)?\s*km',text) is not None:
                            fuel_economy_text = text
                            print(fuel_economy_text)
                            match = re.search('\d+(\.\d+)?L',fuel_economy_text)
                            litres = float(match.group(0).replace('L',''))
                            match = re.search('\d+(\.\d+)?km',fuel_economy_text)
                            km = float(match.group(0).replace('km',''))
                            fuel_economy = {}
                            fuel_economy['text'] = fuel_economy_text
                            fuel_economy['litres'] = litres
                            fuel_economy['km'] = km
                            b.fuel_economy = fuel_economy
                builds[(make,model.model_name,year['year'])] = blds
