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

- **Los mismos campos en todos los registros de una colección.** En `works`, `projects`, `events`, `experience`, cada lista de `education` y cada lista de `sections`, si un campo tiene valor en algún registro, aparece en todos: vale `[]` (listas) o `null` (lo demás) donde no hay dato. Lo mismo dentro de los objetos anidados (`source`, `cvlac`, `authors[]`, `affiliations[]`…).
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
| Producto Scienti | `COD_RH-COD_PRODUCTO` | `0000000001-20912` | `works[].external_ids`, `works[].cvlac.scienti.id`, `sections.*[].scienti.id` |
| Proyecto Scienti | `COD_RH-COD_PROYECTO` | `0000000001-1` | `projects[].scienti.id`, `projects[].external_ids` |
| Proyecto SIIU (UdeA) | `AAAA-n` | `2014-361` | `projects[].siiu.id`, `projects[].external_ids` |
| Evento Scienti | `COD_RH-COD_EVENTO` | `0000000001-4` | `events[].scienti.id` |
| Red Scienti | `COD_RH-COD_RED` | | `sections["Redes de conocimiento especializado"][].scienti.id` |
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
| `sections` | object | Las demás secciones del CV, por título (§13); las tesis dirigidas tienen campos estructurados (§14). |
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
| `participants[]` | array | `{name, role}` | `{"name": "ANA MARIA PEREZ GOMEZ", "role": "Ponente"}` |
| `scienti` | object o null | Coincidencia con un evento Scienti (§17) | |

## 13. `sections`: demás secciones

Objeto cuyas claves son los títulos de sección del CvLAC y cuyos valores son listas de ítems genéricos. Secciones vistas en los cinco CV: Trabajos dirigidos/tutorías, Jurado en comités de evaluación, Participación en comités de evaluación, Par evaluador, Cursos de corta duración, Consultorías, Informes de investigación, Informes técnicos, Demás trabajos, Fortalecimiento o solución de asuntos de interés social, Redes de conocimiento especializado, Estancias posdoctorales, Patentes, Secretos empresariales, Prototipos, Planta piloto, Softwares, Signos distintivos, Nuevos registros científicos, Innovación de proceso o procedimiento.

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `type` | string | Tipo de producto del CvLAC, niveles separados por " - " (p. ej. "Producción técnica - Cursos de corta duración dictados - Extensión extracurricular"). Falta si toda la sección lo tiene vacío. |
| `endorsed` | boolean | Marca de verificación. |
| `text` | string | Texto completo del ítem. |
| `fields` | object o null | Pares etiqueta → valor (`Finalidad`, `Institución`, `Nombre comercial`, `contrato/registro`…). |
| `keywords[]`, `areas[]`, `sectors[]` | array de string | Palabras, áreas y sectores del ítem. |
| `links[]` | array | Enlaces del ítem; no aparece en los cinco CV de prueba. |
| `year` | integer o null | Año detectado en el texto. |
| `scienti` | object o null | Coincidencia con un producto o red Scienti (§17). Los pares evaluadores no son productos Scienti y no tienen id. |
| `origin` | string | Solo con `--scienti full`. |

## 14. Tesis dirigidas: `sections["Trabajos dirigidos/tutorías"][]`

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
| `affiliations[]` | array | Para `advisor` y `student`: la institución de la tesis con su ROR, `years: [año]` y `cvlac.provenance: "cvlac thesis"`. Los cotutores no tienen afiliación. |

## 15. `counts`

Objeto de conteos (enteros):

| Clave | Significado |
| --- | --- |
| `works`, `projects`, `events`, `education` | Registros de cada parte. |
| `works:<sección>` | Obras por sección, p. ej. `works:Artículos`. |
| `<título de sección>` | Ítems de cada sección de `sections`. |
| `endorsed_works` | Obras con la marca de verificación. |
| `works_with_affiliation` | Obras con al menos una afiliación del dueño. |
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
| `years[]` | array de integer | En obras: todos los años de los periodos de experiencia. En tesis: el año de la tesis. |
| `cvlac` | object | `provenance` ("cvlac experience" o "cvlac thesis"), `names[]` (nombres del CvLAC), `periods[]` (`{period, dedication}`, solo experiencia), `ror_match`. |

En las obras, la afiliación es **inferida**: significa "el dueño trabajaba allí ese año", no que el CvLAC declare dónde se hizo la obra. Con dos empleos simultáneos aparecen ambos; varias entradas de la misma institución se fusionan en una.

`affiliations_from_experience` resume el proceso: `ror_api`, `experience` (entradas de experiencia), `experience_with_ror`, `works_with_affiliation`, `theses_with_affiliation`, `lookup_errors`.

## 17. Coincidencias con Scienti y SIIU

**Objeto de coincidencia** (`works[].cvlac.scienti`, `projects[].scienti`, `events[].scienti`, `sections.*[].scienti`):

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
| `not_on_page` | object | Registros Scienti sin coincidencia, por la sección a la que pertenecerían: `works`, `sections` (por título), `projects`, `events`, `networks`. Con `--scienti full` se llama `added_from_scienti` y esos registros se agregan al JSON. |
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
- Se agregan a `sections` los demás productos (a la sección cuyos ítems comparten al menos dos niveles del tipo), a `projects` y `events` los proyectos y eventos de Scienti sin coincidencia.
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
| `@id` de obras, proyectos, eventos e ítems de `sections` | IRI del perfil más un JSON Pointer (RFC 6901) a su lugar en el documento: `…#/works/0`, `…#/sections/Trabajos%20dirigidos~1tutor%C3%ADas/3` |
| `@type` de los registros | `works[]`: `schema:CreativeWork`; `projects[]`: `schema:ResearchProject`; `events[]`: `schema:Event`. Los ítems de `sections` no llevan tipo. |
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
- <a id="section"></a>`sections` es un mapa índice (`@container: @index`): en RDF cada ítem lleva la propiedad `section` con el título de su sección.
- `counts` y `fields` quedan como literales JSON (`@type: @json`), porque sus claves son etiquetas abiertas de la página.
- La conversión a RDF se puede comprobar con `pyld` (`pip install pyld`, luego `pyld.jsonld.to_rdf(doc)`). Las pruebas lo hacen si está instalado (`pip install -e ".[dev]"`).
