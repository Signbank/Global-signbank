# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Gloss.qualitytf'
        db.delete_column('dictionary_gloss', 'qualitytf')

        # Deleting field 'Gloss.worktf'
        db.delete_column('dictionary_gloss', 'worktf')

        # Deleting field 'Gloss.angcongtf'
        db.delete_column('dictionary_gloss', 'angcongtf')

        # Deleting field 'Gloss.bodyprtstf'
        db.delete_column('dictionary_gloss', 'bodyprtstf')

        # Deleting field 'Gloss.begindirtf'
        db.delete_column('dictionary_gloss', 'begindirtf')

        # Deleting field 'Gloss.daystf'
        db.delete_column('dictionary_gloss', 'daystf')

        # Deleting field 'Gloss.roomstf'
        db.delete_column('dictionary_gloss', 'roomstf')

        # Deleting field 'Gloss.seonlytf'
        db.delete_column('dictionary_gloss', 'seonlytf')

        # Deleting field 'Gloss.sextf'
        db.delete_column('dictionary_gloss', 'sextf')

        # Deleting field 'Gloss.propernametf'
        db.delete_column('dictionary_gloss', 'propernametf')

        # Deleting field 'Gloss.numbertf'
        db.delete_column('dictionary_gloss', 'numbertf')

        # Deleting field 'Gloss.groomtf'
        db.delete_column('dictionary_gloss', 'groomtf')

        # Deleting field 'Gloss.alternate'
        db.delete_column('dictionary_gloss', 'alternate')

        # Deleting field 'Gloss.questsigntf'
        db.delete_column('dictionary_gloss', 'questsigntf')

        # Deleting field 'Gloss.doublehnd'
        db.delete_column('dictionary_gloss', 'doublehnd')

        # Deleting field 'Gloss.familytf'
        db.delete_column('dictionary_gloss', 'familytf')

        # Deleting field 'Gloss.twohand'
        db.delete_column('dictionary_gloss', 'twohand')

        # Deleting field 'Gloss.clothingtf'
        db.delete_column('dictionary_gloss', 'clothingtf')

        # Deleting field 'Gloss.marginaltf'
        db.delete_column('dictionary_gloss', 'marginaltf')

        # Deleting field 'Gloss.sensestf'
        db.delete_column('dictionary_gloss', 'sensestf')

        # Deleting field 'Gloss.traveltf'
        db.delete_column('dictionary_gloss', 'traveltf')

        # Deleting field 'Gloss.cookingtf'
        db.delete_column('dictionary_gloss', 'cookingtf')

        # Deleting field 'Gloss.onehand'
        db.delete_column('dictionary_gloss', 'onehand')

        # Deleting field 'Gloss.peopletf'
        db.delete_column('dictionary_gloss', 'peopletf')

        # Deleting field 'Gloss.gensigntf'
        db.delete_column('dictionary_gloss', 'gensigntf')

        # Deleting field 'Gloss.timetf'
        db.delete_column('dictionary_gloss', 'timetf')

        # Deleting field 'Gloss.transltf'
        db.delete_column('dictionary_gloss', 'transltf')

        # Deleting field 'Gloss.setf'
        db.delete_column('dictionary_gloss', 'setf')

        # Deleting field 'Gloss.doubtlextf'
        db.delete_column('dictionary_gloss', 'doubtlextf')

        # Deleting field 'Gloss.utensilstf'
        db.delete_column('dictionary_gloss', 'utensilstf')

        # Deleting field 'Gloss.arithmetictf'
        db.delete_column('dictionary_gloss', 'arithmetictf')

        # Deleting field 'Gloss.drinkstf'
        db.delete_column('dictionary_gloss', 'drinkstf')

        # Deleting field 'Gloss.recreationtf'
        db.delete_column('dictionary_gloss', 'recreationtf')

        # Deleting field 'Gloss.carstf'
        db.delete_column('dictionary_gloss', 'carstf')

        # Deleting field 'Gloss.saluttf'
        db.delete_column('dictionary_gloss', 'saluttf')

        # Deleting field 'Gloss.eductf'
        db.delete_column('dictionary_gloss', 'eductf')

        # Deleting field 'Gloss.cathschtf'
        db.delete_column('dictionary_gloss', 'cathschtf')

        # Deleting field 'Gloss.telecomtf'
        db.delete_column('dictionary_gloss', 'telecomtf')

        # Deleting field 'Gloss.obscuretf'
        db.delete_column('dictionary_gloss', 'obscuretf')

        # Deleting field 'Gloss.dirtf'
        db.delete_column('dictionary_gloss', 'dirtf')

        # Deleting field 'Gloss.sporttf'
        db.delete_column('dictionary_gloss', 'sporttf')

        # Deleting field 'Gloss.enddirtf'
        db.delete_column('dictionary_gloss', 'enddirtf')

        # Deleting field 'Gloss.religiontf'
        db.delete_column('dictionary_gloss', 'religiontf')

        # Deleting field 'Gloss.artstf'
        db.delete_column('dictionary_gloss', 'artstf')

        # Deleting field 'Gloss.domonly'
        db.delete_column('dictionary_gloss', 'domonly')

        # Deleting field 'Gloss.fingersptf'
        db.delete_column('dictionary_gloss', 'fingersptf')

        # Deleting field 'Gloss.govtf'
        db.delete_column('dictionary_gloss', 'govtf')

        # Deleting field 'Gloss.animalstf'
        db.delete_column('dictionary_gloss', 'animalstf')

        # Deleting field 'Gloss.orienttf'
        db.delete_column('dictionary_gloss', 'orienttf')

        # Deleting field 'Gloss.otherreltf'
        db.delete_column('dictionary_gloss', 'otherreltf')

        # Deleting field 'Gloss.techtf'
        db.delete_column('dictionary_gloss', 'techtf')

        # Deleting field 'Gloss.metalgtf'
        db.delete_column('dictionary_gloss', 'metalgtf')

        # Deleting field 'Gloss.furntf'
        db.delete_column('dictionary_gloss', 'furntf')

        # Deleting field 'Gloss.feeltf'
        db.delete_column('dictionary_gloss', 'feeltf')

        # Deleting field 'Gloss.moneytf'
        db.delete_column('dictionary_gloss', 'moneytf')

        # Deleting field 'Gloss.langactstf'
        db.delete_column('dictionary_gloss', 'langactstf')

        # Deleting field 'Gloss.varlextf'
        db.delete_column('dictionary_gloss', 'varlextf')

        # Deleting field 'Gloss.lawtf'
        db.delete_column('dictionary_gloss', 'lawtf')

        # Deleting field 'Gloss.materialstf'
        db.delete_column('dictionary_gloss', 'materialstf')

        # Deleting field 'Gloss.deaftf'
        db.delete_column('dictionary_gloss', 'deaftf')

        # Deleting field 'Gloss.para'
        db.delete_column('dictionary_gloss', 'para')

        # Deleting field 'Gloss.crudetf'
        db.delete_column('dictionary_gloss', 'crudetf')

        # Deleting field 'Gloss.stateschtf'
        db.delete_column('dictionary_gloss', 'stateschtf')

        # Deleting field 'Gloss.opaquetf'
        db.delete_column('dictionary_gloss', 'opaquetf')

        # Deleting field 'Gloss.foodstf'
        db.delete_column('dictionary_gloss', 'foodstf')

        # Deleting field 'Gloss.obsoletetf'
        db.delete_column('dictionary_gloss', 'obsoletetf')

        # Deleting field 'Gloss.judgetf'
        db.delete_column('dictionary_gloss', 'judgetf')

        # Deleting field 'Gloss.ordertf'
        db.delete_column('dictionary_gloss', 'ordertf')

        # Deleting field 'Gloss.colorstf'
        db.delete_column('dictionary_gloss', 'colorstf')

        # Deleting field 'Gloss.weathertf'
        db.delete_column('dictionary_gloss', 'weathertf')

        # Deleting field 'Gloss.locdirtf'
        db.delete_column('dictionary_gloss', 'locdirtf')

        # Deleting field 'Gloss.catholictf'
        db.delete_column('dictionary_gloss', 'catholictf')

        # Deleting field 'Gloss.citiestf'
        db.delete_column('dictionary_gloss', 'citiestf')

        # Deleting field 'Gloss.naturetf'
        db.delete_column('dictionary_gloss', 'naturetf')

        # Deleting field 'Gloss.sym'
        db.delete_column('dictionary_gloss', 'sym')

        # Deleting field 'Gloss.transptf'
        db.delete_column('dictionary_gloss', 'transptf')

        # Deleting field 'Gloss.restricttf'
        db.delete_column('dictionary_gloss', 'restricttf')

        # Deleting field 'Gloss.mindtf'
        db.delete_column('dictionary_gloss', 'mindtf')

        # Deleting field 'Gloss.shoppingtf'
        db.delete_column('dictionary_gloss', 'shoppingtf')

        # Deleting field 'Gloss.quantitytf'
        db.delete_column('dictionary_gloss', 'quantitytf')

        # Deleting field 'Gloss.reglextf'
        db.delete_column('dictionary_gloss', 'reglextf')

        # Deleting field 'Gloss.shapestf'
        db.delete_column('dictionary_gloss', 'shapestf')

        # Deleting field 'Gloss.physicalactstf'
        db.delete_column('dictionary_gloss', 'physicalactstf')

        # Deleting field 'Gloss.jwtf'
        db.delete_column('dictionary_gloss', 'jwtf')

        # Deleting field 'Gloss.bodyloctf'
        db.delete_column('dictionary_gloss', 'bodyloctf')


    def backwards(self, orm):
        # Adding field 'Gloss.qualitytf'
        db.add_column('dictionary_gloss', 'qualitytf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.worktf'
        db.add_column('dictionary_gloss', 'worktf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.angcongtf'
        db.add_column('dictionary_gloss', 'angcongtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.bodyprtstf'
        db.add_column('dictionary_gloss', 'bodyprtstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.begindirtf'
        db.add_column('dictionary_gloss', 'begindirtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.daystf'
        db.add_column('dictionary_gloss', 'daystf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.roomstf'
        db.add_column('dictionary_gloss', 'roomstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.seonlytf'
        db.add_column('dictionary_gloss', 'seonlytf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.sextf'
        db.add_column('dictionary_gloss', 'sextf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.propernametf'
        db.add_column('dictionary_gloss', 'propernametf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.numbertf'
        db.add_column('dictionary_gloss', 'numbertf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.groomtf'
        db.add_column('dictionary_gloss', 'groomtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.alternate'
        db.add_column('dictionary_gloss', 'alternate',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.questsigntf'
        db.add_column('dictionary_gloss', 'questsigntf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.doublehnd'
        db.add_column('dictionary_gloss', 'doublehnd',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.familytf'
        db.add_column('dictionary_gloss', 'familytf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.twohand'
        db.add_column('dictionary_gloss', 'twohand',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.clothingtf'
        db.add_column('dictionary_gloss', 'clothingtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.marginaltf'
        db.add_column('dictionary_gloss', 'marginaltf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.sensestf'
        db.add_column('dictionary_gloss', 'sensestf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.traveltf'
        db.add_column('dictionary_gloss', 'traveltf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.cookingtf'
        db.add_column('dictionary_gloss', 'cookingtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.onehand'
        db.add_column('dictionary_gloss', 'onehand',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.peopletf'
        db.add_column('dictionary_gloss', 'peopletf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.gensigntf'
        db.add_column('dictionary_gloss', 'gensigntf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.timetf'
        db.add_column('dictionary_gloss', 'timetf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.transltf'
        db.add_column('dictionary_gloss', 'transltf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.setf'
        db.add_column('dictionary_gloss', 'setf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.doubtlextf'
        db.add_column('dictionary_gloss', 'doubtlextf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.utensilstf'
        db.add_column('dictionary_gloss', 'utensilstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.arithmetictf'
        db.add_column('dictionary_gloss', 'arithmetictf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.drinkstf'
        db.add_column('dictionary_gloss', 'drinkstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.recreationtf'
        db.add_column('dictionary_gloss', 'recreationtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.carstf'
        db.add_column('dictionary_gloss', 'carstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.saluttf'
        db.add_column('dictionary_gloss', 'saluttf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.eductf'
        db.add_column('dictionary_gloss', 'eductf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.cathschtf'
        db.add_column('dictionary_gloss', 'cathschtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.telecomtf'
        db.add_column('dictionary_gloss', 'telecomtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.obscuretf'
        db.add_column('dictionary_gloss', 'obscuretf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.dirtf'
        db.add_column('dictionary_gloss', 'dirtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.sporttf'
        db.add_column('dictionary_gloss', 'sporttf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.enddirtf'
        db.add_column('dictionary_gloss', 'enddirtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.religiontf'
        db.add_column('dictionary_gloss', 'religiontf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.artstf'
        db.add_column('dictionary_gloss', 'artstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.domonly'
        db.add_column('dictionary_gloss', 'domonly',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.fingersptf'
        db.add_column('dictionary_gloss', 'fingersptf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.govtf'
        db.add_column('dictionary_gloss', 'govtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.animalstf'
        db.add_column('dictionary_gloss', 'animalstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.orienttf'
        db.add_column('dictionary_gloss', 'orienttf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.otherreltf'
        db.add_column('dictionary_gloss', 'otherreltf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.techtf'
        db.add_column('dictionary_gloss', 'techtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.metalgtf'
        db.add_column('dictionary_gloss', 'metalgtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.furntf'
        db.add_column('dictionary_gloss', 'furntf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.feeltf'
        db.add_column('dictionary_gloss', 'feeltf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.moneytf'
        db.add_column('dictionary_gloss', 'moneytf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.langactstf'
        db.add_column('dictionary_gloss', 'langactstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.varlextf'
        db.add_column('dictionary_gloss', 'varlextf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.lawtf'
        db.add_column('dictionary_gloss', 'lawtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.materialstf'
        db.add_column('dictionary_gloss', 'materialstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.deaftf'
        db.add_column('dictionary_gloss', 'deaftf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.para'
        db.add_column('dictionary_gloss', 'para',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.crudetf'
        db.add_column('dictionary_gloss', 'crudetf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.stateschtf'
        db.add_column('dictionary_gloss', 'stateschtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.opaquetf'
        db.add_column('dictionary_gloss', 'opaquetf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.foodstf'
        db.add_column('dictionary_gloss', 'foodstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.obsoletetf'
        db.add_column('dictionary_gloss', 'obsoletetf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.judgetf'
        db.add_column('dictionary_gloss', 'judgetf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.ordertf'
        db.add_column('dictionary_gloss', 'ordertf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.colorstf'
        db.add_column('dictionary_gloss', 'colorstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.weathertf'
        db.add_column('dictionary_gloss', 'weathertf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.locdirtf'
        db.add_column('dictionary_gloss', 'locdirtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.catholictf'
        db.add_column('dictionary_gloss', 'catholictf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.citiestf'
        db.add_column('dictionary_gloss', 'citiestf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.naturetf'
        db.add_column('dictionary_gloss', 'naturetf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.sym'
        db.add_column('dictionary_gloss', 'sym',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.transptf'
        db.add_column('dictionary_gloss', 'transptf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.restricttf'
        db.add_column('dictionary_gloss', 'restricttf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.mindtf'
        db.add_column('dictionary_gloss', 'mindtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.shoppingtf'
        db.add_column('dictionary_gloss', 'shoppingtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.quantitytf'
        db.add_column('dictionary_gloss', 'quantitytf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.reglextf'
        db.add_column('dictionary_gloss', 'reglextf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.shapestf'
        db.add_column('dictionary_gloss', 'shapestf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.physicalactstf'
        db.add_column('dictionary_gloss', 'physicalactstf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.jwtf'
        db.add_column('dictionary_gloss', 'jwtf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Gloss.bodyloctf'
        db.add_column('dictionary_gloss', 'bodyloctf',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)


    models = {
        'dictionary.definition': {
            'Meta': {'ordering': "['gloss']", 'object_name': 'Definition'},
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'gloss': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dictionary.Gloss']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'dictionary.dialect': {
            'Meta': {'ordering': "['language', 'name']", 'object_name': 'Dialect'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dictionary.Language']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'dictionary.gloss': {
            'BookProb': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'InMainBook': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'InMedLex': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'InSuppBook': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'Meta': {'ordering': "['idgloss']", 'object_name': 'Gloss'},
            'NotBkDBOnly': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'Palm_orientation': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'SpecialCore': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'StemSN': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'annotation_idgloss': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'aslgloss': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'asloantf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'asltf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'blend': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'blendtf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'bslgloss': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'bslloantf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'bsltf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'comp': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'compound': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'comptf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'dialect': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['dictionary.Dialect']", 'symmetrical': 'False'}),
            'domhndsh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'blank': 'True'}),
            'handedness': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'healthtf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'idgloss': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'inCD': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'inWeb': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'inittext': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'}),
            'inittf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'isNew': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'language': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['dictionary.Language']", 'symmetrical': 'False'}),
            'locprim': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'locsecond': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'morph': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'queries': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sedefinetf': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'segloss': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'sense': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sn': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'subhndsh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'tjspeculate': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'dictionary.keyword': {
            'Meta': {'ordering': "['text']", 'object_name': 'Keyword'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'dictionary.language': {
            'Meta': {'ordering': "['name']", 'object_name': 'Language'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'dictionary.relation': {
            'Meta': {'ordering': "['source']", 'object_name': 'Relation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relation_sources'", 'to': "orm['dictionary.Gloss']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relation_targets'", 'to': "orm['dictionary.Gloss']"})
        },
        'dictionary.translation': {
            'Meta': {'ordering': "['gloss', 'index']", 'object_name': 'Translation'},
            'gloss': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dictionary.Gloss']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'translation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dictionary.Keyword']"})
        }
    }

    complete_apps = ['dictionary']