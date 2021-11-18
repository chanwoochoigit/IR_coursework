import re
from nltk.stem import PorterStemmer
import itertools

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
        pc1 = 0

        for word in words_preprocessed:
            words_stemmed.append(ps.stem(word))
        # np.save('words_stemmed.npy', words_stemmed)
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
