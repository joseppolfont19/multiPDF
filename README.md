# multiPDF
Conversión por lotes de imágenes digitalizadas a PDF verificado, con marcadores y control de integridad página a página.


# archive-pdf-toolkit

Conversión por lotes de imágenes digitalizadas a PDF verificado, con marcadores
y control de integridad página a página.

> **En el Archivo Diocesano de Mallorca digitalizamos más de 400 libros cada año y necesitamos una herramienta que se adapte a nosotros para un mejor funcionamiento. Para ello, creamos este programa sencillo, en cual nos permite satisfacer todas nuestras demandas. En primer lugar, un programa de software libre y sin coste alguno. En segundo lugar, un programa modificable a los requisitos que tenemos en materia de presentación de los libros digitalizados (equipos antiguos con Ubuntu y poca memoria RAM, necesidad de respetar el foliado de los libros con verso y reverso, compresión disponible sin perder calidad y creación de pdfs de manera masiva)**
---
> *Antes de la creación de este script, se utilizaba una versión antigua de Adobe que no aceptaba según qué numeros de imágenes para procesar (algunos libros tienen más de 2000 imágenes) y la compresión afectaba mucho a la calidad de las imágenes. La mejora principal fue el hecho de poder ejecutar la creación de todos los documentos PDF a la vez, ya que el programa navega por las carpetas del directorio seleccionado, sabe como montar el PDF respetando las carpetas que nosotros creams R (recto) y V (verso) y el órden de enumeración de Windows en carpeta. El programa acaba poniendo el nombre de la carpeta principal en la que se encuentran las fotos y sigue con el siguiente. El tiempo ahorrado es incalculable.*

---

## El problema

Digitalizar un fondo documental produce miles de imágenes sueltas repartidas en
una jerarquía de carpetas. Convertirlas en documentos consultables plantea tres
problemas que las herramientas genéricas no resuelven:

1. **Orden.** `10.jpg` va después de `9.jpg`, no antes. Un PDF mal ordenado es
   una reproducción defectuosa del original.
2. **Escala.** Un lote de 20.000 imágenes no cabe en memoria. Cargarlas todas
   agota la RAM de la estación de trabajo a mitad del proceso.
3. **Integridad.** Una página perdida en silencio es peor que un fallo. Si el
   PDF sale con 898 páginas de 900, nadie lo detecta hasta años después.

## Cómo los resuelve

| Problema | Solución |
|---|---|
| Orden | Clave de ordenación natural que entiende numeración compuesta (`12-15`) |
| Escala | Procesado por *chunks*: la memoria depende del tamaño del bloque, no del lote |
| Integridad | *Safe Mode*: verificación página a página, un reintento por bloque, y validación del PDF final |
| Saturación | *Backpressure*: el proceso espera si la CPU o la RAM superan el umbral |
| Interrupciones | Idempotencia: un PDF ya generado no se rehace, así que basta relanzar |
| Recto/verso | Las carpetas `R/` y `V/` de un mismo documento se entrelazan por orden natural |
| Consulta | Marcadores generados desde el nombre de fichero, que en un archivo es metadato |

## Instalación

```bash
git clone https://github.com/<usuario>/archive-pdf-toolkit.git
cd archive-pdf-toolkit
pip install -e ".[gui,dev]"     # sin el extra 'gui' solo se instala la CLI
```

## Uso

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

Códigos de salida: `0` correcto, `1` terminado con errores por carpeta,
`2` fallo. Aptos para `cron`, CI o cualquier planificador.

### Interfaz gráfica

```bash
python -m archivepdf
```

Tres pestañas: **Convertidor** (conversión estándar), **Optimitzador**
(compresión con recomendación automática) y **Rotar** (rotación por página con
vista previa). La interfaz consume exactamente el mismo núcleo que la CLI.

### Manifiesto de ejecución

`--report` acumula una fila por ejecución en un CSV: imágenes, MB de origen y
de destino, ratio de compresión, PDFs generados, errores y duración. Es la
materia prima para analizar después qué preset funciona mejor según el tipo de
fondo documental.

## Arquitectura

```
src/archivepdf/
├── config.py            # constantes y perfiles de conversión (ConversionConfig)
├── exceptions.py        # errores de dominio
├── logging_setup.py     # el núcleo registra; no abre diálogos
├── paths.py             # localización de recursos (PyInstaller / código fuente)
├── cli.py               # interfaz de línea de comandos
├── core/                # lógica de dominio: sin GUI, sin diálogos, testeable
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

La regla que sostiene todo: **`core/` no importa nada de `gui/`**. El núcleo
lanza excepciones y emite logs; cada front-end decide cómo informar. Por eso el
mismo código puede ejecutarse en un test, en un contenedor o en un cron.

## Desarrollo

```bash
pytest                    # suite completa
pytest --cov=archivepdf   # con cobertura
ruff check src tests      # análisis estático
```

## Decisiones y limitaciones conocidas

Documentadas en [`docs/architecture.md`](docs/architecture.md), incluyendo el
uso simultáneo de `pypdf` y `PyMuPDF` y el valor de calidad heredado del perfil
estándar.

## Licencia

MIT
