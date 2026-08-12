# multiPDF

Conversión por lotes de imágenes digitalizadas a PDF verificado, con marcadores y control de integridad página a página.

> En el Archivo Diocesano de Mallorca digitalizamos más de 400 libros al año, algunos de ellos con más de 2.000 imágenes. Necesitábamos una herramienta adaptada a nuestro flujo de trabajo real: software libre y sin coste, capaz de funcionar en equipos antiguos con Ubuntu y poca memoria RAM, que respetara el foliado de recto y verso, comprimiera sin degradar la calidad y generara los PDF de forma masiva.
>
> Hasta entonces usábamos una versión antigua de Adobe que no admitía lotes grandes de imágenes y cuya compresión afectaba mucho a la calidad. La mejora principal de este programa es poder montar todos los documentos de una sola pasada: recorre el directorio seleccionado, ensambla cada PDF respetando las carpetas `R` (recto) y `V` (verso) y el orden de numeración del sistema, y nombra el archivo resultante según la carpeta que lo contiene antes de pasar al siguiente. El tiempo ahorrado es incalculable.

---

## El problema

Digitalizar un fondo documental produce miles de imágenes sueltas repartidas en una jerarquía de carpetas. Convertirlas en documentos consultables plantea tres problemas que las herramientas genéricas no resuelven:

1. **Orden.** `10.jpg` va después de `9.jpg`, no antes. Un PDF mal ordenado es una reproducción defectuosa del original.
2. **Escala.** Un lote de 20.000 imágenes no cabe en memoria. Cargarlas todas agota la RAM de la estación de trabajo a mitad del proceso.
3. **Integridad.** Una página perdida en silencio es peor que un fallo. Si el PDF sale con 898 páginas de 900, nadie lo detecta hasta años después.

## Cómo los resuelve

| Problema | Solución |
|---|---|
| Orden | Clave de ordenación natural que entiende numeración compuesta (`12-15`) |
| Escala | Procesado por *chunks*: la memoria depende del tamaño del bloque, no del lote |
| Integridad | *Safe Mode*: verificación página a página, un reintento por bloque y validación del PDF final |
| Saturación | *Backpressure*: el proceso espera si la CPU o la RAM superan el umbral |
| Interrupciones | Idempotencia: un PDF ya generado no se rehace, así que basta relanzar |
| Recto/verso | Las carpetas `R/` y `V/` de un mismo documento se entrelazan por orden natural |
| Consulta | Marcadores generados desde el nombre de fichero, que en un archivo es metadato |

## Instalación

Requiere Python 3.10 o superior.

```bash
git clone https://github.com/joseppolfont19/multiPDF.git
cd multiPDF
pip install -e ".[gui]"     # sin el extra 'gui' solo se instala la CLI
```

## Uso

### Interfaz gráfica

```bash
python -m archivepdf
```

Tres pestañas: **Convertidor** (conversión estándar), **Optimitzador** (compresión con recomendación automática según el peso del lote) y **Rotar** (rotación por página con vista previa). La interfaz consume exactamente el mismo núcleo que la línea de comandos.

### Línea de comandos

```bash
# Analizar un lote y obtener ajustes recomendados, sin escribir nada
archivepdf scan ./Fons_Parroquial

# Conversión estándar de todo el árbol de carpetas
archivepdf convert ./Fons_Parroquial

# PDF comprimido aplicando la recomendación automática
archivepdf compress ./Fons_Parroquial --auto --report ejecuciones.csv

# Parámetros manuales
archivepdf compress ./Fons_Parroquial --dpi 96 --quality 50 --scale 75

# Rotar páginas concretas de un PDF ya generado
archivepdf rotate documento.pdf --angle 90 --pages 3 4 5
```

Códigos de salida: `0` correcto, `1` terminado con errores por carpeta, `2` fallo. Aptos para `cron` o cualquier planificador.

### Manifiesto de ejecución

`--report` acumula una fila por ejecución en un CSV: imágenes procesadas, MB de origen y de destino, ratio de compresión, PDF generados, errores y duración. Sirve para analizar después qué ajustes funcionan mejor según el tipo de fondo documental.

## Arquitectura

```
src/archivepdf/
├── config.py            # constantes y perfiles de conversión (ConversionConfig)
├── exceptions.py        # errores de dominio
├── logging_setup.py     # el núcleo registra; no abre diálogos
├── paths.py             # localización de recursos (PyInstaller / código fuente)
├── cli.py               # interfaz de línea de comandos
├── core/                # lógica de dominio: sin GUI, sin diálogos
│   ├── discovery.py     # búsqueda de imágenes y ordenación natural
│   ├── conversion.py    # pipeline por chunks, Safe Mode y recorrido del árbol
│   ├── compression.py   # heurísticas de recomendación
│   ├── bookmarks.py     # generación del índice del PDF
│   ├── rotation.py      # sesión de rotación sin dependencia de interfaz
│   └── resources.py     # backpressure de CPU/RAM
└── gui/                 # front-end de escritorio (CustomTkinter)
    ├── theme.py         # sistema visual
    ├── assets.py        # carga del logo
    ├── app.py           # ventana, navegación, cabecera y pie
    └── tabs/            # una pestaña por módulo
```

La regla que sostiene todo: **`core/` no importa nada de `gui/`**. El núcleo lanza excepciones y emite registros de log; cada front-end decide cómo informar al usuario. Por eso el mismo código puede ejecutarse desde la interfaz gráfica, desde un script o desde una tarea programada.

## Dependencias

| Biblioteca | Uso |
|---|---|
| Pillow | Lectura de imágenes, escalado y generación de los bloques PDF |
| pypdf | Operaciones estructurales: fusión de bloques, conteo de páginas, marcadores |
| psutil | Lectura de CPU y RAM para el control de saturación |
| PyMuPDF | Rasterizado de la vista previa y rotación (opcional, extra `gui`) |
| CustomTkinter | Interfaz de escritorio (opcional, extra `gui`) |

## Estado del proyecto

Este repositorio contiene el código de la aplicación. La suite de tests y la documentación de decisiones de arquitectura forman parte del proyecto y se publicarán más adelante.

## Licencia

MIT
