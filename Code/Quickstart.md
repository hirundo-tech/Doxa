# Download & Use Doxa

### 1. Clone the Repository
```
git clone [https://github.com/your-username/doxa.git](https://github.com/your-username/doxa.git)
cd doxa
```

### 2. Setup Enviroment
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. API Configuration (.env)

Create a .env file in the root directory and add your keys:
```
OPENAI_API_KEY=your_openai_api_key
LLAMA_CLOUD_API_KEY=your_llama_parse_api_key
```

### 4. Run App
```
python app.py
```
