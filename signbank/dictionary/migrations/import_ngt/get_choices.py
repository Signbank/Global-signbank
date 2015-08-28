filepath = 'ngt_lexicon_final.csv';
investigate = False

row = 25
choices = [''];

for n, line in enumerate(open(filepath)):

	column = line.split('\t');

	if column[row].strip() not in choices and column[row].strip() != '?':
		choices.append(column[row].strip()	);
#	elif column[25] not in choices and column[25] != '?':
#		choices.append(column[25]);

	if investigate:
		for n,c in enumerate(column):
			print(n,c);
		break;
 
for n,c in enumerate(choices):
	
	print '                    '+str((str(n),c.capitalize()))+','
