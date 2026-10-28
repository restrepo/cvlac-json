# Cambios

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones, [versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

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

[Sin publicar]: https://github.com/restrepo/cvlac-json/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/restrepo/cvlac-json/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/restrepo/cvlac-json/releases/tag/v0.1.0
