import json
from pathlib import Path

CHISTES_DIR = Path("chistes")

def validar_json():
    errores = []
    for archivo in CHISTES_DIR.glob("*.json"):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                errores.append(f"❌ {archivo.name} no es una lista (tipo {type(data)})")
            elif not all(isinstance(chiste, str) for chiste in data):
                errores.append(f"⚠️ {archivo.name} tiene elementos que no son texto")

        except Exception as e:
            errores.append(f"❌ Error en {archivo.name}: {e}")

    if errores:
        print("\n".join(errores))
    else:
        print("✅ Todos los archivos JSON en 'chistes/' son válidos.")

if __name__ == "__main__":
    validar_json()
