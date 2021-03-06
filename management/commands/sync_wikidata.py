# -*- coding: utf-8 -*-

"""
sync_wikidata.py
superlachaise_api

Created by Maxime Le Moine on 28/05/2015.
Copyright (c) 2015 Maxime Le Moine.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    
    http:www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import datetime, json, os, requests, sys, time, traceback
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone, translation
from django.utils.translation import ugettext as _

from superlachaise_api.models import *

def print_unicode(str):
    print str.encode('utf-8')

def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj

def none_to_blank(s):
    if s is None:
        return u''
    return unicode(s)

class Command(BaseCommand):
    
    def request_wikidata(self, wikidata_codes):
        result = {}
        last_continue = {
            'continue': '',
        }
        languages = '|'.join(Language.objects.all().values_list('code', flat=True))
        ids = '|'.join(wikidata_codes).encode('utf8')
        props = '|'.join(['labels', 'descriptions', 'claims', 'sitelinks'])
        
        while True:
            # Request properties
            params = {
                'languages': languages,
                'action': 'wbgetentities',
                'props': props,
                'format': 'json',
                'ids': ids,
            }
            params.update(last_continue)
            
            if settings.MEDIAWIKI_USER_AGENT:
                headers = {"User-Agent" : settings.MEDIAWIKI_USER_AGENT}
            else:
                raise 'no USER_AGENT defined in settings.py'
            
            json_result = requests.get('https://www.wikidata.org/w/api.php', params=params, headers=headers).json()
            
            if 'entities' in json_result:
                result.update(json_result['entities'])
            
            if 'continue' not in json_result: break
            
            last_continue = json_result['continue']
        
        return result
    
    def get_instance_of(self, entity):
        try:
            p31 = entity['claims']['P31']
            
            result = []
            for entry in p31:
                result.append('Q' + str(entry['mainsnak']['datavalue']['value']['numeric-id']))
            
            return result
        except:
            return []
    
    def get_occupations(self, entity):
        try:
            p106 = entity['claims']['P106']
            
            result = []
            for entry in p106:
                result.append('Q' + str(entry['mainsnak']['datavalue']['value']['numeric-id']))
            
            return result
        except:
            return []
    
    def get_sex_or_gender(self, entity):
        try:
            p31 = entity['claims']['P21']
            
            result = []
            if len(p31) == 1:
                result = 'Q' + str(p31[0]['mainsnak']['datavalue']['value']['numeric-id'])
            
            return result
        except:
            return []
    
    def get_wikimedia_commons_category(self, entity):
        try:
            # Use P373
            p373 = entity['claims']['P373']
            
            wikimedia_commons = none_to_blank(p373[0]['mainsnak']['datavalue']['value'])
            
            # Delete random trailing character
            return wikimedia_commons.replace(u'\u200e',u'')
        except:
            return u''
    
    def get_wikimedia_commons_grave_category(self, entity):
        try:
            p119 = entity['claims']['P119']
            
            for location_of_burial in p119:
                if ('Q' + str(location_of_burial['mainsnak']['datavalue']['value']['numeric-id'])) in self.accepted_locations_of_burial:
                    p373 = location_of_burial['qualifiers']['P373']
                    break
            
            wikimedia_commons = none_to_blank(p373[0]['datavalue']['value'])
            
            # Delete random trailing character
            return wikimedia_commons.replace(u'\u200e',u'')
        except:
            return u''
    
    def get_date(self, entity, date_code):
        try:
            date = entity['claims'][date_code]
            
            date_value = date[0]['mainsnak']['datavalue']['value']
            
            precision_string = date_value['precision']
            date_string = date_value['time']
            
            date = datetime.date(*time.strptime(date_string[1:11], "%Y-%m-%d")[:3])
            
            # Convert accuracy
            if precision_string == 9:
                accuracy = WikidataEntry.YEAR
            elif precision_string == 10:
                accuracy = WikidataEntry.MONTH
            elif precision_string == 11:
                accuracy = WikidataEntry.DAY
            else:
                raise BaseException
            
            return (date, accuracy)
        except:
            return (None, u'')
    
    def get_name(self, entity, language_code):
        try:
            name = entity['labels'][language_code]
            
            return none_to_blank(name['value'])
        except:
            return u''
    
    def get_wikipedia(self, entity, language_code):
        try:
            wikipedia = entity['sitelinks'][language_code + 'wiki']
            
            return none_to_blank(wikipedia['title'])
        except:
            return u''
    
    def get_description(self, entity, language_code):
        try:
            description = entity['descriptions'][language_code]
            
            return none_to_blank(description['value'])
        except:
            return u''
    
    def get_grave_of_wikidata(self, entity):
        try:
            p31 = entity['claims']['P31']
            
            result = []
            for entry in p31:
                if str(entry['mainsnak']['datavalue']['value']['numeric-id']) == '173387':
                    for p642 in entry['qualifiers']['P642']:
                        result.append('Q' + str(p642['datavalue']['value']['numeric-id']))
                    break
            
            return result
        except:
            return None
    
    def get_person_burial_plot_reference(self, entity):
        try:
            p119 = entity['claims']['P119']
            
            for location_of_burial in p119:
                if ('Q' + str(location_of_burial['mainsnak']['datavalue']['value']['numeric-id'])) in self.accepted_locations_of_burial:
                    p965 = location_of_burial['qualifiers']['P965']
                    break
            
            return none_to_blank(p965[0]['datavalue']['value'])
        except:
            return u''
    
    def get_burial_plot_reference(self, entity):
        try:
            p965 = entity['claims']['P965']
            
            return none_to_blank(p965[0]['mainsnak']['datavalue']['value'])
        except:
            return u''
    
    def get_field_of_profession(self, entity):
        try:
            p965 = entity['claims']['P965']
            
            return none_to_blank(p965[0]['mainsnak']['datavalue']['value'])
        except:
            return u''
    
    def get_values_from_entity(self, entity):
        result = {}
        
        instance_of = self.get_instance_of(entity)
        result['instance_of'] = ';'.join(instance_of)
        
        result['wikimedia_commons_category'] = self.get_wikimedia_commons_category(entity)
        
        if 'Q5' in instance_of:
            # human
            result['wikimedia_commons_grave_category'] = self.get_wikimedia_commons_grave_category(entity)
            result['burial_plot_reference'] = self.get_person_burial_plot_reference(entity)
            result['date_of_birth'], result['date_of_birth_accuracy'] = self.get_date(entity, 'P569')
            result['date_of_death'], result['date_of_death_accuracy'] = self.get_date(entity, 'P570')
            result['sex_or_gender'] = self.get_sex_or_gender(entity)
            result['occupations'] = ';'.join(self.get_occupations(entity))
        else:
            result['wikimedia_commons_grave_category'] = u''
            result['burial_plot_reference'] = self.get_burial_plot_reference(entity)
            result['date_of_birth'], result['date_of_birth_accuracy'] = (None, u'')
            result['date_of_death'], result['date_of_death_accuracy'] = (None, u'')
            result['sex_or_gender'] = u''
            result['occupations'] = u''
        
        if 'Q173387' in instance_of:
            # tomb
            grave_of_wikidata = self.get_grave_of_wikidata(entity)
            if grave_of_wikidata:
                for grave_of in grave_of_wikidata:
                    if not grave_of in self.wikidata_codes and not grave_of in self.grave_of_wikidata_codes:
                        self.grave_of_wikidata_codes.append(grave_of)
                result['grave_of_wikidata'] = ';'.join(grave_of_wikidata)
            else:
                result['grave_of_wikidata'] = u''
        else:
            result['grave_of_wikidata'] = u''
        
        return result
    
    def get_localized_values_from_entity(self, entity, language_code):
        result = {
            'name': self.get_name(entity, language_code),
            'wikipedia': self.get_wikipedia(entity, language_code),
            'description': self.get_description(entity, language_code),
        }
        
        return result
    
    def handle_localized_entity(self, wikidata_entry, language, localized_values_dict):
        # Get or create object in database
        target_object_id_dict = {"wikidata_entry": wikidata_entry, "language": language}
        wikidata_localized_entry, created = WikidataLocalizedEntry.objects.get_or_create(**target_object_id_dict)
        self.localized_fetched_objects_pks.append(wikidata_localized_entry.pk)
        modified = False
        
        if created:
            self.created_objects = self.created_objects + 1
        else:
            # Search for modifications
            for field, value in localized_values_dict.iteritems():
                if value != getattr(wikidata_localized_entry, field):
                    modified = True
                    self.modified_objects = self.modified_objects + 1
                    break
        
        if created or modified:
            for field, value in localized_values_dict.iteritems():
                setattr(wikidata_localized_entry, field, value)
            wikidata_localized_entry.save()
    
    def handle_entity(self, code, entity):
        # Get values
        values_dict = self.get_values_from_entity(entity)
        
        # Get or create object in database
        target_object_id_dict = {"wikidata_id": code}
        wikidata_entry, created = WikidataEntry.objects.get_or_create(**target_object_id_dict)
        self.fetched_objects_pks.append(wikidata_entry.pk)
        modified = False
        
        if created:
            self.created_objects = self.created_objects + 1
        else:
            # Search for modifications
            for field, value in values_dict.iteritems():
                if value != getattr(wikidata_entry, field):
                    modified = True
                    self.modified_objects = self.modified_objects + 1
                    break
        
        if created or modified:
            for field, value in values_dict.iteritems():
                setattr(wikidata_entry, field, value)
            wikidata_entry.save()
        
        for language in Language.objects.all():
            localized_values_dict = self.get_localized_values_from_entity(entity, language.code)
            if localized_values_dict:
                self.handle_localized_entity(wikidata_entry, language, localized_values_dict)
    
    def sync_wikidata(self, wikidata_ids):
        self.wikidata_codes = []
        
        # List wikidata codes
        if wikidata_ids:
            self.wikidata_codes = wikidata_ids.split('|')
        else:
            for openstreetmap_element in OpenStreetMapElement.objects.exclude(wikidata__exact=''):
                for wikidata in openstreetmap_element.wikidata.split(';'):
                    link = wikidata.split(':')[-1]
                    if not link in self.wikidata_codes:
                        self.wikidata_codes.append(link)
            for wikidata_entry in WikidataEntry.objects.exclude(grave_of_wikidata__exact=''):
                for link in wikidata_entry.grave_of_wikidata.split(';'):
                    if not link in self.wikidata_codes:
                        self.wikidata_codes.append(link)
        
        self.grave_of_wikidata_codes = []
        
        print_unicode(_('Requesting Wikidata codes from OpenStreetMap elements...'))
        self.wikidata_codes = list(set(self.wikidata_codes))
        
        self.fetched_objects_pks = []
        self.localized_fetched_objects_pks = []
        
        total = len(self.wikidata_codes)
        count = 0
        max_count_per_request = 25
        for chunk in [self.wikidata_codes[i:i+max_count_per_request] for i in range(0,len(self.wikidata_codes),max_count_per_request)]:
            print_unicode(str(count) + u'/' + str(total))
            count += len(chunk)
            
            entities = self.request_wikidata(chunk)
            for wikidata_code, entity in entities.iteritems():
                self.handle_entity(wikidata_code, entity)
        print_unicode(str(count) + u'/' + str(total))
        
        if self.grave_of_wikidata_codes:
            print_unicode(_('Requesting new Wikidata codes from grave_of...'))
            self.grave_of_wikidata_codes = list(set(self.grave_of_wikidata_codes))
            total = len(self.grave_of_wikidata_codes)
            count = 0
            max_count_per_request = 25
            for chunk in [self.grave_of_wikidata_codes[i:i+max_count_per_request] for i in range(0,len(self.grave_of_wikidata_codes),max_count_per_request)]:
                print_unicode(str(count) + u'/' + str(total))
                count += len(chunk)
            
                entities = self.request_wikidata(chunk)
                for wikidata_code, entity in entities.iteritems():
                    self.handle_entity(wikidata_code, entity)
            print_unicode(str(count) + u'/' + str(total))
        
        if not wikidata_ids:
            # Look for deleted elements
            for wikidata_entry in WikidataEntry.objects.exclude(pk__in=self.fetched_objects_pks):
                self.deleted_objects = self.deleted_objects + 1
                wikidata_entry.delete()
            for wikidata_localized_entry in WikidataLocalizedEntry.objects.exclude(Q(pk__in=self.localized_fetched_objects_pks) | ~Q(wikidata_entry__pk__in=self.fetched_objects_pks)):
                self.deleted_objects = self.deleted_objects + 1
                wikidata_localized_entry.delete()
    
    def add_arguments(self, parser):
        parser.add_argument('--wikidata_ids',
            action='store',
            dest='wikidata_ids')
    
    def handle(self, *args, **options):
        
        try:
            self.synchronization = Synchronization.objects.get(name=os.path.basename(__file__).split('.')[0].split('sync_')[-1])
        except:
            raise CommandError(sys.exc_info()[1])
        
        error = None
        
        try:
            translation.activate(settings.LANGUAGE_CODE)
            
            self.accepted_locations_of_burial = json.loads(Setting.objects.get(key=u'wikidata:accepted_locations_of_burial').value)
            
            self.created_objects = 0
            self.modified_objects = 0
            self.deleted_objects = 0
            self.errors = []
            
            print_unicode(_('== Start %s ==') % self.synchronization.name)
            self.sync_wikidata(options['wikidata_ids'])
            print_unicode(_('== End %s ==') % self.synchronization.name)
            
            self.synchronization.created_objects = self.created_objects
            self.synchronization.modified_objects = self.modified_objects
            self.synchronization.deleted_objects = self.deleted_objects
            self.synchronization.errors = ', '.join(self.errors)
            
            translation.deactivate()
        except:
            print_unicode(traceback.format_exc())
            error = sys.exc_info()[1]
            self.synchronization.errors = traceback.format_exc()
        
        self.synchronization.last_executed = timezone.now()
        self.synchronization.save()
        
        if error:
            raise CommandError(error)
