# Comunidad del reproductor visual

Plantillas que la gente comparte para [reproductor-visual](https://github.com/Noull999/reproductor-visual): colores, fondos, plantillas hechas en el Editor y ajustes de las incluidas.

## Cómo usar una plantilla

1. En la app, abre la pestaña **Comunidad**.
2. Elige una plantilla y toca **Instalar**.

La app solo descarga desde este repositorio, revisa el archivo entero antes de usarlo y nunca ejecuta nada: una plantilla son solo datos e imágenes.

## Galería web

La carpeta `sitio/` es una página estática con todas las plantillas (se regenera sola con el catálogo). Para publicarla gratis en Vercel o Cloudflare Pages: importa este repositorio, deja el comando de build vacío y pon `sitio` como carpeta de salida (el archivo `vercel.json` ya lo indica).

## Cómo compartir la tuya

Mira [CONTRIBUIR.md](CONTRIBUIR.md). En corto: exportas desde la app, agregas tres archivos y abres un pull request. Un revisor automático comprueba que todo esté bien y yo lo apruebo.

## Cómo funciona

```
entradas/<nombre>.json       nombre, autor y descripción
plantillas/<nombre>.plantilla   el archivo que exporta la app
previas/<nombre>.webp        una captura de cómo se ve
catalogo.json                lo arma GitHub solo; no se edita a mano
```

- `herramientas/validar.py` usa los mismos revisores que la app, así que lo que pasa aquí también se puede importar allá.
- `catalogo.json` se regenera automáticamente cuando se aprueba un envío.

Las herramientas de este repositorio son [MIT](LICENSE). Cada plantilla es de su autor y la comparte para que otras personas la usen.
