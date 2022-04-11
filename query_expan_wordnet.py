import copy
import sys
import re
import xml.etree.ElementTree as ET
import nltk

nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('stopwords')
from nltk.corpus import wordnet
from nltk.corpus import stopwords

MAX_SYNONYMS = 1
MIN_LENGTH_FOR_EXPAN = 5
NOUNS_ONLY = False
# original term has weight = 1
SYNONYM_WEIGHT = 0.1


class Query:
    expanded = False
    original = None
    expansion = None
    original_terms = []
    expansion_weights = []
    expansion_terms = []
    number = None
    original_synonyms = {}
    expansion_synonyms = {}

    def __init__(self, original_q, expanded):
        self.expanded = expanded
        self.original = original_q.lower().strip()
        self.expansion = None
        self.expansion_weights = []
        self.expansion_terms = []
        self.number = None
        self.original_synonyms = {}
        self.expansion_synonyms = {}
        tmp = []
        for el in original_q.split(' '):
            if not el == '\n':
                # save the lower case version of terms
                tmp.append(el.lower())
        self.original_terms = tmp


def remove_chars(s, chars):
    for c in chars:
        if c in s:
            s = s.replace(c, '')
    return s


def str_between_strs(s, str1, str2):
    result = re.findall(f'{str1}(.*){str2}', s, re.DOTALL)
    return result[0]


def parse_exp_queries(src):
    query_obj_lst = []
    query_lst = re.findall('# expanded:(.*?)\) \)', src, re.DOTALL)
    for i in range(len(query_lst)):
        query_lst[i] = query_lst[i] + "  ) <STOP>"
        # print(el)
        # print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
    for el in query_lst:
        # isolate original query
        orig = re.findall('#combine\( (.*?) \)', el, re.DOTALL)[0].strip()

        # isolate expansion
        tmp = re.findall('#weight\((.*)<STOP>', el, re.DOTALL)[0]
        expan = re.findall('#weight\( (.*?) \)', tmp, re.DOTALL)[0]

        # Isolate lowercase terms and weights from expansion
        term_list = [t.lower() for t in re.findall(' "(.*?)" ', expan)]
        weight_list = [re.findall(f'(.*?)"{term_list[0]}"', expan)[0]]

        for i in range(len(term_list) - 1):
            weight_list.extend(re.findall(f'"{term_list[i]}"(.*?)"{term_list[i + 1]}"', expan))

        # create appropriate object
        q = Query(orig, True)
        q.expansion = expan
        q.expansion_weights = weight_list
        q.expansion_terms = term_list
        query_obj_lst.append(q)
    # print(f"Total number of queries in  file: {src.count('# query:')}")
    # print(f"Total number of expanded queries in file: {src.count('# expanded:')}")
    return query_obj_lst.copy()


def wordnet_expan(obj_lst: [Query], max_syns=1, min_len=4, nouns_only=False):
    # iterate all queries:
    for on in range(len(obj_lst)):
        obj_lst[on].expansion_synonyms = {}
        tmp_orig_syns = {}
        # iterate original terms:
        for n in range(len(obj_lst[on].original_terms)):
            ter = obj_lst[on].original_terms[n]
            # exclude small words from expansion:
            if len(ter) >= min_len:
                # The following is a list of lists of same meaning synonyms
                if nouns_only:
                    synons = [synset.lemma_names() for synset in wordnet.synsets(ter, pos=wordnet.NOUN)]
                else:
                    synons = [synset.lemma_names() for synset in wordnet.synsets(ter)]
                # if synonyms exist:
                if synons:
                    tmp_orig_syns[ter] = []
                    count = 0
                    for similar_synons in synons:
                        for sy in similar_synons:
                            s = remove_chars(sy, '''!()[]{}';:\,<>?/@#$%^&*_~.''').lower()
                            if s not in obj_lst[on].original_terms and s not in tmp_orig_syns[ter]:
                                tmp_orig_syns[ter].append(s)
                                count += 1
                                # go to next set of similar synons for the word:
                                break
                        if count >= max_syns:
                            break
                    obj_lst[on].original_synonyms[ter] = tmp_orig_syns[ter]

        if obj_lst[on].expanded:
            obj_lst[on].expansion_synonyms = {}
            tmp_exp_syns = {}
            # iterate fb_expansion terms:
            for n in range(len(obj_lst[on].expansion_terms)):
                ter = obj_lst[on].expansion_terms[n]
                # exclude small words from expansion:
                if len(ter) >= min_len:
                    # The following is a list of lists of same meaning synonyms
                    if nouns_only:
                        synons = [synset.lemma_names() for synset in wordnet.synsets(ter, pos=wordnet.NOUN)]
                    else:
                        synons = [synset.lemma_names() for synset in wordnet.synsets(ter)]

                    # if synonyms exist:
                    if synons:
                        tmp_exp_syns[ter] = []
                        count = 0
                        for similar_synons in synons:
                            for sy in similar_synons:
                                s = remove_chars(sy, '''!()[]{}';:\,<>?/@#$%^&*_~.''').lower()
                                if s not in obj_lst[on].expansion_terms and s not in tmp_exp_syns[ter]:
                                    tmp_exp_syns[ter].append(s)
                                    count += 1
                                    # go to next set of similar synons for the word:
                                    break
                            if count >= max_syns:
                                break
                        obj_lst[on].expansion_synonyms[ter] = tmp_exp_syns[ter]


def create_indri_stoplist():
    stoplist = stopwords.words('english')
    indri_stoplist = "<stopper>"
    for stopword in stoplist:
        sw = remove_chars(stopword, '''!()[]{}';:\,<>?/@#$%^&*_~.''')
        indri_stoplist += f'<word>{sw}</word>'
    indri_stoplist += "</stopper>"
    return indri_stoplist


source_file = 'results_Bi+Q.trec'
original_queries_file = 'queries_Bi'
queries_out_file = 'queries_Bii'
if len(sys.argv) == 4:
    source_file = sys.argv[1]
    original_queries_file = sys.argv[2]
    queries_out_file = sys.argv[3]

# get and parse expanded queries
with open(source_file) as f:
    source = f.read()
f.close()

query_obj_list = parse_exp_queries(source)

# get and parse original queries:
with open(original_queries_file) as f:
    original_queries = f.read()
f.close()
# parse file:
root = ET.fromstring(original_queries)
# get some important parameters:
index = root.find('index').text
fb_orig_weight = float(root.find('fbOrigWeight').text)
# get all queries:
orig_query_lst = root.findall('query')
orig_query_obj_lst = []
for q in orig_query_lst:
    num = int(q.find('number').text)
    text = q.find('text').text.strip()
    obj = Query(text, False)
    obj.number = num
    orig_query_obj_lst.append(obj)

# filling expanded queries with correct numbers
query_nums_in_both_lists = []
for i in range(len(query_obj_list)):
    for j in range(len(orig_query_obj_lst)):
        # if query is the same
        if query_obj_list[i].original == orig_query_obj_lst[j].original.lower().strip():
            num = orig_query_obj_lst[j].number
            query_obj_list[i].number = num
            query_nums_in_both_lists.append(num)

for orig in orig_query_obj_lst:
    if orig.number not in query_nums_in_both_lists:
        query_obj_list.append(orig)

# find synonyms for each object:
wordnet_expan(query_obj_list, MAX_SYNONYMS, MIN_LENGTH_FOR_EXPAN, NOUNS_ONLY)

# create indri stoplist from nltk
stoplist_param = create_indri_stoplist()
# create new queries file:
lines = []
lines.append('<parameters>')
lines.append(f'<index>{index}</index>')
lines.append('<rule>method:dirichlet,mu:1000</rule>')
lines.append('<count>1000</count>')
lines.append('<trecFormat>true</trecFormat>')
# lines.append(stoplist_param)

for o in query_obj_list:
    # original = f"#combine({o.original} "
    # original_synonyms = ""
    # for syns in o.original_synonyms.values():
    #     # syns is a list of synonyms for each term
    #     if syns:
    #         for syn in syns:
    #             original_synonyms += syn.replace('-', '').replace('_', '')
    #             original_synonyms += " "
    # original += f'{original_synonyms} )'

    original = f"#combine("
    # iterate original terms:
    for i in range(len(o.original_terms)):
        term = o.original_terms[i]
        syns_part = ""
        # check if term exists in dictionary of synonyms
        if term in o.original_synonyms:
            # check if it has any synonyms
            if o.original_synonyms[term]:
                # get synonyms for each extra term
                for syn in o.original_synonyms[term]:
                    # create the synonyms part of the string
                    syns_part += f'{SYNONYM_WEIGHT} "{syn}" '
                    # create the whole expansion part of the string containing both expansion terms and its synonyms
                    original += f'#wsyn(1.0 {term} {syns_part})' + ' '
        else:
            # no synonyms
            # create the whole expansion part of the string containing both expansion terms
            original += f'"{term}" '
    original += ")"

    expansion = "#weight( "
    # iterate expansion terms:
    for i in range(len(o.expansion_terms)):
        term = o.expansion_terms[i]
        weight = o.expansion_weights[i]
        syns_part = ""
        # check if term exists in dictionary of synonyms
        if term in o.expansion_synonyms:
            # check if it has any synonyms
            if o.expansion_synonyms[term]:
                # get synonyms for each extra term
                for syn in o.expansion_synonyms[term]:
                    # create the synonyms part of the string
                    syns_part += f'{SYNONYM_WEIGHT} "{syn}" '
                    # create the whole expansion part of the string containing both expansion terms and its synonyms
                    expansion += weight + f'#wsyn(1.0 "{term}" {syns_part})' + ' '
        else:
            # no synonyms
            # create the whole expansion part of the string containing both expansion terms
            expansion += weight + f'"{term}"' + ' '
    expansion += ")"
    text = f'#weight( {fb_orig_weight} {original} {1 - fb_orig_weight} {expansion} )'
    lines.append(f'<query> <type>indri</type> <number>{o.number}</number> <text>{text}</text> </query>')
lines.append('</parameters>')

with open(queries_out_file, 'w') as f:
    for line in lines:
        f.write(line)
        f.write('\n')
f.close()

# '#weight( {fb_orig_weight} #combine( {original} {synonyms} ) {1-fb_orig_weight} #weight({expansion_weight} #combine({expansion_term} {expansion_synonyms}) ) )'
