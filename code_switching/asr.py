from pathlib import Path

import torch
from transformers import WhisperForConditionalGeneration, WhisperTokenizer, pipeline


def run_asr(path: Path, model_name: str = "openai/whisper-small"):
    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda:0"
    elif torch.backends.mps.is_available():
        device = "mps"

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model_name,
        chunk_length_s=15,
        device=device,
        generate_kwargs={"task": "transcribe"},
    )

    model: WhisperForConditionalGeneration = pipe.model  # type: ignore
    tokenizer: WhisperTokenizer = pipe.tokenizer  # type: ignore
    language_tokens = ["<|en|>", "<|es|>"]
    language_token_ids: List[str] = tokenizer.convert_tokens_to_ids(language_tokens)  # type: ignore
    en_ids = tokenizer.get_decoder_prompt_ids(task="transcribe")
    es_ids = tokenizer.get_decoder_prompt_ids(language="spanish", task="transcribe")
    transcribe_token: int = tokenizer.convert_tokens_to_ids("<|transcribe|>")  # type: ignore

    chunks = pipe.preprocess(str(path), **pipe._preprocess_params)

    result = []
    for chunk in chunks:
        input_features: torch.Tensor = chunk["input_features"].to(device)  # type: ignore
        logits = model(
            input_features,
            decoder_input_ids=torch.full(
                (input_features.shape[0], 1),
                transcribe_token,
                device=device,
            ),
        ).logits.detach()
        en_tokens = model.generate(
            input_features,
            forced_decoder_ids=en_ids,
            repetition_penalty=1.1,
        )

        es_tokens = model.generate(
            input_features,
            forced_decoder_ids=es_ids,
            repetition_penalty=1.1,
        )

        mask = torch.ones(logits.shape[-1], dtype=torch.bool, device=device)
        mask[language_token_ids] = False
        logits[:, :, mask] = -float("inf")

        output_probs = logits.softmax(dim=-1).cpu()

        for input_idx in range(logits.shape[0]):
            r = {
                lang: output_probs[input_idx, 0, token_id].item()
                for token_id, lang in zip(language_token_ids, language_tokens)
            }
            r["en_text"] = tokenizer.batch_decode(en_tokens, skip_special_tokens=False)
            r["es_text"] = tokenizer.batch_decode(es_tokens, skip_special_tokens=False)
            result.append(r)
    return result

    # return pipe(str(path), batch_size=8, return_timestamps=True)


# %%
result = run_asr(
    Path(
        "/Users/logan/Projects/code-switching/data/audio/que-pasa-midwest/que-pasa-midwest_1_1_pulque-en-america.mp3"
    )
)

# Load data
# Split into 30s chunks
# Token-level language ID: https://discuss.huggingface.co/t/language-detection-with-whisper/26003/2
result
