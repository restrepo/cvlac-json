# cvlac-json

[![CI](https://github.com/restrepo/cvlac-json/actions/workflows/ci.yml/badge.svg)](https://github.com/restrepo/cvlac-json/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/cvlac-json.svg)](https://pypi.org/project/cvlac-json/)
[![Python](https://img.shields.io/pypi/pyversions/cvlac-json.svg)](https://pypi.org/project/cvlac-json/)

Convierte la página pública del **CvLAC** de un investigador (Minciencias, Colombia) en un único documento JSON: perfil, formación, experiencia, producción bibliográfica en el esquema de obras de [ImpactU](https://impactu.colav.co), proyectos, eventos, tesis dirigidas y todas las demás secciones.

- Sin dependencias: solo la biblioteca estándar de Python (3.10 o superior).
- Agrega los **identificadores ROR** de las instituciones de la experiencia y de las tesis.
- Con una clave de [apis.colav.co](https://apis.colav.co), agrega los **identificadores Scienti** (`COD_RH-COD_PRODUCTO`, `-COD_PROYECTO`, `-COD_EVENTO`) de las entradas que coinciden.

## Instalación

```bash
pip install cvlac-json
```

## Uso en la terminal

```bash
cvlac-json 0000026549                         # escribe cvlac_0000026549.json
cvlac-json 26549 -o zapata.json               # los ceros a la izquierda se agregan solos
cvlac-json 0000026549 --save-html cv.html     # guarda también la página descargada
cvlac-json 0000026549 --html cv.html          # analiza una página guardada, sin descargar
cvlac-json 0000026549 -o -                    # JSON por la salida estándar
cvlac-json 0000026549 --scienti off --ror off # solo la página pública, sin otras APIs
```

| Opción | Efecto |
| --- | --- |
| `--scienti auto` (por defecto) | Si hay clave de apis.colav.co, agrega los ids Scienti de las entradas que coinciden. |
| `--scienti full` | Además agrega los registros de Scienti que no están en la página (`origin: "scienti"`). |
| `--scienti off` | No consulta Scienti. |
| `--institution`, `--model-year` | Volcado de Scienti (`udea`, `univalle`, `uec`, `unaula`) y año del modelo. |
| `--apikey CLAVE` | Clave de apis.colav.co para esta ejecución. |
| `--siiu auto` / `off` | Con Scienti activo, agrega o no a los proyectos el código de SIIU (UdeA) del proyecto con el mismo título y un año compatible. |
| `--ror auto` / `off` | Consulta o no el registro ROR. |
| `--format json` / `jsonld` | Salida JSON (por defecto) o JSON-LD (ver más abajo). Sin `-o`, el archivo es `cvlac_COD_RH.json` o `cvlac_COD_RH.jsonld`. |
| `--base URL` | Con `--format jsonld`, prefijo del IRI del perfil, al que se agrega el COD_RH. Por defecto, el IRI es la URL de la página del CvLAC. |
| `--no-progress` | No muestra la barra de progreso. |

Mientras trabaja, el comando muestra en la terminal una barra de progreso con la etapa actual (descarga, análisis, cada consulta a Scienti, ROR) y el tiempo transcurrido:

```text
⠼ ████████░░░░░░░░░░░░░░░░░░░░░░  27% 4/11 Scienti products 1:12
```

La consulta de productos de Scienti puede tardar varios minutos en un CV grande: el indicador que gira y el reloj muestran que el programa sigue trabajando. La barra va por la salida de error y solo aparece cuando esta es una terminal, así que no se mezcla con el JSON (`-o -`) ni con las redirecciones a archivos.

La clave de apis.colav.co se toma, en este orden, de `--apikey`, de la variable de entorno `COLAV_APIKEY` o del archivo `~/.config/colav/apikey`. Nunca se imprime. Para no dejarla en el historial de la terminal, use `--apikey "$(cat archivo)"`.

## Uso como biblioteca

```python
from cvlac_json import extract

data = extract("0000026549", scienti="off")  # descarga y analiza la página
print(data["profile"]["Nombre"], len(data["works"]))

html = open("cv.html", encoding="latin-1").read()
data = extract("0000026549", html=html, ror=False)

# progreso propio: progress(etapa, hechas=None, total=None)
data = extract("0000026549", progress=lambda etapa, hechas=None, total=None: print(etapa))  # página guardada
```

## JSON-LD

`--format jsonld` (o `to_jsonld(data)` en Python) entrega el mismo documento con `@context`, `@id` y `@type`, listo para convertirlo a RDF:

```bash
cvlac-json 0000026549 --format jsonld                                   # @id = URL de la página del CvLAC
cvlac-json 0000026549 --format jsonld --base https://ejemplo.org/cvlac/ # @id = https://ejemplo.org/cvlac/0000026549
```

- Ninguna clave cambia de nombre ni de valor; el contexto usa schema.org donde el significado es claro y el vocabulario de este esquema en lo demás.
- Obras, proyectos, eventos e ítems de las demás secciones tienen un `@id` con un JSON Pointer a su lugar en el documento: `…/0000026549#/works/0`.
- `authors` es una lista ordenada (el orden de la cita se conserva en RDF); `counts` y `fields` quedan como literales JSON.
- El contexto completo, con la correspondencia de cada clave, está en la [sección 20 del esquema](docs/cvlac_json_esquema.md#20-json-ld).

## Esquema del JSON

El esquema completo, campo por campo, está en [docs/cvlac_json_esquema.md](docs/cvlac_json_esquema.md) y en versión navegable en [docs/cvlac_json_esquema.html](docs/cvlac_json_esquema.html).

## Desarrollo

```bash
git clone https://github.com/restrepo/cvlac-json.git
cd cvlac-json
python -m pip install -e ".[dev]"
python -m pytest
ruff check . && ruff format --check .
```

Las pruebas no usan la red: corren sobre una página sintética (`tests/fixtures/cvlac_sintetico.html`) con una persona ficticia y la misma estructura HTML del CvLAC.

Cómo publicar una versión nueva en PyPI: [PUBLISHING.md](PUBLISHING.md).

## Avisos

- La página del CvLAC es pública, pero contiene datos personales (nombre, nacionalidad, sexo). Úselos de acuerdo con la normativa de protección de datos que aplique.
- Sea moderado con el servidor de Minciencias: haga una pausa de uno o dos segundos entre CV cuando procese muchos.
- Las afiliaciones de las obras son **inferidas** de la experiencia (dónde trabajaba la persona ese año); el CvLAC no las declara.

## Licencia

[MIT](LICENSE)
