# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'GlossVideo.version'
        db.add_column('video_glossvideo', 'version',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'GlossVideo.version'
        db.delete_column('video_glossvideo', 'version')


    models = {
        'video.glossvideo': {
            'Meta': {'object_name': 'GlossVideo'},
            'gloss_sn': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'version': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'videofile': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        'video.video': {
            'Meta': {'object_name': 'Video'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'videofile': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['video']