# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Definition.published'
        db.add_column(u'dictionary_definition', 'published',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Definition.published'
        db.delete_column(u'dictionary_definition', 'published')


    models = {
        u'dictionary.definition': {
            'Meta': {'ordering': "['gloss', 'role', 'count']", 'object_name': 'Definition'},
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'gloss': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Gloss']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'text': ('django.db.models.fields.TextField', [], {})
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
        u'dictionary.relation': {
            'Meta': {'ordering': "['source']", 'object_name': 'Relation'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relation_sources'", 'to': u"orm['dictionary.Gloss']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relation_targets'", 'to': u"orm['dictionary.Gloss']"})
        },
        u'dictionary.translation': {
            'Meta': {'ordering': "['gloss', 'index']", 'object_name': 'Translation'},
            'gloss': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Gloss']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'translation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Keyword']"})
        }
    }

    complete_apps = ['dictionary']