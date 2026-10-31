# Cambios

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones, [versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Agregado
- Salida JSON-LD: `to_jsonld(data, base=None)` y la opción `--format jsonld` (con `--base` para el prefijo del IRI). Es el mismo documento con `@context`, `@id` y `@type`; obras, proyectos, eventos e ítems de sección son nodos con un JSON Pointer como `@id`. `pyld` se agrega a las dependencias de desarrollo para probar la conversión a RDF.

### Corregido
- DOI de las obras: se reconoce también escrito como enlace (`DOI: https://doi.org/10…`, `dx.doi.org`) o con texto antes, y se busca en el resto de la cita y en sus enlaces si no está después de "DOI:". Se quitan la puntuación y la barra finales. En una muestra de 1.000 CvLAC, las obras con DOI pasan de 2.421 a 2.611.
- Año de las obras en formatos etiquetados (libros de divulgación, de formación…): se toma de "Fecha de presentación" antes que del texto libre, que incluye el título (`Plan… al año 2050` daba 2050).

### Cambiado
- Documentación: las opciones `--format` y `--base` en el README y en el esquema, y una sección JSON-LD en el esquema (§20) con el contexto, los tipos y los `@id`.
- CI y publicación usan `actions/checkout@v7`, `actions/setup-python@v7`, `actions/upload-artifact@v7` y `actions/download-artifact@v8`.

## [0.4.0] - 2026-10-28

### Agregado
- Código de SIIU (UdeA) en los proyectos: `projects[].siiu` y `projects[].external_ids` con `source: "siiu"`, cuando el título es igual y el año compatible; resumen en el objeto `siiu` y opción `--siiu auto|off` (`siiu=` en `extract()`). Los proyectos de SIIU se buscan con el documento del registro de autor de Scienti, que no se imprime ni se guarda.
- `projects[].external_ids` también con el id de Scienti, como en las obras.

## [0.3.0] - 2026-10-28

### Agregado
- `profile.full_name`, `profile.first_names` y `profile.last_names`, como en ImpactU, separados con las partes del nombre de la página, el nombre en citaciones o la nacionalidad (`profile.name_split_by`).

## [0.2.0] - 2026-10-28

### Agregado
- Barra de progreso en la terminal (etapa, porcentaje, tiempo transcurrido), con `--no-progress` para ocultarla, y parámetro `progress` en `extract()`.

## [0.1.0] - 2026-10-28

### Agregado
- Comando `cvlac-json` y función `cvlac_json.extract()`, para Python 3.10 o superior, sin dependencias.
- Perfil, identificadores, formación, experiencia (con años y ROR), áreas, idiomas, líneas, reconocimientos, proyectos, eventos y todas las demás secciones.
- Producción bibliográfica en el esquema de obras de ImpactU, con las afiliaciones del dueño del CV según el año.
- Tesis dirigidas con título, director, codirectores, estudiantes, institución con ROR, estado y programa.
- Identificadores Scienti por DOI o título (`--scienti auto|full|off`, `--apikey`).

[Sin publicar]: https://github.com/restrepo/cvlac-json/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/restrepo/cvlac-json/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/restrepo/cvlac-json/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/restrepo/cvlac-json/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/restrepo/cvlac-json/releases/tag/v0.1.0
