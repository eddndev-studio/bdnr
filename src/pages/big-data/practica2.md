---
layout: ../../layouts/Layout.astro
title: "Big Data - Práctica 2: Introducción a Apache Spark"
---

[Volver al índice de Big Data](/#big-data) · [Práctica 1: Limpieza de datos](/big-data/practica1/)

# Práctica 2: Introducción a Apache Spark

**Asignatura:** C703 · Big Data / Big Data  
**Alumno:** Eduardo Alonso Sánchez · **Boleta:** 2023630155  
**Grupo:** 7CV4 · **Docente:** Tania Rodríguez Sarabia · **Periodo:** 20271

[Descargar reporte PDF](/big-data/practica2/bd-02-introduccion-apache-spark.pdf) · [Script de análisis](/big-data/practica2/scripts/analisis_censo.py) · [CSV de ocupaciones](/big-data/practica2/resultados/Reporte_Ocupaciones_Eduardo_Alonso_Sanchez/ocupaciones.csv)

## 1. Objetivo y conjunto de datos

El objetivo fue ejecutar un flujo básico de Apache Spark: cargar un CSV con tipos inferidos, explorar su esquema y cantidad de filas, aplicar filtros y agrupaciones, y exportar una tabla de resultados. Utilicé la [copia de Adult Income indicada para la práctica](https://github.com/saravrajavelu/Adult-Income-Analysis/blob/master/adult.csv).

[UCI describe Adult](https://archive.ics.uci.edu/dataset/2/adult) como un conjunto de datos usado para estudiar si los ingresos anuales superan 50,000 dólares. En esta práctica realicé un análisis descriptivo de ocupaciones, horas semanales y país de origen. No entrené un modelo de clasificación ni extrapolé los resultados a una población.

El archivo tiene **48,842 registros, 15 columnas y 5,326,368 bytes**. La huella SHA-256 de la entrada es:

```text
1f13ee2bf9d7c66098429281ab91fa1b51cbabd3b805cc365b3c6b44491ea2c0
```

## 2. Entorno y carga del CSV

La ejecución guardada usó **PySpark 4.2.0 en modo local de dos núcleos**, con una sesión llamada `Análisis Censo`. Los cálculos se realizaron mediante DataFrames de Spark. Esta ejecución permite practicar sus operaciones, pero no mide el rendimiento de un clúster distribuido.

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = (
    SparkSession.builder.appName("Análisis Censo")
    .master("local[2]")
    .config("spark.sql.shuffle.partitions", "2")
    .getOrCreate()
)
census = spark.read.csv(str(SOURCE), header=True, inferSchema=True)
census.printSchema()
total = census.count()
```

`header=True` usa la primera línea como encabezado e `inferSchema=True` permite inferir los tipos. La salida registró:

```text
root
 |-- age: integer (nullable = true)
 |-- workclass: string (nullable = true)
 |-- fnlwgt: integer (nullable = true)
 |-- education: string (nullable = true)
 |-- educational-num: integer (nullable = true)
 |-- marital-status: string (nullable = true)
 |-- occupation: string (nullable = true)
 |-- relationship: string (nullable = true)
 |-- race: string (nullable = true)
 |-- gender: string (nullable = true)
 |-- capital-gain: integer (nullable = true)
 |-- capital-loss: integer (nullable = true)
 |-- hours-per-week: integer (nullable = true)
 |-- native-country: string (nullable = true)
 |-- income: string (nullable = true)

Total de registros: 48842
```

Seis campos quedaron como enteros y nueve como texto. `hours-per-week` quedó numérico, lo que permitió calcular su promedio sin una conversión manual. El script comprueba que existan las cuatro columnas necesarias para las consultas antes de continuar.

## 3. Las diez ocupaciones más frecuentes

Agrupé por `occupation`, conté los registros y ordené por frecuencia descendente. Para resolver empates usé el nombre de la categoría en orden alfabético. Después limité la salida a diez filas.

```python
top_occupations = (
    census.groupBy("occupation")
    .count()
    .orderBy(F.desc("count"), F.asc("occupation"))
    .limit(10)
)
top_occupations.show(10, truncate=False)
```

| Ocupación | Registros |
| --- | ---: |
| Prof-specialty | 6,172 |
| Craft-repair | 6,112 |
| Exec-managerial | 6,086 |
| Adm-clerical | 5,611 |
| Sales | 5,504 |
| Other-service | 4,923 |
| Machine-op-inspct | 3,022 |
| ? | 2,809 |
| Transport-moving | 2,355 |
| Handlers-cleaners | 2,072 |

`Prof-specialty` encabeza la lista. La diferencia con la tercera categoría es de 86 registros. El símbolo `?` aparece en 2,809 filas y no identifica una profesión. Lo conservé como etiqueta literal para mantener el conteo del archivo cargado; esta práctica no incluyó una etapa de limpieza.

## 4. Promedio de horas semanales por género

Agrupé por el campo `gender` y calculé la media de `hours-per-week`. También conté los registros con horas para dejar visible el tamaño de cada grupo.

```python
hours_by_gender = (
    census.groupBy("gender")
    .agg(
        F.count("hours-per-week").alias("registros_con_horas"),
        F.avg("hours-per-week").alias("horas_promedio"),
    )
    .orderBy("gender")
)
hours_by_gender.show(truncate=False)
```

| Valor de gender | Registros con horas | Promedio de horas semanales |
| --- | ---: | ---: |
| Female | 16,192 | 36.4006916996 |
| Male | 32,650 | 42.4168453292 |

En los registros del archivo, el promedio de `Male` supera al de `Female` por aproximadamente **6.02 horas semanales**. La comparación describe las medias calculadas; por sí sola no explica sus causas.

## 5. Registros con país de origen México

El filtro comparó exactamente `native-country` con `Mexico` y devolvió **951 filas**. El script mostró las primeras veinte en consola, sin agregar un criterio de ordenamiento.

```python
mexico = census.filter(F.col("native-country") == "Mexico")
mexico_total = mexico.count()
mexico.select(
    "age", "workclass", "education", "occupation", "gender",
    "hours-per-week", "native-country", "income"
).show(20, truncate=False)
```

La siguiente tabla reproduce cinco registros mostrados en la ejecución conservada. En los cinco, `workclass` fue `Private`, `native-country` fue `Mexico` e `income` fue `<=50K`.

| Edad | Estudios | Ocupación | Género | Horas semanales |
| ---: | --- | --- | --- | ---: |
| 39 | 7th-8th | Craft-repair | Male | 40 |
| 38 | 9th | Exec-managerial | Male | 54 |
| 30 | HS-grad | Machine-op-inspct | Male | 40 |
| 21 | 5th-6th | Machine-op-inspct | Male | 38 |
| 52 | 1st-4th | Machine-op-inspct | Male | 40 |

La columna registra país de origen. Este filtro no permite inferir residencia actual, nacionalidad legal ni historia migratoria. Los veinte registros completos aparecen en el [registro de ejecución](/big-data/practica2/resultados/ejecucion.txt).

## 6. Exportación de resultados

Guardé la tabla de ocupaciones con encabezado y una sola partición de salida. La carpeta conserva mi nombre completo, como en la ejecución original.

```python
(
    top_occupations.coalesce(1)
    .write.mode("overwrite")
    .option("header", True)
    .csv(str(OCCUPATIONS_DIR))
)
```

Spark escribió un directorio con un archivo `part-*.csv` y archivos de control. Para su descarga en este sitio, la pieza de datos se ofrece como [ocupaciones.csv](/big-data/practica2/resultados/Reporte_Ocupaciones_Eduardo_Alonso_Sanchez/ocupaciones.csv), conservando su contenido. El resumen JSON registra la versión de Spark, el esquema, los conteos y la huella del CSV de entrada.

| Comprobación de la ejecución | Resultado |
| --- | ---: |
| Registros cargados | 48,842 |
| Columnas | 15 |
| Ocupación más frecuente | Prof-specialty: 6,172 |
| Filas con ocupación ? | 2,809 |
| País de origen Mexico | 951 |
| Filas del CSV de ocupaciones | 10 |

La verificación conservada en el espacio de trabajo recalculó estos conteos y promedios con la biblioteca estándar de Python y obtuvo los mismos valores. El CSV exportado coincide fila por fila con las ocupaciones del resumen JSON.

## 7. Reproducción y evidencias

El [script completo](/big-data/practica2/scripts/analisis_censo.py) usa rutas relativas a su propia ubicación. Para ejecutarlo, prepara este árbol, descarga la entrada desde el repositorio citado y conserva sus nombres:

```text
practica2/
├── requirements.txt
├── scripts/
│   └── analisis_censo.py
├── datos/
│   └── raw/
│       └── adult.csv
└── resultados/  (se genera al ejecutar)
```

Con Python y Java compatibles con PySpark, instala las [dependencias](/big-data/practica2/requirements.txt) y ejecuta desde `practica2/`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/analisis_censo.py
```

El script imprime el esquema, el total de registros, las ocupaciones, los promedios y veinte filas del filtro de México. Después genera el resumen y el directorio CSV. Las acciones `count()`, `show()` y la escritura materializan resultados a partir de las transformaciones. La sesión se cierra con `spark.stop()` en un bloque `finally`.

- [Reporte PDF con la plantilla ESCOM](/big-data/practica2/bd-02-introduccion-apache-spark.pdf).
- [Script Python completo](/big-data/practica2/scripts/analisis_censo.py).
- [Dependencias de la ejecución](/big-data/practica2/requirements.txt).
- [CSV de las diez ocupaciones](/big-data/practica2/resultados/Reporte_Ocupaciones_Eduardo_Alonso_Sanchez/ocupaciones.csv).
- [Resumen JSON](/big-data/practica2/resultados/resumen.json).
- [Consola de la ejecución guardada](/big-data/practica2/resultados/ejecucion.txt).

## 8. Conclusiones

El flujo de PySpark cubrió la carga, la exploración inicial, las tres consultas y la exportación. La ocupación más frecuente fue `Prof-specialty`, el promedio semanal fue de 36.40 horas para `Female` y 42.42 para `Male`, y el filtro de México produjo 951 registros.

La etiqueta `?` limita una comparación posterior de profesiones: una de las categorías más frecuentes no identifica una ocupación. Si se necesitara analizar sólo oficios conocidos, habría que definir su tratamiento antes de repetir la agrupación. En esta práctica la conservé para que los resultados fueran verificables contra el archivo original.

La ejecución local permitió revisar el funcionamiento de las operaciones. Para estudiar escalabilidad haría falta una prueba con condiciones de clúster, volumen y tiempos documentados; no se obtuvieron esas mediciones en este análisis.

## Fuentes

- [Adult. UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/2/adult). Procedencia y propósito del conjunto.
- [saravrajavelu: Adult Income Analysis, adult.csv](https://github.com/saravrajavelu/Adult-Income-Analysis/blob/master/adult.csv). Copia utilizada.
- [Apache Spark: lectura CSV con DataFrameReader](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrameReader.csv.html). Opciones de lectura.
- [Apache Spark: guía de inicio](https://spark.apache.org/docs/latest/quick-start.html). DataFrames, transformaciones y acciones.
- [Apache Spark: escritura CSV con DataFrameWriter](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrameWriter.csv.html). Exportación de resultados.

[Volver al índice de Big Data](/#big-data) · [Revisar la Práctica 1](/big-data/practica1/)
