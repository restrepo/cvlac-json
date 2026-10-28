# Publicar en PyPI

Este repositorio publica el paquete **cvlac-json** en [PyPI](https://pypi.org) con GitHub Actions, cada vez que se sube una etiqueta de versión (`v0.1.0`, `v0.2.0`…).

## Primera vez: orden de los pasos

1. Cree en GitHub un repositorio **vacío** llamado `cvlac-json` (sin README ni licencia: ya están aquí), por ejemplo con `gh repo create restrepo/cvlac-json --public`.
2. Si el repositorio queda en otra cuenta que no sea `restrepo`, cambie `restrepo` en las URL de `pyproject.toml`, `README.md` y este archivo, y haga commit.
3. Suba **solo la rama** `main`, todavía sin la etiqueta:

   ```bash
   git remote add origin git@github.com:restrepo/cvlac-json.git
   git push -u origin main
   ```

4. Configure PyPI y el environment de GitHub (sección siguiente).
5. Recién entonces suba la etiqueta, que es lo que dispara la publicación: `git push origin v0.1.0`.

Si sube la etiqueta antes del paso 4, el job `publish-pypi` falla sin publicar nada; vuelva a lanzarlo desde **Actions → Release → Re-run jobs** cuando haya terminado la configuración.

## Dónde van las credenciales de PyPI

**En ningún archivo del repositorio.** Ni en `pyproject.toml`, ni en los workflows, ni en un `.pypirc` o `.env`: todo lo que se sube a GitHub queda en el historial, aunque luego se borre.

Hay dos formas de autorizar la publicación. Use la primera.

### Opción A (recomendada): Trusted Publishing, sin contraseñas ni tokens

PyPI confía directamente en el workflow `release.yml` de este repositorio, mediante OpenID Connect. No hay ningún secreto que guardar, copiar ni rotar.

**1. En PyPI** (una sola vez, antes de la primera publicación):

1. Entre a <https://pypi.org/manage/account/publishing/> con su cuenta (créela en <https://pypi.org/account/register/> si no tiene, y active la autenticación de dos factores).
2. En **"Add a new pending publisher"**, pestaña **GitHub**, llene:

   | Campo | Valor |
   | --- | --- |
   | PyPI Project Name | `cvlac-json` |
   | Owner | `restrepo` (el usuario de GitHub dueño del repositorio) |
   | Repository name | `cvlac-json` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

3. Pulse **Add**. El proyecto se crea en PyPI con la primera publicación.

**2. En GitHub** (una sola vez):

1. En el repositorio: **Settings → Environments → New environment**, nombre `pypi`.
2. Recomendado: en ese environment, active **Required reviewers** y póngase usted, para aprobar cada publicación antes de que salga. En **Deployment branches and tags**, limite a etiquetas `v*`.

Eso es todo: el job `publish-pypi` de `.github/workflows/release.yml` ya tiene `environment: pypi` y `permissions: id-token: write`, que es lo que PyPI verifica.

**Opcional, TestPyPI** (para ensayar sin tocar el PyPI real): repita los dos pasos en <https://test.pypi.org/manage/account/publishing/> (otra cuenta, en test.pypi.org) con **Workflow name** `testpypi.yml` y **Environment name** `testpypi`, y cree en GitHub el environment `testpypi`. Luego, en **Actions → TestPyPI → Run workflow**.

### Opción B: token de API guardado como secreto de GitHub

Úsela solo si no puede usar Trusted Publishing.

1. En PyPI: **Account settings → API tokens → Add API token**. Para la primera publicación el alcance tiene que ser "Entire account"; después de publicar, bórrelo y cree uno limitado al proyecto `cvlac-json`.
2. Copie el token (empieza por `pypi-`). PyPI lo muestra una sola vez.
3. En GitHub: **Settings → Secrets and variables → Actions → New repository secret**:
   - Name: `PYPI_API_TOKEN`
   - Secret: el token
   (Mejor aún: créelo como secreto del environment `pypi`, en **Settings → Environments → pypi → Add environment secret**, para que solo el job de publicación lo vea.)
4. En `.github/workflows/release.yml`, en el paso `pypa/gh-action-pypi-publish`, quite el comentario de las dos líneas:

   ```yaml
   with:
     password: ${{ secrets.PYPI_API_TOKEN }}
   ```

GitHub nunca muestra el valor de un secreto, ni siquiera en los registros de Actions (aparece como `***`).

## Publicar una versión

La versión sale de la etiqueta de git (con `hatch-vcs`): no hay que editarla en ningún archivo.

1. Actualice `CHANGELOG.md` (mueva lo de "Sin publicar" a una sección con el número y la fecha) y haga commit en `main`.
2. Compruebe que el workflow **CI** pasa en `main`.
3. Cree y suba la etiqueta:

   ```bash
   git tag -a v0.1.0 -m "cvlac-json 0.1.0"
   git push origin v0.1.0
   ```

4. En **Actions → Release** verá tres jobs: `build` (construye y revisa el paquete y que la versión coincida con la etiqueta), `publish-pypi` (sube a PyPI; espera su aprobación si activó *Required reviewers*) y `github-release` (crea la página de la versión en GitHub con los archivos).
5. Pruebe la instalación:

   ```bash
   pip install --upgrade cvlac-json
   cvlac-json --version
   ```

Una versión publicada en PyPI no se puede reemplazar: si algo sale mal, publique la siguiente (`v0.1.1`).

## Probar el paquete en local antes de publicar

```bash
python -m pip install build twine
python -m build               # crea dist/cvlac_json-*.whl y dist/cvlac_json-*.tar.gz
python -m twine check --strict dist/*
python -m pip install dist/*.whl && cvlac-json --version
```
