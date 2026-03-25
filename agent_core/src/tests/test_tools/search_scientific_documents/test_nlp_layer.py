from shared.nlp.similarity.cosine import CosineSimilarity
from shared.nlp.vectorizers.tfidf import TFIDFVectorizer


def test_tfidf_and_cosine_are_decoupled_and_operational():
    vectorizer = TFIDFVectorizer()
    corpus = [
        "band gap engineering semiconductor",
        "thermodynamic stability screening",
    ]

    vectorizer.fit(corpus)
    doc_vectors = vectorizer.transform(corpus)
    query_vector = vectorizer.transform(["band gap semiconductor"])[0]

    similarity = CosineSimilarity()
    score0 = similarity.compute(query_vector, doc_vectors[0])
    score1 = similarity.compute(query_vector, doc_vectors[1])

    assert score0 > score1
