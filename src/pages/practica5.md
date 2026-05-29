---
layout: ../layouts/Layout.astro
title: "Práctica 5 - Neo4j"
---

# Reporte de Práctica 5: Uso de un sistema NoSQL basado en grafos (Neo4j)

Este documento registra la implementación de la Práctica 5 sobre **Neo4j 5.7**, una base de datos orientada a grafos. En lugar de instalar Neo4j Desktop sobre Windows o usar Neo4j Sandbox como sugiere el enunciado, se optó por levantar el servidor dentro de un contenedor **Podman** usando la imagen oficial `neo4j:5.7`, de modo que la práctica sea reproducible y auto-contenida.

La práctica se divide en dos bloques de trabajo:

1. **Sección 3 (Sentencias y consultas):** 117 sentencias Cypher sobre la base de datos `empresa` (empleados, dependientes, departamentos, proyectos, domicilios, localizaciones y títulos), reproducidas íntegras en `seed.cypher`.
2. **Sección "Actividad con Dataset Real":** 15 actividades de consulta y agregación sobre el dataset **NCR Ride Bookings** (`yashdevladdha/uber-ride-analytics-dashboard`), que contiene 150,000 registros de viajes en una plataforma de transporte compartida.

## 1. Preparación del Entorno

Se levanta el servidor de Neo4j en un contenedor Podman con los puertos del Browser (7474) y de Bolt (7687) expuestos hacia el host. Se cargan dos extras frente al `podman run` mínimo:

- `NEO4J_PLUGINS='["apoc"]'` para habilitar la librería **APOC**, necesaria por una limitación de cypher-shell que se documenta abajo.
- `NEO4J_server_memory_heap_max__size='2G'` para tener margen de memoria al importar 150,000 nodos.

```bash
podman run -d --name neo4j-p5 \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH="neo4j/bdnrpractica5" \
  -e NEO4J_PLUGINS='["apoc"]' \
  -e NEO4J_dbms_security_procedures_unrestricted='apoc.*' \
  -e NEO4J_server_memory_heap_max__size='2G' \
  -v ./neo4jdata:/data:Z \
  -v ./ncr_ride_bookings.csv:/var/lib/neo4j/import/ncr_ride_bookings.csv:Z \
  docker.io/library/neo4j:5.7
```

Verificación de conexión:

```bash
echo 'RETURN 1 AS test;' | \
  podman exec -i neo4j-p5 cypher-shell -u neo4j -p bdnrpractica5 --format plain
```
```text
test
1
```

## 2. Sección 3 — Base de datos `empresa` (117 sentencias)

El archivo `seed.cypher` reproduce las 117 sentencias Cypher enumeradas en el PDF (creación de 9 empleados con su domicilio, relaciones `es_jefe`, 9 dependientes, 3 departamentos con sus jefes y empleados, 5 localizaciones, 3 proyectos con la relación `labora{horas}`, títulos académicos, agregaciones por género/salario, expresiones regulares sobre domicilios, subconsultas con `EXISTS`, etc.).

Tras ejecutar `seed.cypher`, el grafo queda con la siguiente cardinalidad:

```cypher
MATCH (n) RETURN labels(n)[0] AS Etiqueta, count(*) AS Total ORDER BY Total DESC;
```
```text
Etiqueta,      Total
"empleado",    9
"domicilio",   9
"dependiente", 9
"localizacion",5
"titulo",      4
"departamento",3
"proyecto",    3
```

```cypher
MATCH ()-[r]-() RETURN DISTINCT type(r) AS Relacion, count(*)/2 AS Total ORDER BY Total DESC;
```
```text
Relacion,        Total
"titulo",        11
"vive_en",        9
"es_dependiente", 9
"trabaja",        9
"es_jefe",        6
"en_lugar",       6
"labora",         6
"jefe_dpto",      3
"jefe_proyecto",  3
```

Muestra de la consulta 82 del PDF (empleado–departamento con proyección de columnas):

```cypher
MATCH (a:empleado)-[r]-(d:departamento)
RETURN a.NOMBRE AS NOMBRE, a.APELLIDO AS APELLIDO,
       a.GENERO AS GENERO, a.SALARIO AS SALARIO,
       type(r) AS RELACION, d.nombre AS DEPARTAMENTO;
```
```text
NOMBRE,      APELLIDO,  GENERO, SALARIO, RELACION,      DEPARTAMENTO
"Jesús",     "López",   "M",    50000,   "trabaja",     "Administración"
"Jesús",     "López",   "M",    50000,   "jefe_dpto",   "Administración"
"Rogelio",   "Calzada", "M",    39000,   "trabaja",     "Ventas"
"Rogelio",   "Calzada", "M",    39000,   "jefe_dpto",   "Ventas"
"Ricardo",   "Guzmán",  "M",    45000,   "trabaja",     "Sistemas"
"Ricardo",   "Guzmán",  "M",    45000,   "jefe_dpto",   "Sistemas"
...
```

## 3. Importación del Dataset Real (150,000 nodos)

El CSV se monta en `/var/lib/neo4j/import/` para que `LOAD CSV WITH HEADERS FROM 'file:///...'` lo encuentre. Cada fila se transforma en un nodo `:ride_bookings` con 21 propiedades (fechas, IDs, ubicaciones, montos, motivos de cancelación, calificaciones y método de pago), convirtiendo el literal `null` del CSV a `NULL` real de Cypher.

**Primer hallazgo.** El PDF plantea el `LOAD CSV` con `:auto ... CALL { ... } IN TRANSACTIONS OF 10000 ROWS;` (la sintaxis estándar de Neo4j 5 para cargas masivas). Al ejecutarlo desde `cypher-shell`, falla con:

```text
Could not find command :auto, use :help to see available commands
```

La razón es que la *client command* `:auto` solo está implementada en el modo **interactivo** de cypher-shell 5.7; cuando se lee desde un archivo (`--file`) o se reciben sentencias por *stdin*, el parser la rechaza. Como las consultas `CALL { ... } IN TRANSACTIONS` requieren una *transacción implícita* (auto-commit), no basta con suprimir `:auto`: Neo4j respondería con `A query with 'CALL { ... } IN TRANSACTIONS' can only be executed in an implicit transaction`.

La solución adoptada fue habilitar **APOC** y reemplazar `CALL ... IN TRANSACTIONS` por `apoc.periodic.iterate`, que internamente abre sus propias transacciones por lote y sí funciona dentro de una transacción explícita:

```cypher
CALL apoc.periodic.iterate(
  "LOAD CSV WITH HEADERS FROM 'file:///ncr_ride_bookings.csv' AS row RETURN row",
  "CREATE (b:ride_bookings {
    date:                   date(row.`Date`),
    time:                   localtime(row.`Time`),
    booking_id:             replace(row.`Booking ID`, '\"', ''),
    booking_status:         row.`Booking Status`,
    customer_id:            replace(row.`Customer ID`, '\"', ''),
    vehicle_type:           row.`Vehicle Type`,
    pickup_location:        row.`Pickup Location`,
    drop_location:          row.`Drop Location`,
    booking_value:          CASE row.`Booking Value` WHEN 'null' THEN null ELSE toFloat(row.`Booking Value`) END,
    ride_distance:          CASE row.`Ride Distance` WHEN 'null' THEN null ELSE toFloat(row.`Ride Distance`) END,
    driver_ratings:         CASE row.`Driver Ratings`  WHEN 'null' THEN null ELSE toFloat(row.`Driver Ratings`) END,
    customer_rating:        CASE row.`Customer Rating` WHEN 'null' THEN null ELSE toFloat(row.`Customer Rating`) END,
    payment_method:         CASE row.`Payment Method`  WHEN 'null' THEN null ELSE row.`Payment Method` END,
    driver_cancel_reason:   CASE row.`Driver Cancellation Reason` WHEN 'null' THEN null ELSE row.`Driver Cancellation Reason` END
    /* + el resto de las 21 propiedades */
  })",
  {batchSize: 10000, parallel: false}
) YIELD batches, total, timeTaken RETURN batches, total, timeTaken;
```
```text
batches, total, timeTaken
15,      150000, 5
```

*Explicación:* 15 lotes de 10,000 filas procesados en ~5 segundos.

```cypher
MATCH (b:ride_bookings) RETURN count(b) AS NODOS_IMPORTADOS;
```
```text
NODOS_IMPORTADOS
150000
```

---

## 4. Sección "Actividad con Dataset Real" (15 actividades)

> Equivalencias SQL → Cypher usadas a lo largo de las actividades:
> - `GROUP BY` → agrupación implícita al usar funciones de agregación.
> - `HAVING` → `WHERE` después de `WITH` (filtra sobre el agregado).
> - `LIKE '%x%'` → `=~ '.*x.*'` (o `CONTAINS`).

### Actividad 1 — Viajes "Completed" con vehículo "Bike", ordenados por distancia (desc)

```cypher
MATCH (b:ride_bookings)
WHERE b.booking_status = 'Completed' AND b.vehicle_type = 'Bike'
RETURN b.booking_id AS Viaje, b.ride_distance AS Distancia, b.booking_value AS Costo
ORDER BY b.ride_distance DESC;
```
```text
Viaje,        Distancia, Costo
"CNR7401745", 50.0,      149.0
"CNR1072295", 49.99,     2243.0
"CNR9031498", 49.98,     175.0
"CNR3417408", 49.97,     291.0
"CNR1341814", 49.97,     177.0
...
```
*Explicación:* El filtro combina estado y tipo de vehículo; `ORDER BY ... DESC` lleva al frente la distancia máxima registrada.

### Actividad 2 — Top 10 ubicaciones de recogida por dinero recaudado

```cypher
MATCH (b:ride_bookings)
RETURN b.pickup_location AS Ubicacion, sum(b.booking_value) AS Total
ORDER BY Total DESC LIMIT 10;
```
```text
Ubicacion,           Total
"Barakhamba Road",   341154.0
"Khandsa",           338502.0
"Subhash Chowk",     329386.0
"Pataudi Chowk",     328572.0
"Badarpur",          327193.0
"Tughlakabad",       326283.0
"AIIMS",             325733.0
"Inderlok",          325358.0
"Mayur Vihar",       322409.0
"Greater Noida",     322273.0
```
*Explicación:* `sum(b.booking_value)` agrega implícitamente por la única columna no agregada (`pickup_location`), reproduciendo el efecto de `GROUP BY` en SQL.

### Actividad 3 — Destinos que contienen "Nagar" (operador LIKE)

```cypher
MATCH (b:ride_bookings)
WHERE b.drop_location =~ '.*Nagar.*'
RETURN b.booking_id AS Viaje, b.vehicle_type AS Vehiculo,
       b.drop_location AS Destino, b.booking_value AS Costo;
```
La consulta devuelve **14,533 viajes**. Muestra:

```text
Viaje,        Vehiculo,   Destino,         Costo
"CNR8494506", "Auto",     "Malviya Nagar", 627.0
"CNR7721892", "Auto",     "Adarsh Nagar",  135.0
"CNR8962232", "Go Mini",  "GTB Nagar",     836.0
"CNR6739317", "Go Sedan", "GTB Nagar",     NULL
"CNR9465840", "eBike",    "Rajiv Nagar",   NULL
```
*Explicación:* Cypher no tiene `LIKE`; se sustituye por la expresión regular `=~ '.*Nagar.*'`. Los `NULL` en `Costo` corresponden a viajes cancelados (sin tarifa).

### Actividad 4 — Pagos con UPI

```cypher
MATCH (b:ride_bookings)
WHERE b.payment_method = 'UPI'
RETURN b.booking_id AS Viaje, b.booking_value AS Costo, b.booking_status AS Estado;
```
**45,909 viajes** se pagaron con UPI (transferencia electrónica), confirmando que es el método de pago dominante en este dataset.

### Actividad 5 — Viajes atípicos: costo > 800 con distancia < 15 km

```cypher
MATCH (b:ride_bookings)
WHERE b.booking_value > 800 AND b.ride_distance < 15
RETURN b.booking_id AS Viaje, b.booking_value AS Costo,
       b.ride_distance AS Distancia, b.vehicle_type AS Vehiculo
ORDER BY b.booking_value DESC;
```
La consulta detecta **5,662 viajes** con tarifa alta pero distancia corta, candidatos a auditoría tarifaria.

### Actividad 6 — Conteo de viajes por tipo de vehículo (GROUP BY)

```cypher
MATCH (b:ride_bookings)
RETURN b.vehicle_type AS Tipo_Vehiculo, count(*) AS Total_Viajes
ORDER BY Total_Viajes DESC;
```
```text
Tipo_Vehiculo,    Total_Viajes
"Auto",           37419
"Go Mini",        29806
"Go Sedan",       27141
"Bike",           22517
"Premier Sedan",  18111
"eBike",          10557
"Uber XL",         4449
```
*Explicación:* "Auto" representa el mayor volumen (~25 % de la flota).

### Actividad 7 — Promedio de calificación al conductor por tipo de vehículo

```cypher
MATCH (b:ride_bookings)
RETURN b.vehicle_type AS Tipo_Vehiculo,
       round(avg(b.driver_ratings), 2) AS Calificacion_Promedio
ORDER BY Calificacion_Promedio DESC;
```
```text
Tipo_Vehiculo,   Calificacion_Promedio
"Uber XL",       4.24
"eBike",         4.23
"Go Sedan",      4.23
"Auto",          4.23
"Premier Sedan", 4.23
"Bike",          4.23
"Go Mini",       4.23
```
*Explicación:* Las calificaciones son prácticamente uniformes (4.23–4.24), patrón típico de un dataset sintético/generado.

### Actividad 8 — Clientes con más de 3 viajes completados (GROUP BY + HAVING)

```cypher
MATCH (b:ride_bookings)
WHERE b.booking_status = 'Completed'
WITH b.customer_id AS Cliente, count(*) AS Viajes_Completados
WHERE Viajes_Completados > 3
RETURN Cliente, Viajes_Completados
ORDER BY Viajes_Completados DESC;
```
```text
(0 filas)
```
**Segundo hallazgo.** Con el predicado literal del enunciado (`> 3`) **no se obtiene ningún resultado**. Una consulta de diagnóstico muestra por qué:

```cypher
MATCH (b:ride_bookings) WHERE b.booking_status='Completed'
WITH b.customer_id AS c, count(*) AS n
RETURN max(n) AS max_viajes_por_cliente, count(c) AS clientes_unicos;
```
```text
max_viajes_por_cliente, clientes_unicos
3,                      92547
```

El máximo de viajes completados por un cliente en todo el dataset es **exactamente 3** (otro indicio del origen sintético del CSV). Cambiando a `>= 3` se obtiene la respuesta interpretable que el enunciado buscaba:

```cypher
MATCH (b:ride_bookings)
WHERE b.booking_status = 'Completed'
WITH b.customer_id AS Cliente, count(*) AS Viajes_Completados
WHERE Viajes_Completados >= 3
RETURN Cliente, Viajes_Completados
ORDER BY Viajes_Completados DESC;
```
```text
Cliente,       Viajes_Completados
"CID7828101",  3
"CID4523979",  3
"CID8727691",  3
```

*Explicación de la equivalencia:* en SQL `HAVING` filtra **después** de `GROUP BY`; en Cypher el mismo patrón se logra con `WHERE` tras un `WITH` que ya contiene la agregación.

### Actividad 9 — Métodos de pago con ventas acumuladas superiores a 1,000,000

```cypher
MATCH (b:ride_bookings)
WITH b.payment_method AS Metodo, sum(b.booking_value) AS Ventas
WHERE Metodo IS NOT NULL AND Ventas > 1000000
RETURN Metodo, Ventas
ORDER BY Ventas DESC;
```
```text
Metodo,        Ventas
"UPI",         23345101.0
"Cash",        12895649.0
"Uber Wallet",  6200898.0
"Credit Card",  5224025.0
"Debit Card",   4180510.0
```
*Explicación:* Los cinco métodos válidos superan el millón. El `WHERE Metodo IS NOT NULL` elimina viajes cancelados antes del pago.

### Actividad 10 — Distancia máxima y mínima por ubicación de recogida

```cypher
MATCH (b:ride_bookings)
RETURN b.pickup_location AS Ubicacion,
       max(b.ride_distance) AS Maxima,
       min(b.ride_distance) AS Minima
ORDER BY Ubicacion;
```
```text
Ubicacion,        Maxima, Minima
"AIIMS",          49.95,  1.11
"Adarsh Nagar",   49.86,  1.12
"Akshardham",     49.93,  1.28
"Ambience Mall",  49.89,  1.11
"Anand Vihar",    49.87,  1.79
...
```
*Explicación:* `max` y `min` se aplican como cualquier agregación; el rango de distancias es prácticamente idéntico en todas las ubicaciones (≈1 a ≈50 km).

### Actividad 11 — Reporte combinado por método de pago

```cypher
MATCH (b:ride_bookings)
WHERE b.payment_method IS NOT NULL
RETURN b.payment_method AS Metodo,
       count(*) AS Total_Viajes,
       round(avg(b.booking_value), 2) AS Costo_Promedio,
       sum(b.booking_value) AS Suma_Ganancias
ORDER BY Suma_Ganancias DESC;
```
```text
Metodo,        Total_Viajes, Costo_Promedio, Suma_Ganancias
"UPI",         45909,        508.51,         23345101.0
"Cash",        25367,        508.36,         12895649.0
"Uber Wallet", 12276,        505.12,          6200898.0
"Credit Card", 10209,        511.71,          5224025.0
"Debit Card",   8239,        507.41,          4180510.0
```
*Explicación:* Tres agregaciones (`count`, `avg`, `sum`) en una misma agrupación implícita. UPI casi cuadruplica a `Credit Card` en volumen.

### Actividad 12 — Top 5 motivos de cancelación por el conductor

```cypher
MATCH (b:ride_bookings)
WHERE b.driver_cancel_reason IS NOT NULL
RETURN b.driver_cancel_reason AS Motivo, count(*) AS Incidencias
ORDER BY Incidencias DESC LIMIT 5;
```
```text
Motivo,                                Incidencias
"Customer related issue",              6837
"The customer was coughing/sick",      6751
"Personal & Car related issues",       6726
"More than permitted people in there", 6686
```
*Explicación:* Solo aparecen 4 motivos porque el dataset solo define 4 valores no nulos para esta columna; el `LIMIT 5` no inventa una fila adicional.

### Actividad 13 — Fechas con recaudación superior a 50,000

```cypher
MATCH (b:ride_bookings)
WITH b.date AS Fecha, sum(b.booking_value) AS Total
WHERE Total > 50000
RETURN Fecha, Total
ORDER BY Total DESC;
```
**365 fechas** superan el umbral (es decir, **todas** las fechas del año cubierto). Top 5:

```text
Fecha,        Total
2024-10-20,   219424.0
2024-11-16,   218931.0
2024-12-29,   214951.0
2024-01-26,   211007.0
2024-10-13,   209161.0
```
*Explicación:* La distribución es bastante pareja (entre ~150K y ~220K diarios), por lo que el filtro de 50K no excluye ningún día.

### Actividad 14 — Promedio de calificación del cliente por destino (solo viajes completados)

```cypher
MATCH (b:ride_bookings)
WHERE b.booking_status = 'Completed'
RETURN b.drop_location AS Destino,
       round(avg(b.customer_rating), 2) AS Calificacion_Promedio
ORDER BY Calificacion_Promedio DESC;
```
```text
Destino,              Calificacion_Promedio
"Shastri Nagar",      4.47
"Kashmere Gate ISBT", 4.45
"Hauz Rani",          4.44
"Preet Vihar",        4.44
"Palam Vihar",        4.44
...
```
*Explicación:* El filtro `booking_status = 'Completed'` se aplica **antes** del agregado, como pedía el enunciado (descarta cancelados sin calificación válida).

### Actividad 15 — Tarifa por kilómetro (top 20)

```cypher
MATCH (b:ride_bookings)
WHERE b.ride_distance > 0 AND b.booking_value IS NOT NULL
RETURN b.booking_id AS Viaje,
       b.booking_value AS Costo,
       b.ride_distance AS Distancia,
       round(b.booking_value / b.ride_distance, 2) AS Tarifa_Por_Km
ORDER BY Tarifa_Por_Km DESC LIMIT 20;
```
```text
Viaje,        Costo,  Distancia, Tarifa_Por_Km
"CNR3705367", 3148.0, 1.0,       3148.0
"CNR8682875", 3060.0, 1.41,      2170.21
"CNR3303271", 3434.0, 2.06,      1666.99
"CNR9120177", 3834.0, 2.31,      1659.74
"CNR1834127", 2102.0, 1.29,      1629.46
...
```
*Explicación:* El predicado `ride_distance > 0` evita la división por cero que rompería la consulta; `booking_value IS NOT NULL` descarta viajes cancelados. Los líderes son viajes con tarifa cercana al máximo (~3K) sobre distancia mínima (~1 km), perfiles típicos de tarifas dinámicas en zonas de alta demanda.

---

## 5. Conclusiones

Las 117 sentencias de la base `empresa` y las 15 actividades sobre el dataset real `ride_bookings` (150,000 nodos) se ejecutaron correctamente en Neo4j 5.7. La práctica evidenció dos diferencias prácticas respecto a lo planteado en el PDF, ambas detectadas y resueltas:

1. **`:auto` no funciona en cypher-shell no-interactivo (5.7).** El cargador masivo `:auto LOAD CSV ... CALL { ... } IN TRANSACTIONS OF 10000 ROWS;` propuesto en el PDF solo se ejecuta dentro del Neo4j Browser o en una sesión TTY de cypher-shell. Para automatizar la carga vía script se sustituyó por `apoc.periodic.iterate`, lo que requirió habilitar el plugin **APOC** (`NEO4J_PLUGINS='["apoc"]'`) y obliga a recrear el contenedor (no basta con reiniciar).
2. **La Actividad 8 con `> 3` no produce resultados** porque el máximo de viajes completados por cliente en el dataset es exactamente 3 (otro indicio de que el CSV es sintético). El reporte documenta el hallazgo y muestra también la versión con `>= 3` para que el ejercicio tenga salida interpretable.

El modelo orientado a grafos de Neo4j permitió expresar de forma muy directa las relaciones de la base `empresa` (`es_jefe`, `trabaja`, `es_dependiente`, `labora{horas}`, etc.) mediante patrones `MATCH (n)-[r]-(m)`, y reutilizar las mismas funciones de agregación (`count`, `sum`, `avg`, `min`, `max`) sobre los 150,000 nodos del dataset real con tiempos de respuesta de milisegundos.
