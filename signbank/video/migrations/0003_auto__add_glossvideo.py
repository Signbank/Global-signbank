# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'GlossVideo'
        db.create_table('video_glossvideo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('videofile', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('gloss_sn', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('video', ['GlossVideo'])


    def backwards(self, orm):
        # Deleting model 'GlossVideo'
        db.delete_table('video_glossvideo')


    models = {
        'video.glossvideo': {
            'Meta': {'object_name': 'GlossVideo'},
            'gloss_sn': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'videofile': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        'video.video': {
            'Meta': {'object_name': 'Video'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'videofile': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['video']