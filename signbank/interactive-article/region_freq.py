from signbank.dictionary.models import GlossFrequency
from collections import Counter

c = Counter()

for n, glossfreq in enumerate(GlossFrequency.objects.all()):

    c[glossfreq.speaker.location] += 1

    if n%1000 == 0:
        print(c.most_common())