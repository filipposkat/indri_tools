import sys
import re
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
class Topic:
    num = None
    title = None
    desc = None
    narr = None

    def __init__(self, num, title, desc, narr):
        self.num = num
        self.title = title
        self.desc = desc
        self.narr = narr


def str_between_strs(s, str1, str2):
    result = re.findall(f'{str1}(.*){str2}', s, re.DOTALL)
    return result[0]


def remove_chars(s, chars):
    for c in chars:
        if c in s:
            s = s.replace(c, '')
    return s


def create_indri_stoplist():
    stoplist = stopwords.words('english')
    indri_stoplist = "<stopper>"
    for stopword in stoplist:
        sw = remove_chars(stopword,'''!()[]{}';:\,<>?/@#$%^&*_~.''')
        indri_stoplist += f'<word>{sw}</word>'
    indri_stoplist += "</stopper>"
    return indri_stoplist


# topics_file = sys.argv[1]
# queries_out_file = sys.argv[2]
# option = int(sys.argv[3])  # 1 = title, 2 = title+desc, 3=title+desc+narr
topics_file = 'topics.trec6'
queries_out_file = 'qout'
option = 3

if (option == 1):
    print('Option 1: title')
else:
    if (option == 2):
        print('Option 2: title+desc')
    else:
        print('Option 3: title+desc+narr')


# Add root tag to trec file in order to parse it as xml
with open(topics_file) as f:
    topic_text = f.read()
f.close()

topic_objs = []

topics = re.findall('<top>(.*?)</top>', topic_text, re.DOTALL)
# Create object for each topic and add it to topic_objs list:
for topic in topics:
    # num = int(topic.find('num').text.strip().replace('Number: ', '', 1))
    # title = topic.find('title').text
    # desc = topic.find('desc').text.replace(' Description: ', '', 1)
    # narr = topic.find('narr').text.replace(' Narrative: ', '', 1)
    num = int(str_between_strs(topic, '<num> Number: ', '<title>').strip())
    title = remove_chars(str_between_strs(topic, '<title> ', '<desc>').strip(), '''!()[]{}';:\,<>?/@#$%^&*_~.''').lower() #using tiple quotes disables escape \
    desc = remove_chars(str_between_strs(topic, '<desc> Description: ', '<narr>').strip().replace('\n', ' '), '''!()[]{}';:\,<>?/@#$%^&*_~.''').lower()
    narr = remove_chars(str_between_strs(topic, '<narr> Narrative: ', '\n').strip().replace('\n', ' '), '''!()[]{}';:\,<>?/@#$%^&*_~.''').lower()
    top = Topic(num, title, desc, narr)
    topic_objs.append(top)


# create indri stoplist from nltk
#stoplist_param = create_indri_stoplist()

lines = []
lines.append('<parameters>')
lines.append('<index>./indices/trec7-8</index>')
lines.append('<rule>method:dirichlet,mu:1000</rule>')
lines.append('<count>1000</count>')
lines.append('<trecFormat>true</trecFormat>')
#lines.append(stoplist_param)

for obj in topic_objs:
    if option == 1:
        # Use only title:
        lines.append(f'<query> <type>indri</type> <number>{obj.num}</number> <text>{obj.title}</text> </query>')
    else:
        if option == 2:
            # Use title+desc:
            lines.append(
                f'<query> <type>indri</type> <number>{obj.num}</number> <text>{obj.title} \n {obj.desc}</text> </query>')
        else:
            # Use title+desc+narr:
            lines.append(
                f'<query> <type>indri</type> <number>{obj.num}</number> <text>{obj.title} \n {obj.desc} \n {obj.narr}</text> </query>')

lines.append('</parameters>')

with open(queries_out_file, 'w') as f:
    for line in lines:
        f.write(line)
        f.write('\n')
f.close()
