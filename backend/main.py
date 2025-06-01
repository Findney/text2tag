# BACKEND (FastAPI) - backend/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoTokenizer, AutoModelForTokenClassification, AutoModelForSeq2SeqLM
import torch

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load keyword extraction model
keyword_model_path = "./models/best_keyword_model"
keyword_tokenizer = AutoTokenizer.from_pretrained(keyword_model_path, local_files_only=True)
keyword_model = AutoModelForTokenClassification.from_pretrained(keyword_model_path, local_files_only=True)

# Load tag generation model
tag_model_path = "./models/best_tag_model"
tag_tokenizer = AutoTokenizer.from_pretrained(tag_model_path, local_files_only=True)
tag_model = AutoModelForSeq2SeqLM.from_pretrained(tag_model_path, local_files_only=True)

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
keyword_model.to(device)
tag_model.to(device)

# Parameters
MAX_LENGTH = 256
MAX_INPUT_LENGTH = 256
MAX_TARGET_LENGTH = 100
PREFIX = "generate tags: "

# id2label mapping
id2label = {0: 'O', 1: 'B-KEY', 2: 'I-KEY'}

class TextInput(BaseModel):
    text: str

class TagInput(BaseModel):
    title: str
    content: str

@app.post("/generate_keywords")
def generate_keywords(input: TextInput):
    inputs = keyword_tokenizer(input.text, return_tensors="pt", max_length=MAX_LENGTH, padding="max_length", truncation=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        logits = keyword_model(**inputs).logits

    predictions_ids = torch.argmax(logits, dim=2)
    input_tokens = keyword_tokenizer.convert_ids_to_tokens(inputs["input_ids"].squeeze().tolist())

    extracted_keywords = []
    current_keyword_tokens = []
    for token, pred_id in zip(input_tokens, predictions_ids.squeeze().tolist()):
        if token in [keyword_tokenizer.cls_token, keyword_tokenizer.sep_token, keyword_tokenizer.pad_token]:
            continue
        label = id2label[pred_id]
        if label == 'B-KEY':
            if current_keyword_tokens:
                extracted_keywords.append(keyword_tokenizer.convert_tokens_to_string(current_keyword_tokens))
                current_keyword_tokens = []
            current_keyword_tokens.append(token)
        elif label == 'I-KEY' and current_keyword_tokens:
            current_keyword_tokens.append(token)
        else:
            if current_keyword_tokens:
                extracted_keywords.append(keyword_tokenizer.convert_tokens_to_string(current_keyword_tokens))
                current_keyword_tokens = []
    if current_keyword_tokens:
        extracted_keywords.append(keyword_tokenizer.convert_tokens_to_string(current_keyword_tokens))

    final_keywords = list(dict.fromkeys(extracted_keywords))[:10]
    return {"keywords": final_keywords}

@app.post("/generate_tags")
def generate_tags(input: TagInput):
    combined_text = PREFIX + "judul: " + input.title + " konten: " + input.content
    inputs = tag_tokenizer(
        combined_text,
        return_tensors="pt",
        max_length=MAX_INPUT_LENGTH,
        truncation=True,
        padding="max_length"
    ).to(device)

    with torch.no_grad():
        output = tag_model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=MAX_TARGET_LENGTH + 10,
            num_beams=5,
            early_stopping=True,
            no_repeat_ngram_size=2
        )

    decoded = tag_tokenizer.decode(output[0], skip_special_tokens=True)
    tag_list = [tag.strip() for tag in decoded.split(',')][:10]
    return {"tags": tag_list}
