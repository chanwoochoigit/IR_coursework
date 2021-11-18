from xml.etree import cElementTree as ET
import re
from nltk.stem import PorterStemmer
import itertools
import operator
import re
from math import log10
import time

class XMLProcesser():

    def get_xml_root(self, path):
        with open(path) as f:
            xmlstr = f.read()

        return ET.fromstring(xmlstr)

    def extract_text_from_path(self, path):
        root = self.get_xml_root(path)
        doc_dict = {}
        for page in root:
            doc_number = page.find('DOCNO').text
            text = page.find('HEADLINE').text.replace('\n',' ').replace('\t',' ').replace('  ', ' ') + \
                   page.find('TEXT').text.replace('\n',' ').replace('\t',' ').replace('  ', ' ')
            doc_dict[doc_number] = text

        return doc_dict

class Preprocessor():

    def unique_from_array(self, items):
        items_1d = list(itertools.chain.from_iterable(items))
        unique_dump = []
        [unique_dump.append(x) for x in items_1d if x not in unique_dump]

        return unique_dump

    def count_frequencies(self, data, unique_words):
        word_names = []
        word_counts = []
        check_count = 0

        for word in unique_words:
            count = 0
            word_names.append(word)
            for word_to_compare in data:
                if len(word_to_compare) == len(word):
                    if word_to_compare == word:
                        count += 1
            word_counts.append(count)
            check_count += 1
            if check_count % 100 == 1:
                print('counting word number ... {}/{}'.format(check_count, len(unique_words)))
        word_freq = {"Word": word_names, "Count": word_counts}

    def trim_text(self, text):
        text_str = text.replace('\n', ' ').replace('  ',' ')  # replace \n with a space, and if that creates a double space, replace it with a single space
        return text_str.lower()

    def tokenise(self, text_str):
        words = re.split('\W+', text_str)
        words_lower = []
        for word in words:
            words_lower.append(word.lower())
        return words_lower

    def remove_stopwords(self, words):
        with open('stopwords.txt') as f:
            stop_words = f.read().split('\n')
        words_dup_nostop = []
        [words_dup_nostop.append(x) for x in words if x not in stop_words]
        return words_dup_nostop

    def stem_data(self, words_preprocessed):
        ps = PorterStemmer()
        words_stemmed = []
        for word in words_preprocessed:
            words_stemmed.append(ps.stem(word))
        return words_stemmed

    def preprocess(self, data_chunk):
        #trim
        text_str = self.trim_text(data_chunk)

        #tokenise
        words_dup = self.tokenise(text_str)

        #remove stop words
        words_dup_nostop = self.remove_stopwords(words_dup)

        # """normalisation"""
        words_stemmed = self.stem_data(words_dup_nostop)

        return words_stemmed

    def preprocess_many(self, data_chunk_loads):
        processed_chunks_loads = []
        for data in data_chunk_loads:
            processed_chunks_loads.append(self.preprocess(data))

        return processed_chunks_loads

class Indexer():

    #create index for a single term
    def create_idx_single(self, word_to_find, doc_dict):
        #desired style:
        #term: freq
        #   docID: pos1, pos2, ...
        #[term, freq, docID, [positions]]
        idx_single = {}
        frequency = 0
        for docID in list(doc_dict.keys()):
            positions = []
            for j, word in enumerate(doc_dict[docID]):
                if word_to_find == word:
                    positions.append(j+1)
                    frequency += 1
            if len(positions) != 0:
                idx_single[docID] = positions
        idx_single['freq'] = frequency

        return self.convert_dict_to_text(word_to_find, idx_single)

    def convert_dict_to_text(self, word, idx_single):
        # term: freq
        index_text = word + ': ' + str(idx_single['freq']) + '\n'

        #   docID: pos1, pos2, ...
        for docID in idx_single.keys():
            if docID != 'freq':
                index_text += '\t' + str(docID) +': ' + ', '.join(str(x) for x in idx_single[docID]) +'\n'
        return index_text


    def create_idx(self, word_loads, doc_dict):
        index_text = ''
        counter = 0
        for word in word_loads:
            if counter % 10 == 0:
                print("indexing word no.{}/{}".format(counter, len(word_loads)))
            if word == '':
                continue
            index_text += self.create_idx_single(word, doc_dict) +'\n'
            counter += 1

        return index_text

class Querytaker():

    def __init__(self):
        self.index = self.load_index()
        self.documents = self.get_all_documents()
        self.N = len(self.documents)

    def get_all_documents(self):
        documents = []
        index_dict = self.index
        for word in index_dict:
            [documents.append(d) for d in index_dict[word] if d not in documents]

        return documents

    def get_all_relevant_documents(self, query):
        OR_query = ' OR '.join(query)
        relevant_documents_all = self.bool_search(OR_query)
        return relevant_documents_all

    # load index text! file into memory, returns the index dictionary
    def load_index(self):
        with open('index.txt') as f:
            text = f.read()
        index_dict = {}
        for item in text.split('\n\n')[:-1]:
            term_with_freq = item.split('\n')[0].replace(':', '').split(' ')
            term = term_with_freq[0]
            #freq = term_with_freq[1]
            docID_pos = item.split('\n\t')[1:]
            document_dict = {}
            for line in docID_pos:
                docID = line.split(': ')[0]
                positions_str = line.split(': ')[1].split(',')
                positions = list(map(int, positions_str))  # map positions to int from string
                document_dict[int(docID)] = positions
                index_dict[term] = document_dict
        return index_dict

    #takes A single word or A phrase and returns docIDs where matching words/phrases exist
    def basic_search(self, query_str):
        pp = Preprocessor()
        if "\"" in query_str: #if it is phrase
            phrase = query_str.replace("\"", '')
            docIDs_found = self.phrase_search(phrase)
        else:
            try:
                processed = pp.preprocess(query_str)[0]
                docIDs_found = list(self.index[processed].keys())
            except:
                docIDs_found = []

        return set(docIDs_found)

    #takes a query with booleans
    def bool_search(self, query):
        #term11 AND term12
        is_phrase = False
        query_words = []
        for token in query.split(' '):
            if "\"" in token:       # if phrase
                if is_phrase == False:
                    is_phrase = True
                    query_words.append(token)
                else:
                    query_words[-1] += ' ' + token #add the token to the last item in the list of phrases
                    is_phrase = False
            else:
                query_words.append(token)

        operator = ''           #current operator
        current_pos = 0    #current word position in query
        search_result = set()
        raw_result = set()
        is_first_word = True
        is_op_not = False

        while current_pos < len(query_words):

            current_word = query_words[current_pos]

            if current_word == 'AND':
                operator = 'AND'
            elif current_word == 'OR':
                operator = 'OR'
            elif current_word == 'NOT':
                is_op_not = True
            else:   #current word is not an operator

                if is_op_not:
                    raw_result = set(self.documents).difference(self.basic_search(current_word))
                    is_op_not = False
                else:   #operator AND or OR
                    raw_result = self.basic_search(current_word)

                if is_first_word:

                    search_result = raw_result    #if current word is the first word then simply plug in the result
                    is_first_word = False

                if operator == 'AND':
                    search_result = set.intersection(search_result, raw_result)
                    operator = ''

                if operator == 'OR':
                    search_result = set.union(search_result, raw_result)
                    operator = ''

            current_pos += 1

        return sorted(search_result)

    #works as a "helper" function to boolean search, as what it basically does is parsing phrases and doing a boolean search
    def phrase_search(self, query_phrase):
        # "term21 term22"
        words_in_phrase = query_phrase.split(' ')
        adjusted_query = ' AND '.join(words_in_phrase)
        pp = Preprocessor()
        AND_results = self.bool_search(adjusted_query)   #docIDs
        phs_result = []
        for docID in AND_results:
            dict = {}
            for i, word in enumerate(words_in_phrase):
                word = pp.preprocess(word)[0]
                dict[i] = [pos-i for pos in self.index[word][docID]]    #modify all word positions to be the same
            is_result_not_none = set.intersection(*(set(values) for values in dict.values()))
            if is_result_not_none:
                phs_result.append(docID)

        return phs_result

    def proximity_search(self, query):
        # #15(term1, term2)
        matching = re.match(r'#(\d+)\((.*?),(.*?)\)', query)
        search_range = int(matching.group(1))
        w1 = matching.group(2).strip()
        w2 = matching.group(3).strip()

        adjusted_query = w1 + ' AND ' + w2
        AND_results = self.bool_search(adjusted_query)
        pp = Preprocessor()
        w1_preprocessed = pp.preprocess(w1)[0]
        w2_preprocessed = pp.preprocess(w2)[0]

        prox_result = []

        for docID in AND_results:
            legit_search = False
            doc_positions_1 = self.index[w1_preprocessed][docID]
            doc_positions_2 = self.index[w2_preprocessed][docID]
            for pos_1 in doc_positions_1:
                for pos_2 in doc_positions_2:
                    if abs(pos_1 - pos_2) <= search_range: # any AND search results within search range would be accepted
                        legit_search = True

            if legit_search:
                prox_result.append(docID)

        return prox_result

    def get_tf(self, term, document):
        try:
            tf = len(self.index[term][document])
        except: #if the term doesn't exist in the document
            tf = 0
        return tf

    def get_df(self, term):
        try:
            df = len(self.index[term])
        except: #if the term doesn't exist in any document
            df = 0
        return df

    def calc_weight(self, term, document):
        tf = self.get_tf(term, document)

        if tf > 0:
            df = self.get_df(term)
            idf = log10(self.N / df)
            weight = (1 + log10(tf)) * idf
        else:
            weight = 0

        return weight

    def calc_score(self, query, document):
        score = 0
        for term in query:
            score += self.calc_weight(term, document)

        return score

    def take_query_bool(self):
        with open('CW1collection/queries.boolean.txt') as f:
            query = f.read()

        for q in query.split('\n'):
            try:
                qID, qqq = q.split(' ', maxsplit=1) #split 1 query to ['1', 'query']
                qqq = qqq.strip()
            except:  # when an empty '' is in the query document just skip
                continue

            if '#' in qqq:
                search_result = self.proximity_search(qqq)
            else:
                search_result = self.bool_search(qqq) #phrase search is included in boolean search

            with open('results.boolean.txt', 'a') as f:
                for docID in search_result:
                    f.write(str(qID)+ ','+str(docID)+'\n')

    def take_query_ranked(self):
        with open('CW1collection/queries.ranked.txt') as f:
            query = f.read()
        pp = Preprocessor()
        for q in query.split('\n'):
            try:
                qID, qqq = q.split(' ', maxsplit=1) #split 1 query to ['1', 'query']
                qqq = pp.preprocess(qqq.strip())
                rel_documents_all = self.get_all_relevant_documents(qqq)
            except: # when an empty '' is in the query document just skip
                continue

            score_dict = {}
            for docID in rel_documents_all:
                score = self.calc_score(qqq, docID)
                score_dict[docID] = score
            score_doc_sorted = sorted(score_dict.items(), key=operator.itemgetter(1))[::-1]
            with open('results.ranked.txt', 'a') as f:
                for i, doc_score in enumerate(score_doc_sorted):
                    if i < 150:
                        f.write(str(qID)+','+str(doc_score[0])+','+str(round(doc_score[1], 4))+'\n')

def run_index_creator():
    xml_data_path = 'CW1collection/trec.5000.xml'
    # xml_data_path = 'collections/trec.sample.xml'
    xmlp = XMLProcesser()
    doc_dict = xmlp.extract_text_from_path(xml_data_path) #create a {doc_number: text} dictinoary from xml file
    pp = Preprocessor()

    for key in list(doc_dict.keys()):
        processed_text = pp.preprocess(doc_dict[key])
        doc_dict[key] = processed_text #update "raw" texts in doc_dict with processed texts

    unique_words = pp.unique_from_array(doc_dict.values())

    idxer = Indexer()
    created_index = idxer.create_idx(unique_words, doc_dict)

    with open('index.txt', 'w') as f:
        f.write(created_index)
        f.write('\n')

run_index_creator()

# start_time = time.time()
# qt = Querytaker()
# index_loaded_time = time.time()
#
# qt.take_query_bool()
# bool_search_time = time.time()
#
# qt.take_query_ranked()
# ranked_search_time = time.time()
#
# print("%s seconds for loading index!" % (index_loaded_time - start_time))
# print("%s seconds for boolean search!" % (bool_search_time - index_loaded_time))
# print("%s seconds for ranked search!" % (ranked_search_time - bool_search_time))

