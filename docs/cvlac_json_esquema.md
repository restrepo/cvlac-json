# Esquema del JSON extraído del CvLAC

Este documento describe el JSON que produce el paquete **cvlac-json** (comando `cvlac-json` o función `cvlac_json.extract()`) a partir de la página pública del CvLAC de un investigador:

```
https://scienti.minciencias.gov.co/cvlac/visualizador/generarCurriculoCv.do?cod_rh=COD_RH
```

El esquema se verificó contra cinco CV reales de profesores de la UdeA (2026-10-28). Los ejemplos de este documento usan una persona ficticia (Ana María Pérez Gómez, COD_RH `0000000001`); los valores de los ejemplos imitan los reales.

## 1. Cómo se genera

```bash
cvlac-json COD_RH [-o salida.json] [--html pagina_guardada.html] [--save-html pagina.html]
           [--scienti auto|full|off] [--institution udea] [--model-year 2024]
           [--apikey CLAVE] [--siiu auto|off] [--ror auto|off]
           [--format json|jsonld] [--base URL] [--no-progress]
```

El JSON combina tres fuentes:

| Fuente | Qué aporta | Opción |
| --- | --- | --- |
| Página pública del CvLAC | **Todos los registros** (perfil, formación, experiencia, productos, proyectos, eventos…) | Siempre |
| Scienti (apis.colav.co, con clave) | Solo los **identificadores Scienti** de las entradas que coinciden (`COD_RH-COD_PRODUCTO`, etc.) y la evidencia de la coincidencia | `--scienti auto` (por defecto) |
| Scienti, registros completos | Además, los registros de Scienti que **no** están en la página, marcados `origin: "scienti"` | `--scienti full` |
| ROR (api.ror.org) | Identificador ROR de las instituciones de la experiencia y de las tesis | `--ror auto` (por defecto) |

Con la configuración por defecto, **todo registro proviene de la página pública**; de Scienti solo llegan ids y la evidencia de la coincidencia, y los registros que solo están en Scienti se cuentan en `scienti.not_on_page`, sin incluirlos.

## 2. Convenciones generales

- **Los mismos campos en todos los registros de una colección.** En `works`, `projects`, `events`, `patents`, `experience`, cada lista de `education` y cada lista de `other_products`, si un campo tiene valor en algún registro, aparece en todos: vale `[]` (listas) o `null` (lo demás) donde no hay dato. Lo mismo dentro de los objetos anidados (`source`, `cvlac`, `authors[]`, `affiliations[]`…).
- **Campos vacíos en toda la colección se eliminan** de esa colección. Por eso las claves pueden variar de un CV a otro (por ejemplo, un CV sin palabras clave no tiene `keywords` en sus `works`).
- **Campos que el CvLAC nunca publica no existen**: no hay `abstracts`, `citations_count`, `groups`, `ranking`, `language` ni `date_published`.
- **Fechas**: año y mes como enteros (`{"year": 2014, "month": 7}`), o cadenas ISO `AAAA-MM-DD` en eventos. No hay fechas en segundos (a diferencia de ImpactU).
- **Textos**: se conservan como aparecen en la página (mayúsculas, errores de digitación como "Coturor/asesor" o "blibliográfica").
- **`provenance` / `source`** siguen la convención de ImpactU: `cvlac` (página), `scienti` (apis.colav.co), `ror` (registro ROR).
- **Datos personales**: el JSON guarda lo que muestra la página pública (nombre, nacionalidad, sexo). No incluye números de identificación. De Scienti solo se copian nombres, nunca los campos personales de sus registros de autor.

## 3. Identificadores

| Identificador | Formato | Ejemplo | Dónde aparece |
| --- | --- | --- | --- |
| COD_RH (Scienti/CvLAC) | 10 dígitos | `0000000001` | `cod_rh`; `authors[].id` del dueño del CV |
| Obra del CvLAC | `cvlac:COD_RH:n` (n = orden en la página) | `cvlac:0000000001:1` | `works[].id` |
| Obra solo en Scienti (`--scienti full`) | `scienti:COD_RH-COD_PRODUCTO` | `scienti:0000000001-10` | `works[].id` |
| Producto Scienti | `COD_RH-COD_PRODUCTO` | `0000000001-20912` | `works[].external_ids`, `works[].cvlac.scienti.id`, `patents[].scienti.id`, `other_products.*[].scienti.id` |
| Proyecto Scienti | `COD_RH-COD_PROYECTO` | `0000000001-1` | `projects[].scienti.id`, `projects[].external_ids` |
| Proyecto SIIU (UdeA) | `AAAA-n` | `2014-361` | `projects[].siiu.id`, `projects[].external_ids` |
| Evento Scienti | `COD_RH-COD_EVENTO` | `0000000001-4` | `events[].scienti.id` |
| Red Scienti | `COD_RH-COD_RED` | | `other_products["Redes de conocimiento especializado"][].scienti.id` |
| ROR | id corto (9 caracteres) y URL | `03bp5hc83`, `https://ror.org/03bp5hc83` | `affiliations[].id`, `affiliations[].external_ids`, `experience[].ror.id`, `institution.id` |
| DOI | sin prefijo en `external_ids`, como URL en `doi` | `10.9999/synthetic.2017.003` | `works[]` |

## 4. Nivel superior

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `cod_rh` | string | COD_RH del investigador (10 dígitos). |
| `url` | string | URL de la página del CvLAC leída. |
| `retrieved` | string | Fecha y hora de la extracción (ISO 8601, UTC). |
| `profile` | object | Datos de la hoja de vida (§5). |
| `identifiers` | array | Identificadores de autor: ORCID, Scopus… (§6). |
| `academic_networks` | array | Perfiles en redes académicas y sociales: Google Scholar, ResearchGate, LinkedIn… (§6). |
| `education` | object | `academic` (formación académica) y `complementary` (formación complementaria) (§7). |
| `experience` | array | Experiencia profesional, con años y ROR (§8). |
| `areas` | array de string | Áreas de actuación, "Gran área -- Área -- Disciplina". |
| `languages` | array | Idiomas (§9). |
| `research_lines` | array | Líneas de investigación (§9). |
| `awards` | array | Reconocimientos (§9). |
| `works` | array | **Producción bibliográfica** en el esquema de obras de ImpactU (§10). |
| `projects` | array | Proyectos (§11). |
| `events` | array | Eventos científicos (§12). |
| `patents` | array | **Patentes** (la sección Patentes del CvLAC), con número, título, oficina, fechas, solicitante y gaceta (§13). Siempre presente; `[]` si no hay. |
| `other_products` | object | **Demás productos**: las demás secciones del CV, por título (§13); las tesis dirigidas tienen campos estructurados (§14). Hasta 0.6.0 se llamaba `sections` e incluía Patentes. |
| `counts` | object | Conteos (§15). |
| `affiliations_from_experience` | object | Resumen de la búsqueda ROR y las afiliaciones asignadas (§16). |
| `scienti` | object | Resumen del cruce con Scienti; solo con clave de apis.colav.co (§17). |
| `siiu` | object | Resumen del cruce con los proyectos de SIIU de la UdeA; solo con clave de apis.colav.co (§17). |

## 5. `profile`

Objeto con las filas de la tabla "Hoja de vida" de la página; las claves son las etiquetas tal como aparecen.

| Clave | Tipo | Ejemplo |
| --- | --- | --- |
| `Categoría` | string | "Investigador Asociado (I) con vigencia hasta la publicación de los resultados de la siguiente convocatoria" |
| `Nombre` | string | "Ana María Pérez Gómez" |
| `Nombre en citaciones` | string | "PÉREZ GÓMEZ, ANA MARÍA" |
| `Nacionalidad` | string | "Colombiana" |
| `Sexo` | string | "Femenino" |
| `notes` | array de string | Notas sueltas de la hoja de vida, p. ej. "Par evaluador reconocido por Minciencias" |
| `full_name` | string | Nombre completo, igual a `Nombre` | "Ana María Pérez Gómez" |
| `first_names` | array de string | Nombres, como en el registro de persona de ImpactU | `["Ana", "María"]` |
| `last_names` | array de string | Apellidos, uno por elemento; las partículas van con el apellido (`"de la Cruz"`) | `["Pérez", "Gómez"]` |
| `name_split_by` | string | Cómo se separó el nombre: `page`, `citation name` o `nationality` (ver abajo) | `page` |

El nombre y el nombre en citaciones se usan para reconocer al dueño del CV entre los autores.

**Nombres y apellidos.** Se conservan `Nombre` y `Nombre en citaciones` y se agregan `full_name`, `first_names` y `last_names`, como en ImpactU. La separación usa, en este orden:

1. `page`: la página escribe el nombre como `NOMBRES&nbsp;APELLIDO1&nbsp;APELLIDO2`; esas partes se usan si coinciden con los apellidos de `Nombre en citaciones` (lo que va antes de la coma).
2. `citation name`: si no coinciden, el número de palabras antes de la coma de `Nombre en citaciones` dice cuántas palabras finales de `Nombre` son apellidos.
3. `nationality`: si no hay nombre en citaciones, dos apellidos para nacionalidades hispanas (Colombiana, Española, Mexicana…) y uno para las demás.

En los cinco CV de prueba la separación salió de la página (`page`) y coincidió con el nombre en citaciones.

## 6. `identifiers` y `academic_networks`

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `name` | string | Nombre del enlace en la página, p. ej. "Autor ID (Scopus)", "Google Scholar". |
| `url` | string | Enlace. |
| `source` | string o null | Fuente normalizada: `orcid`, `scopus`, `scholar`; `null` en las demás (ResearchGate, LinkedIn). |
| `id` | string o null | Identificador extraído del enlace, p. ej. `57000000000` (Scopus), `AbCdEfGhIjKl` (Scholar). |

## 7. `education.academic[]` y `education.complementary[]`

| Campo | Tipo | Descripción | Ejemplo |
| --- | --- | --- | --- |
| `level` | string | Nivel | "Doctorado", "Cursos de corta duración" |
| `institution` | string | Institución, como en la página | "UNIVERSIDAD DE ANTIOQUIA" |
| `program` | string | Programa | "Doctorado en Ingeniería" |
| `start`, `end` | object | `{year, month}`; `month` puede ser `null` | `{"year": 2002, "month": 1}` |
| `dates_text` | string | Texto original de las fechas | "Enerode2010 - Diciembrede 2014" |
| `thesis` | string o null | Título de la tesis (solo formación académica) | |

## 8. `experience[]`

| Campo | Tipo | Descripción | Ejemplo |
| --- | --- | --- | --- |
| `institution` | string | Institución o unidad, como en la página | "UNIVERSIDAD DE ANTIOQUIA", "FACULTAD DE QUIMICA FARMACEUTICA" |
| `dedication` | string | Dedicación | "40 horas Semanales" |
| `period` | string | Periodo original | "Febrero de 1995 de", "Marzo de 2006 de Actual" |
| `start_year`, `end_year` | integer | Años del periodo | 1995, 2026 |
| `open_end` | boolean | `true` si el periodo no tiene fin: `end_year` es entonces el año actual | `true` |
| `ror` | object o null | `{id, name, match}` del registro ROR aceptado; `null` si no hay | `{"id": "03bp5hc83", "name": "Universidad de Antioquia", "match": "name"}` |
| `activities` | array | `{type, items[]}`: actividades de docencia, investigación, administración… | |

**Regla ROR**: se acepta un registro solo si uno de sus nombres, alias, etiquetas o siglas coincide con el nombre del CvLAC (sin tildes ni mayúsculas) → `match: "name"`; o si uno es prefijo del otro por palabras, con puntaje ≥ 0.9 → `match: "prefix"` (p. ej. "UNIVERSIDAD NACIONAL DE COLOMBIA SEDE MANIZALES" → Universidad Nacional de Colombia). Las facultades y departamentos casi nunca tienen ROR.

## 9. `languages[]`, `research_lines[]`, `awards[]`

| Objeto | Campos |
| --- | --- |
| `languages[]` | `language`, `speaks`, `writes`, `reads`, `understands` (valores como "Bueno", "Aceptable") |
| `research_lines[]` | `name`, `active` (boolean) |
| `awards[]` | `name`, `institution`, `date` (`{year, month}`), `text` (texto original) |

## 10. `works[]`: producción bibliográfica (esquema de obras de ImpactU)

Incluye las secciones Artículos, Libros, Capítulos de libro, Textos en publicaciones no científicas, Otra producción bibliográfica, Documentos de trabajo, Libros de formación o divulgación, Manuales y guías especializadas, Traducciones, Notas científicas y Trabajos en eventos.

| Campo | Tipo | Descripción | Ejemplo |
| --- | --- | --- | --- |
| `id` | string | `cvlac:COD_RH:n` | `cvlac:0000000001:1` |
| `title` | string | Título | "A synthetic benchmark for testing CvLAC parsers" |
| `titles[]` | array | `{title, source: "cvlac", provenance: "cvlac"}` | |
| `types[]` | array | Jerarquía del tipo de producto: `{type, level, source, provenance}`; nivel 0 "Producción bibliográfica", nivel 1 la clase (Artículo, Libro, Capítulo de libro…), nivel 2 el subtipo. Son los mismos nombres que ImpactU guarda con `source: "scienti"`. | |
| `product_types[]` | array | `{name, source}` con el tipo más específico | "Publicado en revista especializada" |
| `authors[]` | array | Autores en el orden de la página (ver abajo) | |
| `authors_count` | integer | Número de autores listados. El CvLAC a menudo lista solo al dueño, así que puede ser menor que el real. | 1 |
| `year_published` | integer o null | Año de publicación. En los formatos etiquetados (libros de divulgación, de formación…) se toma de "Fecha de presentación"; en los demás, de la cita (un año en el título, como "…al año 2050", no cuenta en los etiquetados). | 2017 |
| `doi` | string o null | DOI como URL, en minúsculas. Se busca después de "DOI:", también escrito como enlace (`https://doi.org/10…`, `dx.doi.org`) o con texto antes; si no está ahí, en el resto de la cita y en sus enlaces. Se quitan la puntuación y la barra finales. Un DOI truncado en la página queda truncado (p. ej. `10.1111/1750-3841`, que es solo el prefijo de una revista). | `https://doi.org/10.9999/synthetic.2017.003` |
| `external_ids[]` | array | `{provenance, source, id}`: `doi`, `isbn` y, si hubo coincidencia, `scienti` (`COD_RH-COD_PRODUCTO`) | `{"provenance": "scienti", "source": "scienti", "id": "0000000001-20912"}` |
| `external_urls[]` | array | `{provenance, source, url}`: enlaces del ítem y el "Medio de verificación". No aparece en los cinco CV de prueba (ninguna obra tenía enlaces). | |
| `source` | object | Revista o libro: `name`, `external_ids[]` (`issn` o `isbn`), `publisher` (`name`, `country`). En artículos, la revista con ISSN; en capítulos, el libro con ISBN; en libros no hay `name`. | `{"name": "REVISTA DE PRUEBAS SINTETICAS", "external_ids": [{"source": "issn", "id": "1234-5679"}], …}` |
| `bibliographic_info` | object o null | `volume`, `issue`, `start_page`, `end_page`, `pages` (número de páginas de un libro) | `{"volume": "12", "issue": "3", "start_page": "101", "end_page": "115"}` |
| `keywords[]` | array de string | "Palabras" del ítem | "parsing" |
| `subjects[]` | array | `{source: "cvlac", subjects: [{name, level}]}` desde las "Areas" (gran área, área, disciplina) | |
| `cvlac` | object | Datos propios del CvLAC (ver abajo) | |
| `origin` | string | Solo con `--scienti full`: `"cvlac"` o `"scienti"` | |

**`works[].authors[]`**

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `full_name` | string | Nombre como aparece en la cita. |
| `id` | string o null | COD_RH del dueño del CV; `null` para los demás autores. |
| `external_ids[]` | array | `{provenance: "cvlac", source: "scienti", id: COD_RH}` para el dueño. |
| `affiliations[]` | array | Solo el dueño: instituciones de su experiencia cuyo periodo contiene `year_published` (§16). Los coautores no tienen afiliación (la página no la da). |
| `product_hash` | string o null | Solo el dueño: identificador del producto, reproducible desde el GrupLAC (§21). | `"efc8d0bb2fa5…"` |

**El dueño está en todos los registros.** En obras, proyectos, patentes y demás productos (y en los `participants` de los eventos), el dueño del CV aparece siempre, con su COD_RH. Se reconoce por su nombre completo o su nombre en citaciones (o las mismas palabras de este). Si ninguna persona listada lo es, se toma como dueño la única que sea una forma abreviada de su nombre: al menos dos palabras, una de tres letras o más, todas del nombre del dueño, y cada inicial suelta la de una de ellas ("VICTOR ALONSO MOLINA", "CANO, L.E"). Si tampoco hay una, el dueño se agrega al final de la lista. Los dos casos se cuentan en `counts.owner_by_name_variant` y `counts.owner_added`. Las partes con rótulo ("Nombre del producto: …") no son autores.

**`works[].cvlac`**

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `section` | string | Sección del CvLAC: "Artículos", "Capitulos de libro", "Libros"… |
| `endorsed` | boolean | Marca de verificación de la página: producto avalado y validado en la última convocatoria de medición. Su ausencia no significa que el producto no sea válido. |
| `country` | string o null | País de "En:" (de la revista o editorial, no de los autores). |
| `authors_inferred` | boolean | `true` en formatos sin autores (libros de formación, manuales): se asume que el autor es el dueño del CV. |
| `sectors[]`, `areas[]` | array de string | Sectores y áreas del ítem, como en la página. |
| `fields` | object | Pares etiqueta → valor del ítem (ISSN, ed, v, fasc, DOI…). |
| `text` | string | Cita completa, como aparece en la página. |
| `scienti` | object o null | Coincidencia con Scienti (§17). |

## 11. `projects[]`

| Campo | Tipo | Descripción | Ejemplo |
| --- | --- | --- | --- |
| `type` | string | Tipo de proyecto | "Investigación y desarrollo" |
| `title` | string | Título | "Plataforma sintética para pruebas" |
| `authors[]` | array | **Siempre presente.** El dueño del CV solo (la página no lista a los demás participantes), con la forma de §10: `{full_name, id, external_ids, affiliations}`. `affiliations` son las instituciones de su experiencia cuyo periodo se cruza con el del proyecto (año de inicio a `end`, o `projected_end`, o solo el inicio) y, si el proyecto coincide con uno de SIIU y la experiencia no da la UdeA, la Universidad de Antioquia con `cvlac.provenance: "siiu project"` y los años de SIIU (§16). | `[{"full_name": "Ana María Pérez Gómez", "id": "0000000001", …}]` |
| `start` | object | `{year, month}` | `{"year": 1998, "month": 1}` |
| `end` | object o null | `{year, month}` de finalización | |
| `projected_end` | object o null | `{year, month}` de finalización proyectada | |
| `duration_months` | integer o null | Duración en meses | |
| `summary` | string o null | Resumen | |
| `scienti` | object o null | Coincidencia con un proyecto Scienti (§17) | `{"id": "0000000001-1", …}` |
| `external_ids` | array | `{provenance, source, id}` con `source` `scienti` o `siiu`, como en las obras | `[{"provenance": "siiu", "source": "siiu", "id": "2014-361"}]` |
| `siiu` | object o null | Coincidencia con un proyecto de SIIU (§17) | `{"id": "2014-361", "status": "liquidado", …}` |

El CvLAC no enlaza proyectos con productos: no presente un proyecto como fuente de una obra sin otra evidencia (OpenAlex `awards`, compromisos de SIIU).

## 12. `events[]`

| Campo | Tipo | Descripción | Ejemplo |
| --- | --- | --- | --- |
| `name` | string | Nombre del evento | "Simposio internacional de ejemplo" |
| `type` | string | Tipo | "Simposio" |
| `scope` | string o null | Ámbito | "Internacional" |
| `endorsed` | boolean | Marca de verificación | |
| `start`, `end` | string (`AAAA-MM-DD`) o null | Fechas | "2014-10-20" |
| `place` | string o null | Lugar | "Medellín - Universidad de Antioquia" |
| `products[]` | array | Productos asociados: `{name, type}` (único vínculo explícito producto–actividad del CvLAC) | |
| `institutions[]` | array | `{name, link}`; `link` es el tipo de vínculo ("Patrocinadora", "Gestionadora") | |
| `participants[]` | array | `{name, role, id, external_ids, affiliations}`. El dueño, reconocido por su nombre como en las obras (§10), lleva su COD_RH en `id` y en `external_ids`, y en `affiliations` las instituciones de su experiencia cuyo periodo contiene el año de `start` (o de `end`) (§16); si no está en la lista, se agrega al final con `role: null`. Los demás tienen `id: null`, `external_ids: []` y `affiliations: []`. | `{"name": "ANA MARIA PEREZ GOMEZ", "role": "Ponente", "id": "0000000001", …}` |
| `scienti` | object o null | Coincidencia con un evento Scienti (§17) | |

## 13. `patents` y `other_products`: patentes y demás productos

- **`patents`** (nivel superior) es la lista de ítems de la sección Patentes del CvLAC.
- **`other_products`** es un objeto cuyas claves son los títulos de las demás secciones del CvLAC y cuyos valores son listas de ítems. En los 4.596 CvLAC de la UdeA aparecen 48 secciones además de Patentes, entre ellas: Trabajos dirigidos/tutorías, Jurado en comités de evaluación, Par evaluador, Cursos de corta duración, Participación en comités de evaluación, Informes de investigación, Demás trabajos, Consultorías, Nueva secuencia genética, Ediciones/revisiones, Informes técnicos, Redes de conocimiento especializado, Softwares, Prototipos, Producciones de contenido digital, Boletines, Normas y Regulaciones, Secretos empresariales, Signos distintivos, Empresas de base tecnológica y Concepto técnico. Las cuatro secciones de apropiación social del conocimiento (Fortalecimiento o solución de asuntos de interés social, Generación de insumos de política pública y normatividad, Fortalecimiento de cadenas productivas, Trabajo conjunto entre un Centro de Ciencia y un grupo de investigación), cuyos ítems tienen `type` "Apropiación social del conocimiento - Proceso de …", van juntas en una sola lista, "Apropiación social del conocimiento", donde estaba la primera; cada ítem conserva su `type`, que dice de cuál viene. Los productos de divulgación pública de la ciencia (contenido digital, transmedia, desarrollos web), que el menú del CvLAC también pone bajo "Apropiación social", siguen en sus propias secciones.

Hasta la versión 0.6.0 ambos iban juntos en `sections` (las patentes en `sections["Patentes"]`).

Los ítems de `patents` y de `other_products` tienen la misma forma: el texto y, además, los campos estructurados que se puedan leer de él. Las tesis dirigidas tienen sus propios campos (§14).

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `type` | string | Tipo de producto del CvLAC, niveles separados por " - " (p. ej. "Producción técnica - Cursos de corta duración dictados - Extensión extracurricular"). En Asesorías y Secretos empresariales la página pone ahí el nombre del producto. Falta si toda la sección lo tiene vacío. |
| `endorsed` | boolean | Marca de verificación. |
| `title` | string o null | Nombre del producto: el texto entre las personas y el primer dato rotulado, o el valor de "Nombre del producto", "Titulo", "Nombre de la red", "Nombre del evento"… |
| `authors[]` | array | **Siempre presente.** Las personas escritas antes del título, en orden; si la página no lista a nadie, el dueño del CV solo. La página pone cada persona en su propia línea, terminada en coma, y así se separan del título aunque este tenga comas. Cada una es `{full_name, id, external_ids, affiliations}`, como en las obras (§10): el dueño lleva su COD_RH en `id` y en `external_ids`, en `affiliations` las instituciones de su experiencia cuyo periodo contiene el año del ítem (`year`, o el de `date`) (§16), y su `product_hash` (§21); las demás personas tienen `id: null` y `affiliations: []`. En Jurado en comités de evaluación son los jurados (`type: "jury"`) y los orientados (`type: "student"`). |
| `country`, `city` | string | País ("En: Colombia") y ciudad ("En: MEDELLÍN", "Ciudad: …"). |
| `place` | string | Lugar de realización (Talleres creativos). |
| `institution` | string | Institución del ítem: la de "Institución", la solicitante de un concepto técnico, la que emite un registro, la del curso o el comité ("en: …"). |
| `publisher` | string | Editorial o entidad tras el año en Ediciones/revisiones. |
| `source` | object | Solo patentes: los datos que siguen a "Gaceta Industrial de Publicación:" hasta el final del ítem. Tienen la forma `valor rótulo: valor rótulo: valor…`, separados por ",", ", . ", "· " o " ". La parte inicial sin rótulo es `publisher`: un número de gaceta ("849 del 18 de enero de 2019"), una oficina, una URL o un número de publicación. Cada parte con rótulo es una clave más: los rótulos conocidos llevan nombre en inglés (`gazette` ← Gaceta, `publication_date` ← Fecha de publicación o International Publication date, `date` ← Fecha, `international_publication` ← Publicación internacional, `publication_number` ← Nº de publicación o Pub. No., `application_number` ← Número de solicitud o Application Number, `international_application` ← International Application Number o No., `resolution` ← Resolución), y los demás conservan el rótulo como está escrito (`np`, `S/REF`, `Folios`). Así, "AU2014313817B2· Fecha de publicación: 2018-06-14 Publicación Internacional: WO2015028920A1" da `{"publisher": "AU2014313817B2", "publication_date": "2018-06-14", "international_publication": "WO2015028920A1"}`. Como en todo registro, las claves que tiene alguna patente del CV están en todas (en `null` si faltan). Falta si no hay ningún dato (vacío, "N/A", "No aplica"). |
| `venue` | string | Revista o editorial evaluada (Par evaluador). |
| `scope` | string | "Ámbito": Local, Municipal, Departamental, Nacional o Internacional (Par evaluador, Boletines, Talleres Creativos). |
| `review_of` | string | "Par evaluador de": lo que se evaluó, p. ej. "Proyecto" o "Material para publicación científica" (Par evaluador). |
| `program` | string | Programa académico del trabajo evaluado (Jurado). |
| `date` | string | Fecha ISO: `AAAA-MM-DD`, `AAAA-MM` o `AAAA`, de "Fecha de presentación", "Fecha de inicio", "Creada el", "En: Junio - 2016", la fecha de la patente… |
| `duration` | object | `{value, unit}` con unidad `meses`, `semanas`, `horas` o `días`; no aparece si vale 0. |
| `pages` | integer | "p.155", si es mayor que 0. |
| `role` | string | "participación: Docente" (cursos). |
| `purpose` | string | "Finalidad". |
| `holder` | string | Titular: solicitante de la patente, titular del signo distintivo o del secreto empresarial. |
| `database` | string | Base de datos de una secuencia o un registro científico (GenBank, ENA, Index Fungorum…). |
| `platform`, `environment` | string | Plataforma y ambiente de un software. |
| `identifiers[]` | array | `{source, id}`. `source`: `contract/registration` (contrato/registro), `patent` (en `patents`: el texto antes del primer " - ", con sus espacios: `AU 2014313817 B2`, `US 10,085,948 B2`, `NC2020/0015295`; los guiones sin espacios, como en `10-1784319`, son parte del número), `gazette` (número de la Gaceta Industrial: el texto si empieza por cifras, o el valor de `Gaceta:`), `registration` (signos, INVIMA), `nit`, `concept number`, `trade secret`, `copyright registration` (Dirección Nacional de Derechos de Autor), `accession` (palabras clave con forma de número de acceso, en secuencias), `doi`, `isbn`, `issn`. |
| `links[]` | array | `{url, label}`: enlaces `<a>` del ítem y URL escritas en el texto (medio de verificación, "disponible en", plataforma, página web). Las que empiezan por `www.` reciben `http://`. |
| `text` | string | Texto completo del ítem. |
| `fields` | object o null | Pares etiqueta → valor (`Finalidad`, `Institución`, `Nombre comercial`, `contrato/registro`…). Los valores que antes seguían hasta el final del ítem (`"574273, . En: Colombia, ,2018, 0 meses p"`) se cortan donde empieza la parte sin rótulo; los vacíos o "n/a" se quitan. |
| `keywords[]`, `areas[]`, `sectors[]` | array de string | Palabras, áreas y sectores del ítem. |
| `year` | integer o null | Año detectado en el texto. |
| `scienti` | object o null | Coincidencia con un producto o red Scienti (§17). Los pares evaluadores no son productos Scienti y no tienen id. |
| `origin` | string | Solo con `--scienti full`. |

Como en todo el JSON, un campo aparece en todos los ítems de una sección si tiene valor en alguno, y no aparece si está vacío en todos (§2).

Ejemplo de `patents[]` (la afiliación se abrevia):

```json
{
  "type": "Producción técnica - Patente - Patente de invención",
  "endorsed": true,
  "title": "Ionic Gelation on Solids",
  "authors": [
    {"full_name": "Ana María Pérez Gómez", "id": "0000000001",
     "external_ids": [{"provenance": "cvlac", "source": "scienti", "id": "0000000001"}],
     "affiliations": [{"id": "03bp5hc83", "name": "Universidad de Antioquia", "years": [2010, 2011, "…"], "cvlac": {"provenance": "cvlac experience", "…": "…"}}]}
  ],
  "country": "Australia",
  "institution": "Australian Patent Office",
  "date": "2016-12-22",
  "holder": "Universidad de Antioquia",
  "identifiers": [{"source": "patent", "id": "AU 2014313817 B2"}],
  "source": {"publisher": "AU2014313817B2", "publication_date": "2018-06-14", "international_publication": "WO2015028920A1"},
  "text": "AU 2014313817 B2 - Ionic Gelation on Solids, Institución: Australian Patent Office, Vía de solicitud: Via Patent Cooperation Treaty (PCT) En: Australia, ,2016-12-22 00:00:00.0, . Nombre del solicitante de la patente: Universidad de Antioquia, . Gaceta Industrial de Publicación: AU2014313817B2· Fecha de publicación: 2018-06-14 Publicación Internacional: WO2015028920A1,",
  "fields": {"Institución": "Australian Patent Office", "Vía de solicitud": "Via Patent Cooperation Treaty (PCT)"},
  "year": 2016
}
```

Ejemplo de `other_products["Consultorías"][]`:

```json
{
  "type": "Producción técnica - Consultoría Científico Tecnológica e Informe Técnico - Servicios de proyectos de IDI",
  "endorsed": false,
  "title": "Componente de investigación en proyecto Implementación de estrategias de innovación…",
  "authors": [
    {"full_name": "BETSELENE MURCIA ORDONEZ", "id": "0000157155", "external_ids": [{"provenance": "cvlac", "source": "scienti", "id": "0000157155"}],
     "affiliations": [{"id": "…", "name": "…", "cvlac": {"provenance": "cvlac experience", "…": "…"}}]},
    {"full_name": "LUIS CARLOS CHAVES MORENO", "id": null, "external_ids": [], "affiliations": []}
  ],
  "country": "Colombia",
  "duration": {"value": 12, "unit": "meses"},
  "identifiers": [{"source": "contract/registration", "id": "003 de 2017"}],
  "text": "BETSELENE MURCIA ORDONEZ, LUIS CARLOS CHAVES MORENO, Componente de investigación…, Nombre comercial: , contrato/registro: 003 de 2017, . En: Colombia, ,2017, 12 meses p.",
  "fields": {"contrato/registro": "003 de 2017"},
  "year": 2017
}
```

## 14. Tesis dirigidas: `other_products["Trabajos dirigidos/tutorías"][]`

Además de los campos genéricos, cada ítem tiene campos estructurados, leídos de la estructura de la página (el CvLAC separa con `&nbsp;` "DUEÑO, Título" / institución / "Estado: …" / programa / "AÑO. Dirigió como: ROL" / estudiantes / "N meses" / "Tutor(es)/Cotutor(es): …").

Texto de origen:

```
ANA MARIA PEREZ GOMEZ, Análisis de datos sintéticos para la evaluación de algoritmos
UNIVERSIDAD DE ANTIOQUIA Estado: Tesis en curso Doctorado en Ingeniería Electrónica, 2017.
Dirigió como: Tutor principal, Persona(s) orientada(s): Carlos Andrés Ruiz Mejía Tutor(es)/Cotutor(es): ANA MARIA PEREZ GOMEZ,
```

| Campo | Tipo | Descripción | Ejemplo |
| --- | --- | --- | --- |
| `title` | string | Texto entre el nombre del dueño y la institución, sin el punto final | "Análisis de datos sintéticos para la evaluación de algoritmos" |
| `titles[]` | array | `{title, source: "cvlac", provenance: "cvlac"}` | |
| `authors[]` | array | Personas de la tesis (ver abajo) | |
| `institution` | object | `{name, id, ror_name, ror_match}`: institución tras el título, con su ROR | `{"name": "UNIVERSIDAD DE ANTIOQUIA", "id": "03bp5hc83", "ror_name": "Universidad de Antioquia", "ror_match": "name"}` |
| `status` | string | `completed` ("Tesis concluida") u `ongoing` ("Tesis en curso"); otro valor se deja como está | `ongoing` |
| `status_text` | string | Texto original del estado | "Tesis en curso" |
| `program` | string o null | Programa, tras el estado; `null` si la página no lo da | "Doctorado en Ingeniería Electrónica" |
| `role` | string o null | "Dirigió como" | "Tutor principal", "Coturor/asesor" |
| `duration_months` | integer o null | "N meses", si aparece | |
| `year` | integer | Año de la tesis | 2017 |

**`authors[]` de una tesis**

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `full_name` | string | Nombre como en la página. |
| `type` | string | `advisor`: el dueño, si "Dirigió como" es "Tutor principal" (o falta). `co-advisor`: el dueño, si es "Cotutor/asesor", y las demás personas de "Tutor(es)/Cotutor(es)" distintas del dueño y de los estudiantes. `student`: las "Persona(s) orientada(s)". Cuando el dueño es solo cotutor, la página no dice quién fue el tutor principal y todos los demás tutores quedan como `co-advisor`. |
| `id` | string o null | COD_RH del dueño; `null` para los demás. |
| `external_ids[]` | array | El COD_RH del dueño. |
| `affiliations[]` | array | Para `advisor` y `student`: la institución de la tesis con su ROR, `years: [año]` y `cvlac.provenance: "cvlac thesis"`. El dueño como cotutor (o sin rol): las instituciones de su experiencia cuyo periodo contiene el año de la tesis, como en las obras (§16). Los demás cotutores no tienen afiliación. |

## 15. `counts`

Objeto de conteos (enteros):

| Clave | Significado |
| --- | --- |
| `works`, `projects`, `events`, `education` | Registros de cada parte. |
| `works:<sección>` | Obras por sección, p. ej. `works:Artículos`. |
| `patents` | Ítems de `patents`. |
| `<título de sección>` | Ítems de cada sección de `other_products`. |
| `endorsed_works` | Obras con la marca de verificación. |
| `works_with_affiliation` | Obras con al menos una afiliación del dueño. |
| `projects_with_affiliation` | Proyectos con al menos una afiliación del dueño. |
| `events_with_affiliation` | Eventos con al menos una afiliación del dueño en `participants`. |
| `owner_by_name_variant`, `owner_added` | Registros en que el dueño se reconoció por una forma abreviada de su nombre, o se agregó porque no estaba en la lista (§10). |
| `product_hash_repeated` | Registros cuya clave de `product_hash` ya tenía otro registro del CV y llevan un número de repetición (§21). |
| `product_hash_from_text` | Registros sin título cuyo `product_hash` se calculó con su texto (§21). |
| `products_with_affiliation` | Patentes y demás productos (sin las tesis) con al menos una afiliación del dueño. |
| `works_only_in_scienti`, `section_items_only_in_scienti`, … | Solo con `--scienti full`. |

## 16. Afiliaciones y `affiliations_from_experience`

Las afiliaciones siguen la forma de ImpactU:

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `id` | string | ROR corto; `""` o `null` si no se encontró ROR. |
| `name` | string | Nombre ROR (o el del CvLAC si no hay ROR). |
| `types[]` | array | `{source: "ror", type}`: tipos ROR, p. ej. `education`, `funder` (los únicos vistos en los cinco CV), `company`, `government`. |
| `external_ids[]` | array | `{provenance: "ror", source, id}`: `ror` (URL), `grid`, `isni`, `wikidata`, `fundref`. |
| `addresses[]` | array | `{city, country, country_code}` del registro ROR. |
| `years[]` | array de integer | En obras, proyectos, patentes y demás productos: todos los años de los periodos de experiencia. En tesis: el año de la tesis. Con SIIU: los años del proyecto en SIIU. |
| `cvlac` | object | `provenance` ("cvlac experience", "cvlac thesis" o "siiu project"), `names[]` (nombres del CvLAC), `periods[]` (`{period, dedication}`, solo experiencia), `ror_match`. |

En las obras, patentes, demás productos y eventos (salvo las tesis dirigidas como tutor, que llevan la institución de la tesis), la afiliación del dueño se calcula igual, con el año de la obra (`year_published`), del ítem (`year`, o el año de `date`) o del evento (`start`, o `end`). Sin año (casi todos los ítems de Jurado en comités de evaluación, Participación en comités de evaluación, Asesorías y Secretos empresariales, que la página publica sin fecha) o sin experiencia en ese año, el dueño queda con `affiliations: []`. Es **inferida**: significa "el dueño trabajaba allí ese año", no que el CvLAC declare dónde se hizo la obra. Con dos empleos simultáneos aparecen ambos; varias entradas de la misma institución se fusionan en una.

Un proyecto dura varios años, así que el dueño recibe las instituciones de todos los periodos de experiencia que se cruzan con el del proyecto: del año de inicio al de `end` (o de `projected_end`, o solo el de inicio). Los proyectos sin año de inicio no tienen afiliación. Si el proyecto coincide con uno de SIIU (§17), que es el sistema de la UdeA, y la experiencia no da la Universidad de Antioquia (porque el CvLAC no está al día, por ejemplo), se agrega con `cvlac.provenance: "siiu project"` y, en `years`, los años del proyecto en SIIU. En los 4.596 CvLAC de la UdeA, la regla de la experiencia da la UdeA en 3.139 de los 3.634 proyectos con código de SIIU; SIIU agrega los otros 495.

`affiliations_from_experience` resume el proceso: `ror_api`, `experience` (entradas de experiencia), `experience_with_ror`, `works_with_affiliation`, `projects_with_affiliation`, `projects_with_siiu_affiliation` (proyectos a los que SIIU agregó la UdeA), `products_with_affiliation`, `theses_with_affiliation`, `theses_owner_from_experience` (tesis en que el dueño es cotutor y su afiliación sale de la experiencia), `events_with_affiliation`, `lookup_errors`.

## 17. Coincidencias con Scienti y SIIU

**Objeto de coincidencia** (`works[].cvlac.scienti`, `projects[].scienti`, `events[].scienti`, `patents[].scienti`, `other_products.*[].scienti`):

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `id` | string | Id Scienti (`COD_RH-COD_…`). |
| `by` | string | Regla: `doi`, `title`, `title prefix` (Scienti trunca títulos largos) o, con `--scienti full`, `not on the CvLAC page`. |
| `evidence[]` | array de string | Evidencia adicional: `year`, `issn`, `isbn`, `venue`, `patent number`. |
| `shared` | boolean | `true` si el registro Scienti ya se había asignado a otra entrada (duplicados en el CvLAC). |
| `scienti_title`, `scienti_year` | string, integer | Título y año del registro Scienti. |

**Reglas de coincidencia**: (1) mismo DOI normalizado; (2) mismo título normalizado (≥ 25 caracteres y 4 palabras) más una evidencia: año, ISSN, ISBN, revista/libro/evento o número de patente; en ítems genéricos, el título Scienti debe aparecer completo en el texto; (3) un título prefijo del otro (ambos ≥ 40 caracteres) con el mismo año; (4) proyectos, eventos y redes: mismo nombre normalizado y mismo año.

**Objeto `scienti` del nivel superior**:

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `institution`, `model_year` | string | Volcado de Scienti usado (p. ej. `udea`, `2024`). Sin `--institution`, se prueba udea, univalle, uec y unaula, en ese orden. |
| `source` | string | `apis.colav.co` |
| `products`, `products_matched` | integer | Productos Scienti del COD_RH y cuántos coincidieron. |
| `matched` | object | Coincidencias por parte: `works`, `section_items`, `projects`, `events`, `networks`. |
| `records` | object | Registros Scienti recibidos: `projects`, `events`, `networks`, `patents`. |
| `rules` | string | Descripción de las reglas aplicadas. |
| `not_on_page` | object | Registros Scienti sin coincidencia, por la sección a la que pertenecerían: `works`, `patents`, `other_products` (por título de sección), `projects`, `events`, `networks` (hasta 0.6.0, patentes y demás productos se contaban juntos en `sections`). Con `--scienti full` se llama `added_from_scienti` y esos registros se agregan al JSON. |
| `not_on_page_note` | string | Explicación del campo anterior. |
| `note` | string | Solo si el COD_RH no está en ningún volcado. |

**Proyectos de SIIU** (`projects[].siiu`, objeto `siiu` del nivel superior). SIIU es el sistema de información de investigación de la UdeA. Con clave de apis.colav.co (y sin `--siiu off`), se buscan en SIIU los proyectos del dueño con el número de documento de su registro de autor de Scienti. Ese número solo se usa en la consulta: no se imprime ni se guarda. Un proyecto del CvLAC coincide con uno de SIIU cuando:

- su título normalizado es igual al nombre completo del proyecto en SIIU (o a su nombre corto, si tiene al menos 25 caracteres y 4 palabras), y
- su año de inicio cae dentro del periodo del proyecto en SIIU, con un año de margen a cada lado. El periodo va del año de registro (o del inicio de la primera etapa, si es anterior) al último fin de etapa, al año de aprobación o al registro más la duración.

Cuando varios proyectos de SIIU tienen el mismo título (propuestas presentadas de nuevo), gana el que se ejecutó (`aprobado`, `en_ejecucion`, `atrasado`, `finalizado`, `liquidado`) frente a los rechazados o en evaluación; después, el de año de inicio más cercano. Los demás quedan en `also`. El código de SIIU se agrega también a `projects[].external_ids` con `source: "siiu"`.

| Campo de `projects[].siiu` | Tipo | Descripción |
| --- | --- | --- |
| `id` | string | Código del proyecto en SIIU (`AAAA-n`). |
| `by`, `evidence[]` | string, array | `title` y `["year"]`. |
| `shared` | boolean | `true` si el proyecto de SIIU ya se había asignado a otra entrada del CvLAC. |
| `siiu_title` | string | Nombre completo en SIIU. |
| `siiu_years` | array de integer | `[primer año, último año]` del periodo usado para comparar. |
| `status` | string | Estado en SIIU (`finalizado`, `liquidado`, `en_ejecucion`, `rechazado`, `validtec`…). |
| `also` | array de string | Otros códigos de SIIU con el mismo título y un año compatible. |

| Campo del objeto `siiu` | Tipo | Descripción |
| --- | --- | --- |
| `source` | string | `apis.colav.co` |
| `projects`, `projects_matched` | integer | Proyectos de SIIU del dueño y cuántos se asignaron a un proyecto del CvLAC. |
| `not_on_page` | array de string | Códigos de SIIU que no coinciden con ningún proyecto de la página. |
| `rules` | string | Descripción de la regla. |

Si el registro de autor de Scienti no tiene documento, o el investigador no tiene proyectos en SIIU, no hay objeto `siiu`.

## 18. Diferencias con `--scienti full`

- Se agregan a `works` las obras bibliográficas que solo están en Scienti, con `id` `scienti:COD_RH-COD_PRODUCTO`, `types[]` con `source: "scienti"` y el `code` del tipo, autores en orden (`re_author_others`), revista/libro/evento, volumen y páginas, palabras clave, y `cvlac: {section, scienti}`.
- Se agregan a `patents` o a `other_products` los demás productos (a la sección cuyos ítems comparten al menos dos niveles del tipo), con el dueño como autor, a `projects` y `events` los proyectos y eventos de Scienti sin coincidencia.
- Todos los registros llevan `origin` (`"cvlac"` o `"scienti"`), y `counts` incluye `*_only_in_scienti`.
- Muchos de esos registros repiten una entrada de la página que no pasó la regla exacta (sobre todo jurados y comités): revíselos antes de contarlos como producción adicional.

## 19. Valores observados (cinco CV de la UdeA, 2026-10-28)

| | Mínimo | Máximo |
| --- | --- | --- |
| Obras | 36 | 182 |
| Proyectos | 5 | 43 |
| Eventos | 16 | 53 |
| Tesis dirigidas | 8 | 72 |
| Obras con id Scienti | 32 de 36 | 182 de 182 |

## 20. JSON-LD

Con `--format jsonld` (o `cvlac_json.to_jsonld(data, base=None)`) se obtiene el mismo JSON con `@context`, `@id` y `@type`, listo para convertirlo a RDF. Ninguna clave cambia de nombre ni de valor.

| Elemento | Valor |
| --- | --- |
| `@id` del perfil | `--base` seguido del COD_RH; sin `--base`, la URL de la página del CvLAC (`url`) |
| `@type` del perfil | `schema:ProfilePage` y `CvlacProfile` |
| `@id` de obras, proyectos, eventos, patentes e ítems de `other_products` | IRI del perfil más un JSON Pointer (RFC 6901) a su lugar en el documento: `…#/works/0`, `…#/patents/2`, `…#/other_products/Trabajos%20dirigidos~1tutor%C3%ADas/3` |
| `@type` de los registros | `works[]`: `schema:CreativeWork`; `projects[]`: `schema:ResearchProject`; `events[]`: `schema:Event`; `patents[]`: [`Patent`](#Patent) (del vocabulario). Los ítems de `other_products` no llevan tipo. |
| Vocabulario (`@vocab`) | `https://github.com/restrepo/cvlac-json/blob/main/docs/cvlac_json_esquema.md#`. Una clave sin término propio queda como ese prefijo más su nombre, y su significado es el de las tablas de este documento. |

Claves con un término de schema.org o PROV:

| Clave | Término |
| --- | --- |
| `cod_rh`, `id` | `schema:identifier` |
| `url` | `schema:url` |
| `name`, `full_name`, `title`, `profile.Nombre` | `schema:name` |
| `summary` | `schema:abstract` |
| `keywords` | `schema:keywords` |
| `authors` | `schema:author`, como lista ordenada (`@list`): el orden de la cita se conserva |
| `year_published` | `schema:datePublished` (`xsd:gYear`) |
| `doi` | `schema:sameAs`, como IRI |
| `retrieved` | `prov:generatedAtTime` (`xsd:dateTime`) |
| `profile.Nacionalidad`, `profile.Sexo` | `schema:nationality`, `schema:gender` |

- <a id="CvlacProfile"></a>`CvlacProfile` es el tipo del perfil completo que describe este documento.
- Las etiquetas de `profile` con espacios o tildes ("Nombre en citaciones", "Categoría") reciben un término propio: el prefijo del vocabulario más la etiqueta codificada (`Nombre%20en%20citaciones`).
- <a id="Patent"></a>`Patent` es el tipo de los ítems de `patents`.
- <a id="section"></a>`other_products` es un mapa índice (`@container: @index`): en RDF cada ítem lleva la propiedad `section` con el título de su sección.
- `counts` y `fields` quedan como literales JSON (`@type: @json`), porque sus claves son etiquetas abiertas de la página.
- La conversión a RDF se puede comprobar con `pyld` (`pip install pyld`, luego `pyld.jsonld.to_rdf(doc)`). Las pruebas lo hacen si está instalado (`pip install -e ".[dev]"`).

## 21. Identificador de producto: `product_hash`

Cada obra, proyecto, patente y demás producto lleva, en la entrada del dueño en `authors[]`, un `product_hash`: un identificador de 40 caracteres hexadecimales que sale solo del contenido del registro. El paquete [gruplac-json](https://github.com/restrepo/gruplac-json) calcula el mismo valor para cada integrante autor de un producto del GrupLAC, así que sirve para unir un producto del CvLAC con el mismo producto en el GrupLAC de su grupo, y para comparar dos descargas del mismo CvLAC.

**Cómo se calcula.** Es el SHA-1 de la clave

```
<título>|<COD_RH>|<tipo>|<año>
```

| Parte | Regla | Ejemplo |
| --- | --- | --- |
| título | En minúsculas, sin tildes ni otras marcas (Unicode NFKD y luego solo ASCII: "Física" → "fisica", la letra matemática "𝐽" → "j"), y solo con las letras `a`–`z` y los dígitos `0`–`9`: los espacios y la puntuación no cuentan. Un ítem sin título (sin letras ni dígitos en `title`, como las revisiones de Par evaluador) usa en su lugar su `text` (en las obras, `cvlac.text`), el texto del ítem en la página. | "Bleomicina: Una revisión" → `bleomicinaunarevision` |
| COD_RH | El de la persona, con 10 dígitos. | `0000707619` |
| tipo | `work` (producción bibliográfica, `works`), `project` (`projects`), `patent` (`patents`) u `other` (cualquier sección de `other_products`). Los eventos no tienen `product_hash`. | `work` |
| año | Obras: `year_published`. Proyectos: el año de `start`. Patentes y demás productos: `year`, o el año de `date`. Vacío si no hay. | `2024` |

Ejemplo: "Singlet Dirac dark matter streamlined", de `0000707619`, publicado en 2024, tiene la clave `singletdiracdarkmatterstreamlined|0000707619|work|2024` y el `product_hash` `efc8d0bb2fa5…` (SHA-1 de la clave en ASCII).

**Ítems sin título.** Una revisión de Par evaluador no tiene título; su `text` es, por ejemplo, "Ámbito: Internacional Par evaluador de: Material para publicación científica Revista: REVISTA DE BIOLOGIA TROPICAL, 2020, Julio", que da la clave `ambitointernacionalparevaluadordematerialparapublicacioncientificarevistarevistadebiologiatropical2020julio|0000000930|other|2020`. Así el ámbito, lo revisado, la revista o institución y el mes distinguen las revisiones de un mismo año, que antes solo se diferenciaban por `|n`. En los 4.596 CvLAC de la UdeA (2026-11-03) las repeticiones de ítems sin título bajan de 12.139 a 2.379; las que quedan tienen el mismo texto en la página. `counts.product_hash_from_text` cuenta los registros con hash calculado del texto. El texto depende de cómo escribe la página los rótulos y los meses, así que un cambio de rótulo en el CvLAC cambia esos hashes; el GrupLAC no tiene sección Par evaluador, así que no se pierde ninguna coincidencia.

**Único en el CV.** Si varios registros de la persona dan la misma clave (el mismo producto escrito dos veces, un curso dictado dos veces el mismo año, o ítems sin título con el mismo texto), el primero conserva la clave y el n-ésimo, en el orden de la página, la lleva con `|n` al final (`…|work|2024|2`). `counts.product_hash_repeated` cuenta esos registros. Así no hay dos registros con el mismo `product_hash` en un CV. El primero es el que otra fuente reproduce; uno repetido coincide solo si la otra fuente lista las mismas repeticiones en el mismo orden.

**Dónde va.** En la entrada del dueño en `authors[]` (la que tiene su COD_RH en `id`); las demás personas tienen `product_hash: null`. En un GrupLAC cada producto lista a todos los integrantes que lo firmaron, y cada uno lleva el hash calculado con su propio COD_RH: un artículo de dos integrantes tiene dos `product_hash`, uno igual al del CV de cada uno.

**Qué no lo reproduce.** El hash cambia si cambia el título (más allá de mayúsculas, tildes, espacios y puntuación), el año o el tipo. En nueve grupos de muestra, comparados con los CvLAC de sus integrantes de la UdeA (2026-11-02), el hash del GrupLAC está en el CV del integrante en 971 de 1.142 parejas de obra e integrante (85 %) y en 122 de 251 de los demás productos (49 %). Las diferencias son títulos editados en una de las dos páginas ("polychorinated" y "polychlorinated"), años distintos (frecuentes en los demás productos) y productos que no están en el CV. Los proyectos del GrupLAC no tienen autores, así que su hash no se puede calcular desde el GrupLAC. Cuando hay clave de apis.colav.co, el id de Scienti (`COD_RH-COD_PRODUCTO`, §17) identifica el registro de origen de las dos páginas y no depende del título.

**En Python.** `cvlac_json.product_hash(título, cod_rh, tipo, año=None, n=1)` da el hash; `cvlac_json.product_hash.hash_key(...)`, la clave; `cvlac_json.product_hash.product_hashes(registros, cod_rh)`, los hashes únicos de una lista de `(título, tipo, año)` en orden. El módulo `product_hash.py` solo usa la biblioteca estándar y es el mismo en gruplac-json; los casos de `tests/product_hash_vectors.json` fijan su resultado en los dos paquetes.

- A diferencia de la biblioteca `unidecode`, las letras que no tienen forma ASCII se quitan en lugar de transliterarse: "ß" y las letras griegas (𝜓) no aportan nada a la clave.
