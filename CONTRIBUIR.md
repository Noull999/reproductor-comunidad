# Compartir una plantilla

## 1. Exporta desde la app

- **Una plantilla hecha en el Editor:** en la Biblioteca, elígela y toca **Exportar**.
- **Tus ajustes de una plantilla incluida** (tu color, tu fondo, tu cuerpo de Headspace…): toca **Exportar mis ajustes**.

Te queda un archivo `.plantilla`. No lleva tus cuentas, tus canciones ni tus tokens.

## 2. Saca una captura

La captura tiene que ser:

- **WebP**, en proporción **16:9** (por ejemplo 1000×563), de al menos 480×270 y de menos de 600 KB.
- Tomada desde la **vista previa de la Biblioteca**, que usa música inventada. **No uses una captura con tu música real**: podría mostrar tus canciones, tu lista de «me gusta», tu nombre o carátulas de discos que no puedes compartir.

## 3. Agrega tres archivos con el mismo nombre

Elige un nombre corto con minúsculas, números y guiones (máx. 40), por ejemplo `neoy2k-magenta`:

| Archivo | Qué es |
|---|---|
| `plantillas/neoy2k-magenta.plantilla` | el archivo que exportaste (máx. 10 MB) |
| `previas/neoy2k-magenta.webp` | tu captura |
| `entradas/neoy2k-magenta.json` | los datos de abajo |

```json
{
 "nombre": "Neo Y2K magenta",
 "autor": "tu nombre o usuario",
 "descripcion": "Una frase corta sobre cómo se ve."
}
```

Nombre: máx. 40 caracteres. Autor: máx. 30. Descripción: máx. 200.

### Si tu archivo trae imágenes (un fondo o un cuerpo propio)

Hay que decir de dónde vienen, agregando el campo `imagenes` a la entrada:

```json
{
 "nombre": "Winamp neón",
 "autor": "tu nombre o usuario",
 "descripcion": "Un fondo oscuro con luces de neón.",
 "imagenes": { "origen": "propio" }
}
```

| `origen` | Cuándo | `detalle` |
|---|---|---|
| `propio` | Lo hiciste tú (dibujo, foto tuya, código) | opcional |
| `ia` | Lo generó una IA | **obligatorio**: con qué herramienta |
| `libre` | De un banco de imágenes o con licencia libre | **obligatorio**: la fuente y la licencia, por ejemplo `CC0 · pexels.com` (máx. 120 caracteres) |

Si tu archivo trae imágenes y no lo declaras, el revisor rechaza el envío. Y si lo declaras sin traer imágenes, también. La galería muestra esa información en cada tarjeta.

## 4. Abre un pull request

Un revisor automático comprueba tu envío con las mismas reglas de la app. Si falla, te dice qué corregir. Cuando pasa, lo reviso y lo apruebo; el catálogo se actualiza solo.

El **autor verificado** es tu usuario de GitHub, el que abrió el pull request. Se muestra junto al nombre que pongas en `autor`, que puede ser el que prefieras.

## Reglas

- Un envío solo **agrega** esos tres archivos: no se toca nada más.
- Comparte solo lo que puedas compartir: nada de portadas de discos, skins de terceros ni imágenes con derechos ajenos.
- Al enviarla, aceptas que otras personas la usen y la instalen desde la app.
- Puedo rechazar o retirar una plantilla si no cumple las reglas o si alguien reclama derechos sobre ella.
