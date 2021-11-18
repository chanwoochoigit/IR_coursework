import operator

from preprocess import Preprocessor
import re
from math import log10
import time

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
        df = self.get_df(term)
        idf = log10(self.N/df)

        if tf > 0:
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
        with open('queries_boolean.txt') as f:
            query = f.read()

        for q in query.split('\n'):
            qID, qqq = q.split(' ', maxsplit=1) #split 1 query to ['1', 'query']
            qqq = qqq.strip()

            if '#' in qqq:
                search_result = self.proximity_search(qqq)
            else:
                search_result = self.bool_search(qqq) #phrase search is included in boolean search

            with open('results.boolean.txt', 'a') as f:
                for docID in search_result:
                    f.write(str(qID)+ ','+str(docID)+'\n')

    def take_query_ranked(self):
        with open('queries_ranked.txt') as f:
            query = f.read()
        pp = Preprocessor()
        for q in query.split('\n'):
            qID, qqq = q.split(' ', maxsplit=1) #split 1 query to ['1', 'query']
            qqq = pp.preprocess(qqq.strip())
            rel_documents_all = self.get_all_relevant_documents(qqq)

            score_dict = {}
            for docID in rel_documents_all:
                score = self.calc_score(qqq, docID)
                score_dict[docID] = score
            score_doc_sorted = sorted(score_dict.items(), key=operator.itemgetter(1))[::-1]
            with open('results.ranked.txt', 'a') as f:
                for i, doc_score in enumerate(score_doc_sorted):
                    if i < 150:
                        f.write(str(qID)+','+str(doc_score[0])+','+str(round(doc_score[1], 4))+'\n')


if __name__ == '__main__':
    start_time = time.time()
    tester = Querytaker()
    index_loaded_time = time.time()
    tester.take_query_bool()
    bool_search_time = time.time()
    tester.take_query_ranked()
    ranked_search_time = time.time()
    print("%s seconds for loading index!" % (index_loaded_time - start_time))
    print("%s seconds for boolean search!" % (bool_search_time - index_loaded_time))
    print("%s seconds for ranked search!" % (ranked_search_time - bool_search_time))



