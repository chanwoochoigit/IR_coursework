from preprocess import Preprocessor
from process_xml import XMLProcesser

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
        # print(index_text)
        return index_text

xml_data_path = 'collections/trec.sample.xml'
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


