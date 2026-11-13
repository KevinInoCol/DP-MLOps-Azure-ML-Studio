# Instalación de azure CLI en MAC:
brew install azure-cli

# Logueo en CLI
az login

# Creo un Virtual Environment y activo. Con Python 3.11
conda create -n MLOps-AZURE-Consumo-Endpoint python=3.11
conda activate MLOps-AZURE-Consumo-Endpoint

# Instalación de las dependencias
pip install -r requirements.txt

# Ejecutamos la aplicación
streamlit run app_streamlit.py