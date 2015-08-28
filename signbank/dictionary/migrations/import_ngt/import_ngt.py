import json
import value_translations as vt

def translate(table,query):

	try:
		return str(dict([(y.lower(),x) for x,y in table])[query.lower().strip()]);
	except KeyError:
		return '0';

class Sign():

	def __init__(self,string):
		
		column = string.split('\t');

		self.keywords = [kw.strip() for kw in column[1].split(',')];

		self.fields = {};

		self.fields['annotation_idgloss'] = column[6];
		self.fields['idgloss'] = column[6];
		self.fields['annotation_idgloss_en'] = column[7];
		
		#Create an extra keyword from the gloss
		extra_keyword = self.fields['idgloss'].replace('-',' ').replace('*','').lower();

		if len(extra_keyword) > 1 and extra_keyword[-2] == ' ':
			extra_keyword = extra_keyword[:-2]


		self.keywords.append(extra_keyword);

		self.fields['handedness'] = translate(vt.handednessChoices,column[10]);
		self.fields['domhndsh'] = translate(vt.handshapeChoices,column[11]);
		self.fields['subhndsh'] = translate(vt.handshapeChoices,column[13]);
		self.fields['locprim'] = translate(vt.locationChoices,column[15]);

		self.fields['relatArtic'] = translate(vt.locationChoices,column[14]);
		self.fields['absOriPalm'] = translate(vt.absOriPalmChoices,column[22]);
		self.fields['absOriFing'] = translate(vt.absOriFingChoices,column[23]);
		self.fields['relOriMov'] = translate(vt.relOriMovChoices,column[24]);
		self.fields['relOriLoc'] = translate(vt.relOriLocChoices,column[25]);

		self.fields['handCh'] = translate(vt.handChChoices,column[12]);

		self.fields['repeat'] = bool(column[20]);
		self.fields['altern'] = bool(column[21]);

		self.fields['movSh'] = translate(vt.movShapeChoices,column[18]);
		self.fields['movDir'] = translate(vt.movDirChoices,column[17]);
		self.fields['movMan'] = translate(vt.movManChoices,column[19]);

		self.fields['contType'] = translate(vt.contTypeChoices,column[16]);
		self.fields['phonOth'] = column[26];

		self.fields['mouthG'] = column[27];
		self.fields['phonetVar'] = column[29];

		self.fields['iconImg'] = column[32];
		self.fields['namEnt'] = translate(vt.namedEntChoices,column[33]);

#=======

#Interpret the input
filepath = '/home/wessel/signbank/signbank/dictionary/migrations/import_ngt/ngt_lexicon_final.csv';

signs = [];
keywords = [];

for n, line in enumerate(open(filepath)):

	#Skip the first line
	if n == 0:
		continue;

	s = Sign(line);
	
	signs.append(s);
	
	for kw in s.keywords:
		if len(kw) != 0 and kw not in keywords:
			keywords.append(kw);

#Convert the data
result = [];

#Add all keywords
for n, keyword in enumerate(keywords):
	result.append({'pk':n,'model':'dictionary.keyword','fields':{'text':keyword}});

translation_n = 0;

#Add all glosses
for n, sign in enumerate(signs):

	result.append({'pk':n,'model':'dictionary.gloss',
	'fields':sign.fields});

	#Add all translations for each gloss
	for kw in sign.keywords:

		try:
			keyword_n = keywords.index(kw);
		except ValueError:
			continue;
	
		result.append({'pk':translation_n,'model':'dictionary.translation',
                'fields':{'index':1, 'gloss':n,'translation':keyword_n}});
		translation_n += 1;

print(json.dumps(result,indent=4));
