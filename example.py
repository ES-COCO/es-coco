from transformers import BatchEncoding, GPT2TokenizerFast

sentences = ["This is an example.", "Fuzzy green cats sleep soundly."]
responses = whatever_you_have_here(sentences)

tokenizer: GPT2TokenizerFast = GPT2TokenizerFast.from_pretrained("gpt2")
encodings: BatchEncoding = tokenizer(sentences)
output = []
for i, (sentence, (tokens, surprisals)) in enumerate(zip(sentences, responses)):
    # Make sure huggingface gave us the same number of tokens as OpenAI
    word_ids = encodings.word_ids(i)[1:]
    assert len(tokens) == len(word_ids)

    sentence_surprisal = sum(surprisals)
    token_by_token = []
    for token, surprisal, word_id in zip(tokens, surprisals, word_ids):
        item = [token, surprisal, word_id]
        token_by_token.append(item)
        print(token, word_id)
    sentence_level = [sentence, sentence_surprisal, token_by_token]
    output.append(sentence_level)
