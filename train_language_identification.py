import json
import os
from pathlib import Path

import numpy as np

# huggingface packages
from datasets import load_dataset, load_metric
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)

set_seed(1234)
data_dir = Path(
    os.getenv(
        "DATA_DIR", Path(__file__).parent / "data" / "text" / "language_identification"
    )
)
output_dir = Path(os.getenv("OUTPUT_DIR", Path(__file__).parent / "output"))
if not output_dir.exists():
    output_dir.mkdir(parents=True)
checkpoint_dir = output_dir / "checkpoints"
if not checkpoint_dir.exists():
    checkpoint_dir.mkdir(parents=True)

# loading dataset
spaeng = load_dataset(
    "json",
    data_files={
        "train": str(data_dir / "train.json"),
        "test": str(data_dir / "test.json"),
        "dev": str(data_dir / "eval.json"),
    },
)

# tag to int conversion dict
LABELS_LIST = {
    "lang1": 0,
    "lang2": 1,
    "mixed": 2,
    "other": 3,
    "ambiguous": 4,
    "ne": 5,
    "unk": 6,
    "fw": 7,
    "": 8,
}
# ne = name, unk = unknown, fw = dif language
# in lince dataset, fw used for catalan, french, german, italian words

# set tokenizer, data collator, model, and metrics
model_name = "xlm-roberta-large"
tokenizer = AutoTokenizer.from_pretrained(model_name)
data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)
acc_metric = load_metric("accuracy")
prec_metric = load_metric("precision")
reca_metric = load_metric("recall")
f1_metric = load_metric("f1")


def model_init():
    return AutoModelForTokenClassification.from_pretrained(
        model_name, num_labels=len(LABELS_LIST)
    )


# helper function for align_labels(), returns list of labels for an individual item
def tag_to_label(examples, word_ids, i, previous_word_idx):
    label_ids = []
    for word_idx in word_ids:  # Set the special tokens to -100.
        if word_idx is None:
            label_ids.append(-100)
        elif (
            word_idx != previous_word_idx
        ):  # Only label the first token of a given word.
            label_ids.append(
                LABELS_LIST[examples["tags"][i][word_idx]]
            )  # returns int representation of tag as per LABELS_LIST
        else:
            label_ids.append(-100)  # set non-first tokens to -100
        previous_word_idx = word_idx
    return label_ids, previous_word_idx


# helper function for tokenize_and_align_labels(), returns entire list of labels for dataset
def align_labels(examples, tokenized_inputs):
    labels = []
    previous_word_idx = None
    for i in range(len(examples["id"])):  # iterate through each item in dataset split
        word_ids = tokenized_inputs.word_ids(
            batch_index=i
        )  # contains index to link tokens that are part of same word
        label, previous_word_idx = tag_to_label(
            examples, word_ids, i, previous_word_idx
        )
        labels.append(label)
    return labels


# returns tokenized_inputs with labels
def tokenize_and_align_labels(examples):
    tokenized_inputs = tokenizer(examples["tokens"], is_split_into_words=True)
    tokenized_inputs["labels"] = align_labels(examples, tokenized_inputs)
    return tokenized_inputs


tokenized_spaeng = spaeng.map(tokenize_and_align_labels, batched=True)
train_data = tokenized_spaeng["train"]
eval_data = tokenized_spaeng["dev"]

# subsets of spaeng to test trainer, when needed
baby_spaeng_train = tokenized_spaeng["train"].select(range(20))
baby_spaeng_eval = tokenized_spaeng["dev"].select(range(20))
# train_data = baby_spaeng_train
# eval_data = baby_spaeng_train

# helper functon for compute_metrics(), handles compute() arguments because i don't know a better way to do it
def metrics_helper(MET_LIST, i, j, true_predictions, true_labels):
    if j == 0:
        MET_LIST[j]["calc"].append(
            MET_LIST[j]["metric"].compute(
                predictions=true_predictions[i], references=true_labels[i]
            )[MET_LIST[j]["key"]]
        )
    elif j > 1:
        MET_LIST[j]["calc"].append(
            MET_LIST[j]["metric"].compute(
                predictions=true_predictions[i],
                references=true_labels[i],
                average="weighted",
                zero_division=0,
            )[MET_LIST[j]["key"]]
        )
    elif j > 0:
        MET_LIST[j]["calc"].append(
            MET_LIST[j]["metric"].compute(
                predictions=true_predictions[i],
                references=true_labels[i],
                average="weighted",
            )[MET_LIST[j]["key"]]
        )


def compute_metrics(eval_pred):

    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    results = {}
    MET_LIST = [
        {"metric": acc_metric, "calc": [], "key": "accuracy"},
        {"metric": f1_metric, "calc": [], "key": "f1"},
        {"metric": prec_metric, "calc": [], "key": "precision"},
        {"metric": reca_metric, "calc": [], "key": "recall"},
    ]

    true_predictions = [
        [p for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    true_labels = [
        [l for (_, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]

    for i in range(len(true_predictions)):
        for j in range(len(MET_LIST)):
            metrics_helper(MET_LIST, i, j, true_predictions, true_labels)

    for i in range(len(MET_LIST)):
        results[MET_LIST[i]["key"]] = np.mean(MET_LIST[i]["calc"])
    return results


training_args = TrainingArguments(
    num_train_epochs=20,
    optim="adamw_torch",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    output_dir=str(checkpoint_dir),
    evaluation_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=5,
    # auto_find_batch_size=True,
    per_device_train_batch_size=96,
    per_device_eval_batch_size=96,
    remove_unused_columns=True,
)

trainer = Trainer(
    model_init=model_init,
    args=training_args,
    train_dataset=train_data,
    eval_dataset=eval_data,
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
    callbacks=[
        EarlyStoppingCallback(early_stopping_patience=3, early_stopping_threshold=1e-4),
    ],
)


def objective(metrics: dict):
    return metrics["eval_loss"]


def hp_space(trial) -> dict:
    return {
        "learning_rate": trial.suggest_float("learning_rate", 1e-6, 1e-3, log=True),
        "weight_decay": trial.suggest_float("weight_decay", 1e-7, 1e-4, log=True),
        "seed": trial.suggest_int("seed", 1, 3),
    }


result = trainer.hyperparameter_search(
    hp_space=hp_space,
    n_trials=20,
    compute_objective=objective,
    direction="minimize",
)
with (output_dir / "best-model.json").open("w") as f:
    json.dump(result, f)
