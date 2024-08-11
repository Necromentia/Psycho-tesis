import json
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_extraction.text import CountVectorizer
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
import torch
import joblib

# Proporcionar el token en el script
token = "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"
data_file = 'casos_clinicos.json'
with open(data_file) as f:
    data = json.load(f)

# Normalizar el JSON
df = pd.json_normalize(data)

# Convertir la columna 'diagnostico.principal' a una sola columna
df['diagnostico.principal'] = df['diagnostico.principal'].apply(lambda x: x['principal'] if isinstance(x, dict) else x)

# Eliminar filas con valores NaN en la columna 'diagnostico.principal'
df = df.dropna(subset=['diagnostico.principal'])

# Verificar la distribución de las clases
print(df['diagnostico.principal'].value_counts())

# Filtrar las clases con menos de dos instancias
class_counts = df['diagnostico.principal'].value_counts()
valid_classes = class_counts[class_counts >= 2].index
df_filtered = df[df['diagnostico.principal'].isin(valid_classes)]

# Dividir los datos filtrados
train_data, eval_data = train_test_split(df_filtered, test_size=0.3, random_state=42, stratify=df_filtered['diagnostico.principal'])

text_features = [
    'paciente.antecedentes.historia_personal', 
    'paciente.antecedentes.historia_familiar', 
    'paciente.antecedentes.historia_clinica', 
    'sintomas.emocionales', 
    'sintomas.comportamentales', 
    'sintomas.sociales', 
    'sintomas.fisicos', 
    'explicacion.descripcion',
    'explicacion.evidencia'
]
cat_features = ['paciente.sexo']
num_features = ['paciente.edad']

vectorizers = {feature: CountVectorizer() for feature in text_features}
train_text_features = pd.concat([pd.DataFrame(vectorizers[feature].fit_transform(train_data[feature].astype(str)).toarray()) for feature in text_features], axis=1)
eval_text_features = pd.concat([pd.DataFrame(vectorizers[feature].transform(eval_data[feature].astype(str)).toarray()) for feature in text_features], axis=1)

one_hot_encoder = OneHotEncoder()
train_cat_features = one_hot_encoder.fit_transform(train_data[cat_features]).toarray()
eval_cat_features = one_hot_encoder.transform(eval_data[cat_features]).toarray()

scaler = StandardScaler()
train_num_features = scaler.fit_transform(train_data[num_features])
eval_num_features = scaler.transform(eval_data[num_features])

X_train = pd.concat([
    train_data.drop(text_features + cat_features + num_features + ['diagnostico.principal'], axis=1).reset_index(drop=True), 
    pd.DataFrame(train_text_features), 
    pd.DataFrame(train_cat_features), 
    pd.DataFrame(train_num_features)
], axis=1)
y_train = train_data['diagnostico.principal']

X_eval = pd.concat([
    eval_data.drop(text_features + cat_features + num_features + ['diagnostico.principal'], axis=1).reset_index(drop=True), 
    pd.DataFrame(eval_text_features), 
    pd.DataFrame(eval_cat_features), 
    pd.DataFrame(eval_num_features)
], axis=1)
y_eval = eval_data['diagnostico.principal']

# Asegurarse de que el token de padding esté presente y el modelo lo reconozca
tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct", trust_remote_code=True)
model = AutoModelForSequenceClassification.from_pretrained("microsoft/Phi-3-mini-4k-instruct", num_labels=len(y_train.unique()), token=token)

if tokenizer.pad_token is None:
    tokenizer.add_special_tokens({'pad_token': '[PAD]'})
model.resize_token_embeddings(len(tokenizer))

# Verificar que el modelo utilice el token de padding
model.config.pad_token_id = tokenizer.pad_token_id

train_encodings = tokenizer(list(X_train.apply(lambda x: ' '.join(map(str, x)), axis=1)), truncation=True, padding=True, max_length=512)
eval_encodings = tokenizer(list(X_eval.apply(lambda x: ' '.join(map(str, x)), axis=1)), truncation=True, padding=True, max_length=512)

class ClinicalDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

train_dataset = ClinicalDataset(train_encodings, pd.factorize(y_train)[0])
eval_dataset = ClinicalDataset(eval_encodings, pd.factorize(y_eval)[0])

training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=5,  # Incrementa el número de épocas
    per_device_train_batch_size=4,  # Ajusta el tamaño del lote
    per_device_eval_batch_size=4,
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir='./logs',
    logging_steps=10,
    eval_strategy="steps",  # Utiliza `eval_strategy` en lugar de `evaluation_strategy`
    eval_steps=100,
    save_steps=500,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)

trainer.train()

eval_result = trainer.evaluate()
print(f"Eval results: {eval_result}")

model.save_pretrained("custom_phi3_model")
tokenizer.save_pretrained("custom_phi3_model")

joblib.dump(vectorizers, "vectorizers.pkl")
joblib.dump(one_hot_encoder, "one_hot_encoder.pkl")
joblib.dump(scaler, "scaler.pkl")
