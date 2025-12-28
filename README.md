# Team Balancer

Pequeña app en Streamlit para generar equipos balanceados a partir de una lista de jugadores.

## Requisitos
- Windows (PowerShell)
- Python 3.11 (se probó con 3.11.9)

## Instalación (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar la app
```powershell
# Con el entorno activado
python -m streamlit run app.py
# Luego abrir http://localhost:8501 en el navegador
```

## Tests
```powershell
# Con el entorno activado
python -m pytest -q
```

## Notas
- `requirements.txt` contiene versiones pineadas para reproducibilidad.
- Si deseas migrar la persistencia a SQLite o añadir CI, puedo ayudarte a añadir esas mejoras.
