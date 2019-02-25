import numpy as np
import pickle
import keras
import os


class Chars2Vec:

    def __init__(self, emb_dim, char_to_ix):
        '''
        Creates chars2vec model.

        :param emb_dim: int, dimension of embeddings.
        :param char_to_ix: dict, keys are characters, values are sequence numbers of characters.
        '''

        if not isinstance(emb_dim, int) or emb_dim < 1:
            raise TypeError("parameter 'emb_dim' must be a positive integer")

        if not isinstance(char_to_ix, dict):
            raise TypeError("parameter 'char_to_ix' must be a dictionary")

        self.char_to_ix = char_to_ix
        self.ix_to_char = {char_to_ix[ch]: ch for ch in char_to_ix}
        self.vocab_size = len(self.char_to_ix)
        self.dim = emb_dim

        lstm_input = keras.layers.Input(shape=(None, self.vocab_size))

        x = keras.layers.LSTM(emb_dim, return_sequences=True)(lstm_input)
        x = keras.layers.LSTM(emb_dim)(x)

        self.embedding_model = keras.models.Model(inputs=[lstm_input], outputs=x)

        model_input_1 = keras.layers.Input(shape=(None, self.vocab_size))
        model_input_2 = keras.layers.Input(shape=(None, self.vocab_size))

        embedding_1 = self.embedding_model(model_input_1)
        embedding_2 = self.embedding_model(model_input_2)
        x = keras.layers.Subtract()([embedding_1, embedding_2])
        x = keras.layers.Dot(1)([x, x])
        model_output = keras.layers.Dense(1, activation='sigmoid')(x)

        self.model = keras.models.Model(inputs=[model_input_1, model_input_2], outputs=model_output)
        self.model.compile(optimizer='adam', loss='mae')

    def fit(self, word_pairs, targets,
            max_epochs, patience, validation_split, batch_size):
        '''
        Fits model.

        :param word_pairs: list or numpy.ndarray of word pairs.
        :param targets: list or numpy.ndarray of targets.
        :param max_epochs: parameter 'epochs' of keras model.
        :param patience: parameter 'patience' of callback in keras model.
        :param validation_split: parameter 'validation_split' of keras model.
        :param batch_size: parameter 'batch_size' of keras model.
        '''

        if not isinstance(word_pairs, list) and not isinstance(word_pairs, np.ndarray):
            raise TypeError("parameters 'word_pairs' must be a list or numpy.ndarray")

        if not isinstance(targets, list) and not isinstance(targets, np.ndarray):
            raise TypeError("parameters 'targets' must be a list or numpy.ndarray")

        x_1, x_2 = [], []

        for pair_words in word_pairs:
            emb_list_1 = []
            emb_list_2 = []

            if not isinstance(pair_words[0], str) or not isinstance(pair_words[1], str):
                raise TypeError("word must be a string")

            first_word = pair_words[0].lower()
            second_word = pair_words[1].lower()

            for t in range(len(first_word)):

                if first_word[t] in self.char_to_ix:
                    x = np.zeros(self.vocab_size)
                    x[self.char_to_ix[first_word[t]]] = 1
                    emb_list_1.append(x)

                else:
                    emb_list_1.append(np.zeros(self.vocab_size))

            x_1.append(np.array(emb_list_1))

            for t in range(len(second_word)):

                if second_word[t] in self.char_to_ix:
                    x = np.zeros(self.vocab_size)
                    x[self.char_to_ix[second_word[t]]] = 1
                    emb_list_2.append(x)

                else:
                    emb_list_2.append(np.zeros(self.vocab_size))

            x_2.append(np.array(emb_list_2))

        x_1_pad_seq = keras.preprocessing.sequence.pad_sequences(x_1)
        x_2_pad_seq = keras.preprocessing.sequence.pad_sequences(x_2)

        self.model.fit([x_1_pad_seq, x_2_pad_seq], targets,
                       batch_size=batch_size, epochs=max_epochs,
                       validation_split=validation_split,
                       callbacks=[keras.callbacks.EarlyStopping(monitor='val_loss', patience=patience)])

    def vectorize_words(self, words):
        '''
        Returns embeddings for list of words.

        :param words: list or numpy.ndarray of strings.

        :return word_vectors: numpy.ndarray, word embeddings.
        '''

        if not isinstance(words, list) and not isinstance(words, np.ndarray):
            raise TypeError("parameter 'words' must be a list or numpy.ndarray")

        list_of_embeddings = []

        for current_word in words:

            if not isinstance(current_word, str):
                raise TypeError("word must be a string")

            word = current_word.lower()
            current_embedding = []

            for t in range(len(word)):

                if word[t] in self.char_to_ix:
                    x = np.zeros(self.vocab_size)
                    x[self.char_to_ix[word[t]]] = 1
                    current_embedding.append(x)

                else:
                    current_embedding.append(np.zeros(self.vocab_size))

            list_of_embeddings.append(np.array(current_embedding))

        embeddings_pad_seq = keras.preprocessing.sequence.pad_sequences(list_of_embeddings)
        word_vectors = self.embedding_model.predict([embeddings_pad_seq])

        return word_vectors


def save_model(c2v_model, path_to_model):
    '''
    Saves trained model to directory.

    :param c2v_model: Chars2Vec object, trained model.
    :param path_to_model: str, path to save model.
    '''

    if not os.path.exists(path_to_model):
        os.makedirs(path_to_model)

    c2v_model.embedding_model.save_weights(path_to_model + '/weights.h5')

    with open(path_to_model + '/model.pkl', 'wb') as f:
        pickle.dump([c2v_model.dim, c2v_model.char_to_ix], f)


def load_model(path):
    '''
    Loads trained model.

    :param path: str, if it is 'eng_50', 'eng_100' or 'eng_150' then loads one of default models,
     else loads model from `path`.

    :return c2v_model: Chars2Vec object, trained model.
    '''

    if path in ['eng_50', 'eng_100', 'eng_150']:
        path_to_model = os.path.dirname(os.path.abspath(__file__)) + '/trained_models/' + path

    else:
        path_to_model = path

    with open(path_to_model + '/model.pkl', 'rb') as f:
        structure = pickle.load(f)
        emb_dim, char_to_ix = structure[0], structure[1]

    c2v_model = Chars2Vec(emb_dim, char_to_ix)
    c2v_model.embedding_model.load_weights(path_to_model + '/weights.h5')
    c2v_model.embedding_model.compile(optimizer='adam', loss='mae')

    return c2v_model


def train_model(emb_dim, training_set, model_chars,
                max_epochs=200, patience=10, validation_split=0.05, batch_size=64):
    '''
    Creates and trains chars2vec model using given training data.

    :param emb_dim: int, dimension of embeddings.
    :param training_set: list or numpy.ndarray of strings, each string should be like '*word1* *word2* *target*'
    :param model_chars: list or numpy.ndarray of basic chars in model.
    :param max_epochs: parameter 'epochs' of keras model.
    :param patience: parameter 'patience' of callback in keras model.
    :param validation_split: parameter 'validation_split' of keras model.
    :param batch_size: parameter 'batch_size' of keras model.

    :return c2v_model: Chars2Vec object, trained model.
            char_to_ix: dict, keys are characters, values are sequence numbers of characters.
    '''

    if not isinstance(training_set, list) and not isinstance(training_set, np.ndarray):
        raise TypeError("parameter 'train_data' must be a list or numpy.ndarray")

    if not isinstance(model_chars, list) and not isinstance(model_chars, np.ndarray):
        raise TypeError("parameter 'model_chars' must be a list or numpy.ndarray")

    data = [data_str.lower().strip() for data_str in training_set]
    data = [(data_str.split(' ')[0], data_str.split(' ')[1], data_str.split(' ')[2]) for data_str in data]

    char_to_ix = {ch: i for i, ch in enumerate(model_chars)}
    c2v_model = Chars2Vec(emb_dim, char_to_ix)

    list_of_pairs_samples = [(el[0], el[1]) for el in data]
    targets = [int(el[2]) for el in data]
    c2v_model.fit(list_of_pairs_samples, targets, max_epochs, patience, validation_split, batch_size)

    return c2v_model