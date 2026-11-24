# Compartir una plantilla

## 1. Exporta desde la app

- **Una plantilla hecha en el Editor:** en la Biblioteca, elígela y toca **Exportar**.
- **Tus ajustes de una plantilla incluida** (tu color, tu fondo, tu cuerpo de Headspace…): toca **Exportar mis ajustes**.

Te queda un archivo `.plantilla`.

## 2. Saca una captura

Abre tu plantilla en la app y guarda una captura de pantalla. Tiene que ser:

- **WebP**, en proporción **16:9** (por ejemplo 1000×563), de al menos 480×270 y de menos de 600 KB.
- Sin partes de otras personas (fotos, portadas de discos) que no puedas compartir.

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

## 4. Abre un pull request

Un revisor automático comprueba tu envío con las mismas reglas de la app. Si falla, te dice qué corregir. Cuando pasa, lo reviso y lo apruebo; el catálogo se actualiza solo.

## Reglas

- Un envío solo **agrega** esos tres archivos: no se toca nada más.
- Comparte solo lo que puedas compartir: nada de portadas de discos, skins de terceros ni imágenes con derechos ajenos.
- Al enviarla, aceptas que otras personas la usen y la instalen desde la app.
- Puedo rechazar o retirar una plantilla si no cumple las reglas.
