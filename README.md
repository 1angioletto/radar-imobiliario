# 🏠 Radar Imobiliário

Plataforma de inteligência imobiliária desenvolvida para identificar oportunidades de compra de imóveis através da análise automatizada de anúncios, processamento em nuvem e visualização interativa dos dados.

---

## 🚀 Visão Geral

O Radar Imobiliário coleta anúncios de imóveis automaticamente, processa os dados na Google Cloud Platform e disponibiliza insights através de um dashboard web interativo.

O objetivo é ajudar investidores e profissionais do mercado imobiliário a encontrarem imóveis com potencial de valorização e preços abaixo da média regional.

---

## ✨ Funcionalidades

* 🔎 Coleta automatizada de anúncios imobiliários
* 🏘️ Suporte para terrenos e casas
* 📊 Dashboard interativo em Streamlit
* ☁️ Integração com Google Cloud Platform
* 🗄️ Armazenamento e análise no BigQuery
* 📦 Versionamento histórico dos anúncios
* 📈 Identificação de oportunidades de mercado
* 🤖 Recursos de Inteligência Artificial com Vertex AI
* 🐳 Deploy automatizado utilizando Docker e Cloud Run

---

## 🏗️ Arquitetura

```text
OLX
 ↓
Python + Playwright
 ↓
Google Cloud Storage
 ↓
BigQuery (Stage + Histórico + Eventos)
 ↓
Views SQL
 ↓
Streamlit
 ↓
Cloud Run
```

---

## 🛠️ Tecnologias Utilizadas

### Backend e Coleta

* Python
* Playwright
* Pandas

### Google Cloud Platform

* BigQuery
* Cloud Storage
* Cloud Run
* Vertex AI
* Cloud Build

### Frontend

* Streamlit

### DevOps

* Docker
* Git
* GitHub

---

## 📂 Estrutura do Projeto

```text
radar-imobiliario/
├── App/
│   ├── app.py
│   ├── assets/
│   └── Dockerfile
│
├── pipelines/
│   ├── coletores/
│   └── uploads_bigquery/
│
├── sql/
│   └── views/
│
├── requirements.txt
└── README.md
```

---

## ⚙️ Executando Localmente

### Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### Instalar dependências

```bash
pip install -r requirements.txt
```

### Configurar credenciais GCP

```bash
gcloud auth application-default login
gcloud config set project radar-imobiliario
```

### Executar aplicação

```bash
streamlit run App/app.py
```

---

## 🚢 Deploy no Cloud Run

### Build da imagem

```bash
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/radar-imobiliario/cloud-run-source-deploy/radar-imobiliario:latest
```

### Deploy

```bash
gcloud run deploy radar-imobiliario \
  --image us-central1-docker.pkg.dev/radar-imobiliario/cloud-run-source-deploy/radar-imobiliario:latest \
  --region us-central1 \
  --platform managed
```

---

## 🎯 Objetivo do Projeto

Desenvolver uma solução escalável de inteligência imobiliária que permita identificar oportunidades de investimento utilizando dados públicos e técnicas modernas de engenharia de dados.

---

## 👨‍💻 Autor

**Guilherme Angioletto**

Engenheiro de Dados especializado em soluções utilizando Google Cloud Platform.

LinkedIn: https://www.linkedin.com/in/guilherme-angioletto/

GitHub: https://github.com/1angioletto
