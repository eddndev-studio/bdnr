---
layout: ../layouts/Layout.astro
title: "Práctica 4 - MonetDB"
---

# Reporte de Práctica 4: Instalación y uso de un sistema de bases de datos orientado a columnas (MonetDB)

Este documento registra la implementación de la Práctica 4 sobre **MonetDB**, una base de datos orientada a columnas optimizada para cargas analíticas (OLAP). En lugar de instalar MonetDB sobre Windows con el asistente gráfico como sugiere el enunciado original, se optó por levantar el servidor dentro de un contenedor **Podman** usando la imagen oficial `monetdb/monetdb`, de modo que la práctica sea reproducible y auto-contenida.

La actividad evaluable (Sección 5 del enunciado) consiste en resolver 16 consultas analíticas sobre el dataset real **Video Game Sales** (`gregorut/videogamesales`), que contiene 16,598 videojuegos con ventas superiores a 100,000 copias, desglosadas por región.

## 1. Preparación del Entorno

Se levanta el servidor de MonetDB en un contenedor Podman con el puerto 50000 expuesto hacia el host. La imagen exige definir una contraseña de administrador mediante la variable `MDB_DB_ADMIN_PASS`; al arrancar crea una base de datos `monetdb` con el usuario `monetdb`.

```bash
podman run -d --name monetdb-p4 -p 50000:50000 \
  -e MDB_DB_ADMIN_PASS=monetdb \
  docker.io/monetdb/monetdb:latest
```
```text
Creating database 'monetdb'
created database with password for monetdb user: monetdb
Starting MonetDB daemon
```

El cliente `mclient` no acepta la contraseña por argumento; la toma de un archivo `.monetdb`. Se crea dentro del contenedor y se referencia con la variable `DOTMONETDBFILE`:

```bash
podman exec monetdb-p4 sh -c \
  'printf "user=monetdb\npassword=monetdb\nlanguage=sql\n" > /tmp/.monetdb'

echo "SELECT 1 AS test;" | \
  podman exec -i -e DOTMONETDBFILE=/tmp/.monetdb monetdb-p4 mclient -d monetdb
```
```text
+------+
| test |
+======+
|    1 |
+------+
1 tuple
```

## 2. Esquema y carga del dataset

El CSV (`vgsales.csv`) se copia al contenedor en `/data/` y se define la tabla `vgsales`. Durante la carga surgió el **primer hallazgo**: `YEAR` es una palabra reservada en MonetDB (se usa en la sintaxis de intervalos `EXTRACT(YEAR FROM ...)`), por lo que no puede usarse como nombre de columna sin comillas. Siguiendo la misma convención que el autor ya aplicó para `Rank` → `ranking`, la columna `Year` del CSV se mapea a `anio`.

```sql
DROP TABLE IF EXISTS vgsales;

CREATE TABLE vgsales (
    ranking      INTEGER,           -- "Rank" en el CSV (RANK es palabra reservada)
    name         VARCHAR(200) NOT NULL,
    platform     VARCHAR(20)  NOT NULL,
    anio         SMALLINT,          -- "Year"; YEAR es palabra reservada, admite NULL ('N/A')
    genre        VARCHAR(30)  NOT NULL,
    publisher    VARCHAR(120),      -- admite NULL: el CSV trae 'N/A'
    na_sales     DECIMAL(6,2),
    eu_sales     DECIMAL(6,2),
    jp_sales     DECIMAL(6,2),
    other_sales  DECIMAL(6,2),
    global_sales DECIMAL(6,2)
);

-- Carga: OFFSET 2 omite el encabezado; el literal 'N/A' se mapea a NULL.
COPY OFFSET 2 INTO vgsales
    FROM '/data/vgsales.csv'
    USING DELIMITERS ',', E'\n', '"'
    NULL AS 'N/A';
```
*Explicación:* `COPY ... INTO` es el cargador masivo nativo de MonetDB (mucho más rápido que `INSERT` fila por fila). `OFFSET 2` salta la línea de encabezado, `DELIMITERS ',', E'\n', '"'` declara separador de campo, de registro y carácter de entrecomillado (necesario para nombres que contienen comas, p. ej. `"Monsters, Inc."`), y `NULL AS 'N/A'` convierte el literal `N/A` —presente en `Year` y `Publisher`— en `NULL`.

Verificación de la carga:

```sql
SELECT COUNT(*) AS total_filas, COUNT(anio) AS con_anio,
       COUNT(*)-COUNT(anio) AS anio_nulo FROM vgsales;
```
```text
+-------------+----------+-----------+
| total_filas | con_anio | anio_nulo |
+=============+==========+===========+
|       16598 |    16327 |       271 |
+-------------+----------+-----------+
```
*Explicación:* Se cargaron las 16,598 filas y 271 quedaron con `anio` nulo (los registros que traían `N/A`), confirmando que el mapeo a `NULL` funcionó.

---

## 3. Sección 5: Actividades sobre el dataset

### Actividad 1 — Juegos de 'Sports' lanzados en 2006

```sql
SELECT *
FROM vgsales
WHERE genre = 'Sports' AND anio = 2006
ORDER BY global_sales DESC;
```
```text
+---------+----------------------------------+----------+------+--------+-----------------+...+--------------+
| ranking | name                             | platform | anio | genre  | publisher       |   | global_sales |
+=========+==================================+==========+======+========+=================+===+==============+
|       1 | Wii Sports                       | Wii      | 2006 | Sports | Nintendo        |   |        82.74 |
|     241 | Madden NFL 07                    | PS2      | 2006 | Sports | Electronic Arts |   |         4.49 |
|     250 | Winning Eleven: Pro Evo. 2007    | PS2      | 2006 | Sports | Konami          |   |         4.39 |
|     284 | FIFA Soccer 07                   | PS2      | 2006 | Sports | Electronic Arts |   |         4.11 |
|      ...                                                                                                  |
```
*Explicación:* `Wii Sports` (el juego más vendido de toda la tabla, 82.74 M) encabeza el resultado por el `ORDER BY global_sales DESC`. El filtro combina género y año.

### Actividad 2 — Top 10 plataformas por ventas en Norteamérica

```sql
SELECT platform, SUM(na_sales) AS total_na
FROM vgsales
GROUP BY platform
ORDER BY total_na DESC
LIMIT 10;
```
```text
+----------+----------+        +----------+----------+
| platform | total_na |        | platform | total_na |
+==========+==========+        +==========+==========+
| X360     |   601.05 |        | PS       |   336.51 |
| PS2      |   583.84 |        | GBA      |   187.54 |
| Wii      |   507.71 |        | XB       |   186.69 |
| PS3      |   392.26 |        | N64      |   139.02 |
| DS       |   390.71 |        | GC       |   133.46 |
+----------+----------+        +----------+----------+
```
*Explicación:* Agregación clásica `GROUP BY` + `SUM`. La Xbox 360 lidera el mercado norteamericano. Este tipo de consulta agregada sobre una columna es donde el almacenamiento por columnas de MonetDB brilla: solo lee `platform` y `na_sales`.

### Actividad 3 — Juegos con "Mario" en el nombre (LIKE)

```sql
SELECT name, platform, anio, global_sales
FROM vgsales
WHERE name LIKE '%Mario%';
```
La consulta devuelve **113 juegos**. Ordenados por ventas para mostrar los principales:

```text
+---------------------------+----------+------+--------------+
| name                      | platform | anio | global_sales |
+===========================+==========+======+==============+
| Super Mario Bros.         | NES      | 1985 |        40.24 |
| Mario Kart Wii            | Wii      | 2008 |        35.82 |
| New Super Mario Bros.     | DS       | 2006 |        30.01 |
| New Super Mario Bros. Wii | Wii      | 2009 |        28.62 |
| Mario Kart DS             | DS       | 2005 |        23.42 |
+---------------------------+----------+------+--------------+
```
*Explicación:* `LIKE '%Mario%'` busca la subcadena en cualquier posición. Se proyectan únicamente las cuatro columnas pedidas.

### Actividad 4 — Juegos publicados por Nintendo

```sql
SELECT * FROM vgsales WHERE publisher = 'Nintendo';
```
Devuelve **703 juegos**. Muestra de los más vendidos:

```text
+--------------------------+----------+------+--------------+
| name                     | platform | anio | global_sales |
+==========================+==========+======+==============+
| Wii Sports               | Wii      | 2006 |        82.74 |
| Super Mario Bros.        | NES      | 1985 |        40.24 |
| Mario Kart Wii           | Wii      | 2008 |        35.82 |
| Wii Sports Resort        | Wii      | 2009 |        33.00 |
| Pokemon Red/Pokemon Blue | GB       | 1996 |        31.37 |
+--------------------------+----------+------+--------------+
```

### Actividad 5 — Más de 5 M en Europa y menos de 1 M en Japón

```sql
SELECT *
FROM vgsales
WHERE eu_sales > 5 AND jp_sales < 1;
```
```text
+--------------------------------+----------+----------+----------+
| name                           | platform | eu_sales | jp_sales |
+================================+==========+==========+==========+
| Grand Theft Auto V             | PS3      |     9.27 |     0.97 |
| The Sims 3                     | PC       |     6.42 |     0.00 |
| World of Warcraft              | PC       |     6.21 |     0.00 |
| FIFA 16                        | PS4      |     6.06 |     0.06 |
| Call of Duty: Black Ops II     | PS3      |     5.88 |     0.65 |
|  ... (11 juegos en total)                                       |
```
*Explicación:* Conjunción de dos condiciones sobre columnas distintas. Aparecen títulos occidentales (GTA, FIFA, Call of Duty) con escasa penetración en el mercado japonés.

### Actividad 6 — Cantidad de juegos por género

```sql
SELECT genre, COUNT(*) AS total_juegos
FROM vgsales
GROUP BY genre
ORDER BY total_juegos DESC;
```
```text
+--------------+--------------+        +--------------+--------------+
| genre        | total_juegos |        | genre        | total_juegos |
+==============+==============+        +==============+==============+
| Action       |         3316 |        | Racing       |         1249 |
| Sports       |         2346 |        | Platform     |          886 |
| Misc         |         1739 |        | Simulation   |          867 |
| Role-Playing |         1488 |        | Fighting     |          848 |
| Shooter      |         1310 |        | Strategy     |          681 |
| Adventure    |         1286 |        | Puzzle       |          582 |
+--------------+--------------+        +--------------+--------------+
```
*Explicación:* "Action" es, por mucho, el género con más títulos publicados (3,316).

### Actividad 7 — Promedio de ventas en Japón por editorial

```sql
SELECT publisher, AVG(jp_sales) AS promedio_jp
FROM vgsales
GROUP BY publisher
ORDER BY promedio_jp DESC;
```
*Explicación:* Devuelve una fila por cada editorial (≈580) con su promedio de ventas en Japón. Encabezan editoriales pequeñas y especializadas en el mercado japonés cuyo único o escaso catálogo vendió bien localmente, lo que infla el promedio (la media es sensible a catálogos chicos).

### Actividad 8 — Plataformas con más de 1,000 juegos (HAVING)

```sql
SELECT platform, COUNT(*) AS total_juegos
FROM vgsales
GROUP BY platform
HAVING COUNT(*) > 1000
ORDER BY total_juegos DESC;
```
```text
+----------+--------------+
| platform | total_juegos |
+==========+==============+
| DS       |         2163 |
| PS2      |         2161 |
| PS3      |         1329 |
| Wii      |         1325 |
| X360     |         1265 |
| PSP      |         1213 |
| PS       |         1196 |
+----------+--------------+
```
*Explicación:* `HAVING` filtra **después** de agrupar (a diferencia de `WHERE`, que filtra antes). Solo 7 plataformas superan los 1,000 títulos registrados.

### Actividad 9 — Editoriales con más de 50 M acumulados (HAVING SUM)

```sql
SELECT publisher, SUM(global_sales) AS ventas_acumuladas
FROM vgsales
GROUP BY publisher
HAVING SUM(global_sales) > 50
ORDER BY ventas_acumuladas DESC;
```
**25 editoriales** alcanzan la distinción. Top 10:

```text
+------------------------------+-------------------+
| publisher                    | ventas_acumuladas |
+==============================+===================+
| Nintendo                     |           1786.56 |
| Electronic Arts              |           1110.32 |
| Activision                   |            727.46 |
| Sony Computer Entertainment  |            607.50 |
| Ubisoft                      |            474.72 |
| Take-Two Interactive         |            399.54 |
| THQ                          |            340.77 |
| Konami Digital Entertainment |            283.64 |
| Sega                         |            272.99 |
| Namco Bandai Games           |            254.09 |
+------------------------------+-------------------+
```
*Explicación:* `HAVING SUM(...)` filtra grupos por su total acumulado. Nintendo domina con casi 1,787 M de copias.

### Actividad 10 — Año máximo y mínimo por plataforma

```sql
SELECT platform, MAX(anio) AS anio_max, MIN(anio) AS anio_min
FROM vgsales
GROUP BY platform
ORDER BY platform;
```
```text
+----------+----------+----------+
| platform | anio_max | anio_min |
+==========+==========+==========+
| 2600     |     1989 |     1980 |
| 3DS      |     2016 |     2011 |
| DS       |     2020 |     1985 |
| GB       |     2001 |     1988 |
| NES      |     1994 |     1983 |
|  ... (una fila por plataforma)  |
```
*Explicación:* `MAX`/`MIN` sobre `anio` delimitan la ventana temporal de cada plataforma.

### Actividad 11 — Reporte combinado por editorial

```sql
SELECT publisher,
       COUNT(*)          AS total_juegos,
       AVG(global_sales) AS promedio_global,
       SUM(other_sales)  AS total_other
FROM vgsales
GROUP BY publisher
ORDER BY total_juegos DESC;
```
```text
+------------------------------+--------------+-----------------+-------------+
| publisher                    | total_juegos | promedio_global | total_other |
+==============================+==============+=================+=============+
| Electronic Arts              |         1351 |            0.82 |      129.77 |
| Activision                   |          975 |            0.75 |       75.34 |
| Namco Bandai Games           |          932 |            0.27 |       14.69 |
| Ubisoft                      |          921 |            0.52 |       50.26 |
| Konami Digital Entertainment |          832 |            0.34 |       30.31 |
| Nintendo                     |          703 |            2.54 |       95.33 |
+------------------------------+--------------+-----------------+-------------+
```
*Explicación:* Tres funciones de agregación en un mismo `GROUP BY`. Nota interesante: aunque EA publica casi el doble de juegos que Nintendo, el **promedio** de ventas por título de Nintendo (2.54 M) triplica al de EA (0.82 M).

### Actividad 12 — Top 5 géneros por ventas globales, excluyendo PC

```sql
SELECT genre, SUM(global_sales) AS total_global
FROM vgsales
WHERE platform <> 'PC'
GROUP BY genre
ORDER BY total_global DESC
LIMIT 5;
```
```text
+--------------+--------------+
| genre        | total_global |
+==============+==============+
| Action       |      1719.65 |
| Sports       |      1318.92 |
| Shooter      |       992.05 |
| Role-Playing |       879.59 |
| Platform     |       830.88 |
+--------------+--------------+
```
*Explicación:* El `WHERE platform <> 'PC'` filtra **antes** de agregar, excluyendo los títulos de PC del conteo.

### Actividad 13 — Años donde Europa superó a Norteamérica

```sql
SELECT anio,
       SUM(eu_sales) AS total_eu,
       SUM(na_sales) AS total_na
FROM vgsales
WHERE anio IS NOT NULL
GROUP BY anio
HAVING SUM(eu_sales) > SUM(na_sales)
ORDER BY anio;
```
```text
+------+----------+----------+
| anio | total_eu | total_na |
+======+==========+==========+
| 2016 |    26.76 |    22.66 |
+------+----------+----------+
```
*Explicación:* Solo en **2016** las ventas europeas superaron a las norteamericanas. El dataset está incompleto para ese año (de ahí los totales bajos), pero el patrón histórico de dominio de NA solo se invierte ahí.

### Actividad 14 — Promedio de ventas globales por género (sin años nulos)

```sql
SELECT genre, AVG(global_sales) AS promedio_global
FROM vgsales
WHERE anio IS NOT NULL
GROUP BY genre
ORDER BY promedio_global DESC;
```
```text
+--------------+-----------------+        +--------------+-----------------+
| genre        | promedio_global |        | genre        | promedio_global |
+==============+=================+        +==============+=================+
| Platform     |            0.95 |        | Action       |            0.53 |
| Shooter      |            0.80 |        | Fighting     |            0.53 |
| Role-Playing |            0.63 |        | Misc         |            0.47 |
| Racing       |            0.59 |        | Simulation   |            0.46 |
| Sports       |            0.57 |        | Puzzle       |            0.42 |
+--------------+-----------------+        +--------------+-----------------+
```
*Explicación:* Aunque "Action" tiene más títulos (Act. 6), el género "Platform" tiene el **mayor promedio** de ventas por juego (0.95 M): menos títulos pero más exitosos en promedio. El `WHERE anio IS NOT NULL` descarta los 271 registros sin año.

### Actividad 15 — Top 20 por porcentaje de ventas en Japón

```sql
SELECT name, platform, anio, jp_sales, global_sales,
       (jp_sales / global_sales * 100) AS porcentaje_jp
FROM vgsales
WHERE global_sales > 1
ORDER BY porcentaje_jp DESC
LIMIT 20;
```
```text
+------------------------------------------+----------+------+----------+--------------+---------------+
| name                                     | platform | anio | jp_sales | global_sales | porcentaje_jp |
+==========================================+==========+======+==========+==============+===============+
| Monster Hunter Freedom 3                 | PSP      | 2010 |     4.87 |         4.87 |       100.000 |
| Friend Collection                        | DS       | 2009 |     3.67 |         3.67 |       100.000 |
| Monster Hunter 4                         | 3DS      | 2013 |     3.44 |         3.44 |       100.000 |
| Dragon Quest VI: Maboroshi no Daichi     | SNES     | 1995 |     3.19 |         3.19 |       100.000 |
| Super Mario Bros.: The Lost Levels       | NES      | 1986 |     2.65 |         2.65 |       100.000 |
|  ... (20 títulos, todos exclusivos de Japón = 100%)                                                  |
```
*Explicación:* El `WHERE global_sales > 1` evita sesgos: sin él, cualquier juego con ventas ínfimas exclusivas de Japón daría 100% espuriamente. Aun así, los 20 primeros son títulos japoneses (Monster Hunter, Dragon Quest, Yokai Watch) que vendieron **exclusivamente** en Japón, dando 100%.

### Actividad 16 (consulta extra) — Promedio de los 10 más rankeados

> **Interpretación:** se toman los 10 juegos mejor rankeados (la columna `ranking` del CSV es la posición por ventas globales, así que `ranking` 1–10 son los 10 mayores vendedores), se listan ordenados alfabéticamente por nombre, luego por año y por ventas, y se calcula el **promedio de ventas globales** de esos 10 títulos.

```sql
WITH top10 AS (
    SELECT ranking, name, anio, global_sales
    FROM vgsales
    WHERE ranking <= 10
)
SELECT name, anio, global_sales,
       AVG(global_sales) OVER () AS promedio_global_top10
FROM top10
ORDER BY name ASC, anio ASC, global_sales ASC;
```
```text
+---------------------------+------+--------------+-----------------------+
| name                      | anio | global_sales | promedio_global_top10 |
+===========================+======+==============+=======================+
| Duck Hunt                 | 1984 |        28.31 |                 36.94 |
| Mario Kart Wii            | 2008 |        35.82 |                 36.94 |
| New Super Mario Bros.     | 2006 |        30.01 |                 36.94 |
| New Super Mario Bros. Wii | 2009 |        28.62 |                 36.94 |
| Pokemon Red/Pokemon Blue  | 1996 |        31.37 |                 36.94 |
| Super Mario Bros.         | 1985 |        40.24 |                 36.94 |
| Tetris                    | 1989 |        30.26 |                 36.94 |
| Wii Play                  | 2006 |        29.02 |                 36.94 |
| Wii Sports                | 2006 |        82.74 |                 36.94 |
| Wii Sports Resort         | 2009 |        33.00 |                 36.94 |
+---------------------------+------+--------------+-----------------------+
```
*Explicación:* El **promedio de ventas globales de los 10 títulos más vendidos es 36.94 M**. Se usó la función de ventana `AVG(...) OVER ()` para mostrar el promedio junto a cada fila sin colapsar el listado. **Segundo hallazgo:** MonetDB no admite `LIMIT` dentro de una CTE (devuelve `CREATE VIEW: LIMIT not supported`), por lo que se filtró con `WHERE ranking <= 10` — equivalente, ya que `ranking` no tiene huecos en el rango 1–10.

---

## 4. Conclusiones

Las 16 actividades se ejecutaron correctamente sobre las 16,598 filas reales del dataset Video Game Sales cargado en MonetDB. La práctica evidenció dos diferencias prácticas de MonetDB frente a otros motores SQL, ambas detectadas y corregidas al ejecutar las consultas:

1. **`YEAR` es palabra reservada** y no puede ser nombre de columna sin entrecomillar; se renombró a `anio` siguiendo la convención que el propio esquema ya usaba para `Rank` → `ranking`.
2. **`LIMIT` no se permite dentro de una CTE**; se sustituyó por un filtro `WHERE ranking <= 10`.

El almacenamiento orientado a columnas de MonetDB resulta especialmente eficiente para estas consultas analíticas (`GROUP BY`, `SUM`, `AVG`, `HAVING`), ya que solo lee de disco las columnas involucradas en cada consulta en lugar de filas completas.
