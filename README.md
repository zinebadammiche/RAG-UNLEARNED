# RAG-UNLEARNED

**Projet RAG** pour la gestion de documents sur le Sahara Occidental, avec un backend en Python et un frontend en Vue.js.

---

## Prérequis

- **Python 3.10+**
- **Node.js 18+** et **npm**
- **Git**

---

## Installation et exécution

### 1️ Cloner le dépôt

```bash
git clone https://github.com/zinebadammiche/RAG-UNLEARNED.git
cd RAG-UNLEARNED
```

---

### 2️ Configurer le backend

#### Pour **standardragback** ou **unlearnedragback** :
1. Accédez au dossier du backend :
   ```bash
   cd standardragback  # ou unlearnedragback
   ```
2. Créez et activez un environnement virtuel :
   ```bash
   python -m venv venv
   ```
   - **Windows** :
     ```bash
     venv\Scripts\activate
     ```
   - **Linux / Mac** :
     ```bash
     source venv/bin/activate
     ```
3. Installez les dépendances Python :
   ```bash
   pip install -r requirements.txt
   ```
4. Copiez le fichier `.env.example` en `.env` et **ajoutez votre token Hugging Face** dans le fichier `.env` :
   ```bash
   # Windows
   copy .env.example .env
   # Linux / Mac
   cp .env.example .env
   ```
   - Ouvrez le fichier `.env` et ajoutez votre token Hugging Face comme suit :
     ```
     HUGGINGFACE_TOKEN=votre_token_ici
     ```
5. Lancez le serveur backend :
   ```bash
   uvicorn main\:app --reload --port 8001  # ou 8000 selon votre configuration
   ```

---

### 3️ Configurer le frontend

1. Accédez au dossier du frontend :
   ```bash
   cd ../standarragfront  # ou unlearnedragfront
   ```
2. Installez les dépendances npm :
   ```bash
   npm install
   ```
3. Copiez le fichier `.env.example` en `.env` (si nécessaire) :
   ```bash
   # Windows
   copy .env.example .env
   # Linux / Mac
   cp .env.example .env
   ```
4. Lancez le serveur de développement :
   ```bash
   npm run dev
   ```

---

## Remarques
- Assurez-vous que le token Hugging Face est correctement configuré dans le fichier `.env` du backend pour accéder aux modèles  .
 
