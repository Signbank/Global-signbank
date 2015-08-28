# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'InterpreterFeedback'
        db.create_table(u'feedback_interpreterfeedback', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('gloss', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dictionary.Gloss'])),
            ('comment', self.gf('django.db.models.fields.TextField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='unread', max_length=10)),
        ))
        db.send_create_signal(u'feedback', ['InterpreterFeedback'])


    def backwards(self, orm):
        # Deleting model 'InterpreterFeedback'
        db.delete_table(u'feedback_interpreterfeedback')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'dictionary.dialect': {
            'Meta': {'ordering': "['language', 'name']", 'object_name': 'Dialect'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Language']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'dictionary.gloss': {
            'Meta': {'ordering': "['idgloss']", 'object_name': 'Gloss'},
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
            'compound': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'comptf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'dialect': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['dictionary.Dialect']", 'symmetrical': 'False'}),
            'domhndsh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'final_domhndsh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'final_loc': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'final_palm_orientation': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'final_relative_orientation': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'final_secondary_loc': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'final_subhndsh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'idgloss': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'inWeb': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'initial_palm_orientation': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'initial_relative_orientation': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'initial_secondary_loc': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'inittext': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'}),
            'isNew': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'language': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['dictionary.Language']", 'symmetrical': 'False'}),
            'locprim': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'locsecond': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'morph': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'sedefinetf': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'segloss': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'sense': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sn': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'subhndsh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'})
        },
        u'dictionary.keyword': {
            'Meta': {'ordering': "['text']", 'object_name': 'Keyword'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'dictionary.language': {
            'Meta': {'ordering': "['name']", 'object_name': 'Language'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'dictionary.translation': {
            'Meta': {'ordering': "['gloss', 'index']", 'object_name': 'Translation'},
            'gloss': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Gloss']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'translation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Keyword']"})
        },
        u'feedback.generalfeedback': {
            'Meta': {'ordering': "['-date']", 'object_name': 'GeneralFeedback'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'unread'", 'max_length': '10'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'video': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'})
        },
        u'feedback.interpreterfeedback': {
            'Meta': {'object_name': 'InterpreterFeedback'},
            'comment': ('django.db.models.fields.TextField', [], {}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'gloss': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Gloss']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'unread'", 'max_length': '10'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'feedback.missingsignfeedback': {
            'Meta': {'ordering': "['-date']", 'object_name': 'MissingSignFeedback'},
            'althandshape': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'direction': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'handbodycontact': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'handform': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'handinteraction': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'handshape': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'meaning': ('django.db.models.fields.TextField', [], {}),
            'movementtype': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'relativelocation': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'repetition': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'smallmovement': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'unread'", 'max_length': '10'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'video': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'})
        },
        u'feedback.signfeedback': {
            'Meta': {'ordering': "['-date']", 'object_name': 'SignFeedback'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'correct': ('django.db.models.fields.IntegerField', [], {}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isAuslan': ('django.db.models.fields.IntegerField', [], {}),
            'kwnotbelong': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'like': ('django.db.models.fields.IntegerField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'unread'", 'max_length': '10'}),
            'suggested': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'translation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Translation']"}),
            'use': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'whereused': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }

    complete_apps = ['feedback']