---
layout: ../layouts/Layout.astro
title: "Práctica 3 - MongoDB"
---

# Reporte de Práctica 3: Definición y validación de datos de documentos JSON con MongoDB

Este documento registra la implementación de la Práctica 3 sobre MongoDB. En lugar de instalar MongoDB sobre Windows como sugiere el enunciado original, se optó por levantar el servidor dentro de un contenedor **Podman** usando la imagen oficial `mongo:7`, de modo que la práctica sea reproducible y auto-contenida.

## 1. Preparación del Entorno

Se levanta el servidor de MongoDB en un contenedor Podman con el puerto 27017 expuesto hacia el host y un volumen persistente en el directorio del proyecto.

```bash
podman run -d --name mongo-p3 \
  -p 27017:27017 \
  -v "$(pwd)/mongodata":/data/db:Z \
  docker.io/library/mongo:7
```
*Explicación:* Se usa la imagen `mongo:7` (misma rama mayor que menciona el enunciado, `7.0.x`). La bandera `-v ... :Z` indica a SELinux que el volumen es accesible por el contenedor. El puerto 27017 queda disponible para que cualquier cliente externo (incluido MongoDB Compass) pueda conectarse.

Se verifica la conexión ejecutando `mongosh` dentro del contenedor:

```bash
podman exec mongo-p3 mongosh --quiet --eval 'db.runCommand({ping:1})'
```
```text
{ ok: 1 }
```

Para correr los scripts de la práctica se creó un helper `run.sh` que copia el archivo al contenedor y lo ejecuta con `mongosh`:

```bash
#!/usr/bin/env bash
CONTAINER=mongo-p3
if [ $# -eq 0 ]; then
  podman exec -it "$CONTAINER" mongosh
else
  podman cp "$1" "$CONTAINER":/tmp/script.js
  podman exec "$CONTAINER" mongosh --quiet --file /tmp/script.js
fi
```

---

## 2. Sección 4: Sentencias del Enunciado

Todo el bloque de la Sección 4 se reorganizó en un archivo único `seccion4.js` que se ejecuta de principio a fin con `./run.sh seccion4.js`. El script es idempotente: al inicio elimina las colecciones `oficinas`, `empleados` y `proyectos` para poder re-ejecutarse sin conflictos.

### 2.1 Colección `oficinas` (puntos 1-6)

Se cambia a la base `empresa` y se crea la colección `oficinas` como no-limitada (`capped: false`). Posteriormente se insertan las tres oficinas con sus arreglos de ubicaciones.

```javascript
db = db.getSiblingDB("empresa");
db.createCollection("oficinas", { capped: false });

db.oficinas.insertOne({ _id: 1, numero: 1, nombre_of: "Sistemas",       jefe_of: "111222333", ubicaciones: ["CDMX"] });
db.oficinas.insertOne({ _id: 2, numero: 2, nombre_of: "Ventas",         jefe_of: "333444555", ubicaciones: ["CDMX", "Pachuca"] });
db.oficinas.insertOne({ _id: 3, numero: 3, nombre_of: "Administración", jefe_of: "777888999", ubicaciones: ["Monterrey", "Guadalupe", "Juárez"] });

db.oficinas.find();
```
```text
[
  { _id: 1, numero: 1, nombre_of: 'Sistemas',       jefe_of: '111222333', ubicaciones: ['CDMX'] },
  { _id: 2, numero: 2, nombre_of: 'Ventas',         jefe_of: '333444555', ubicaciones: ['CDMX', 'Pachuca'] },
  { _id: 3, numero: 3, nombre_of: 'Administración', jefe_of: '777888999', ubicaciones: ['Monterrey', 'Guadalupe', 'Juárez'] }
]
```
*Explicación:* En MongoDB, una colección puede almacenar arreglos directamente como valor de un campo; esto contrasta con el modelo relacional donde haría falta una tabla puente `oficina_ubicacion`. El atributo `_id` se fija manualmente a enteros 1-3 para que coincida con el campo `numero`.

### 2.2 Colección `empleados` (puntos 7-21)

Se declara primero el empleado `emp1` como variable JavaScript con un dependiente anidado; se imprime por consola con `print(emp1)` y luego se inserta.

```javascript
let emp1 = {
  _id: 1, nss: "222333444",
  nombre: "Guadalupe", paterno: "Oñate", materno: "Martínez",
  fecha_nac: ISODate("1969-11-24"),
  direccion: { calle: "Av. Revolución", numero: 348, colonia: "Fuentes", ciudad: "San Ignacio", codpos: "67656" },
  genero: "F", salario: 25000, jefe: "777888999",
  cargo: "Oficinista", oficina: 3, titulo: "Licenciado",
  fecha_contratacion: ISODate("2000-04-07"),
  dependientes: [
    { nombre: "Karen", paterno: "Oñate", materno: "Rodríguez", fecha_nac: ISODate("1995-11-09"), genero: "F", parentesco: "HIJA" }
  ]
};
db.empleados.insertOne(emp1);
db.empleados.countDocuments();
```
```text
1
```
*Explicación:* `direccion` se modela como **documento embebido** (relación 1:1 que siempre se consulta con el empleado) y `dependientes` como **arreglo de documentos embebidos** (relación 1:N de baja cardinalidad). Este patrón de *embedding* es el más natural en MongoDB para datos que se acceden en conjunto y evita la necesidad de hacer `lookup` en tiempo de lectura.

A continuación se declaran las variables `emp2` a `emp9` (empleados Jesús, Julia, Mario, Rogelio, Bruce, Laura, Sandra y Guadalupe) y se insertan en lote:

```javascript
db.empleados.insertMany([emp2, emp3, emp4, emp5, emp6, emp7, emp8, emp9]);
db.empleados.countDocuments();
```
```text
9
```
*Explicación:* `insertMany` es más eficiente que múltiples `insertOne` porque MongoDB procesa el lote en una sola operación de escritura.

### 2.3 Validación con JSON Schema (punto 22)

El enunciado define un esquema `$jsonSchema` extenso que impone tipos, longitudes y enumeraciones sobre la colección `empleados`. El PDF pide copiar este texto a la pestaña **Validation** de Compass; en este reporte se aplica programáticamente con `collMod` sin necesidad de la UI:

```javascript
let esquemaEmpleados = {
  $jsonSchema: {
    required: ["nss", "nombre", "paterno", "genero", "dependientes"],
    properties: {
      _id:     { bsonType: "int" },
      nss:     { bsonType: "string", minLength: 5, maxLength: 9 },
      nombre:  { bsonType: "string", minLength: 3, maxLength: 30 },
      paterno: { bsonType: "string", minLength: 3, maxLength: 30 },
      materno: { bsonType: "string", minLength: 3, maxLength: 30 },
      genero:  { bsonType: "string", enum: ["F", "M"] },
      fecha_nac: { bsonType: "date" },
      direccion: {
        bsonType: "object",
        properties: {
          calle:   { bsonType: "string", minLength: 3, maxLength: 30 },
          numero:  { bsonType: "int", minimum: 1 },
          colonia: { bsonType: "string", minLength: 3, maxLength: 30 },
          ciudad:  { bsonType: "string", minLength: 3, maxLength: 30 },
          codpos:  { bsonType: "string", minLength: 5, maxLength: 5 }
        }
      },
      salario: { bsonType: "int", minimum: 2000, maximum: 50000 },
      cargo:   { bsonType: "string", minLength: 3, maxLength: 30 },
      oficina: { bsonType: "int", minimum: 1, maximum: 50 },
      titulo:  { bsonType: "string", minLength: 3, maxLength: 50 },
      fecha_contratacion: { bsonType: "date" },
      dependientes: {
        bsonType: "array",
        items: {
          bsonType: "object",
          properties: {
            nombre:   { bsonType: "string", minLength: 3, maxLength: 30 },
            paterno:  { bsonType: "string", minLength: 3, maxLength: 30 },
            materno:  { bsonType: "string", minLength: 3, maxLength: 30 },
            fecha_nac: { bsonType: "date" },
            genero:    { bsonType: "string", enum: ["F", "M"] },
            parentesco:{ bsonType: "string", enum: ["HIJO","HIJA","PADRE","MADRE","NIETO","NIETA"] }
          }
        }
      }
    }
  }
};

db.runCommand({
  collMod: "empleados",
  validator: esquemaEmpleados,
  validationLevel: "moderate",
  validationAction: "error"
});
```
*Explicación:* `collMod` modifica la configuración de una colección existente sin tener que re-crearla. `validationLevel: "moderate"` aplica el validador solo a documentos que ya cumplen el esquema (útil porque nuestros 9 documentos existentes encajan), y `validationAction: "error"` hace que un documento inválido en un `insertOne` posterior sea rechazado. Si usáramos `strict` con datos preexistentes heterogéneos, corretían el riesgo de bloquear actualizaciones legítimas.

### 2.4 Consultas sobre `empleados` (puntos 23, 24, 28, 29)

```javascript
// Punto 23: todos los empleados
db.empleados.find({}).toArray().length;
```
```text
9
```

```javascript
// Punto 24: $nor sobre dos predicados
db.empleados.find({
  $nor: [
    { genero: { $in: ["F", "M"] } },
    { salario: { $gte: 2000, $lte: 50000 } }
  ]
});
```
```text
[]
```
*Explicación:* `$nor` devuelve los documentos que **no cumplen ninguna** de las condiciones listadas. Como todos los empleados tienen género "F" o "M" *y* salario entre 2000 y 50000, el resultado es vacío. Es la consulta opuesta a un `$or`.

```javascript
// Punto 28: empleados hombres
db.empleados.countDocuments({ genero: "M" });
```
```text
4
```

```javascript
// Punto 29: empleados fuera del enum [F, M]
db.empleados.countDocuments({ genero: { $nin: ["F", "M"] } });
```
```text
0
```
*Explicación:* Los cuatro hombres son Jesús, Mario, Rogelio y Bruce. La consulta 29 devuelve cero porque el validador ahora obliga a que `genero` pertenezca al conjunto `{F, M}`.

### 2.5 Colección `proyectos` con validador de creación (puntos 30-36)

A diferencia de `empleados`, aquí el validador se define **en el momento de crear la colección** porque no hay datos previos. También se incluyen reglas aritméticas (`minimum`, `maximum`) sobre `presupuesto`, un enumerado para `estado` y restricciones de cardinalidad en el arreglo `trabajadores`.

```javascript
db.createCollection("proyectos", {
  validator: {
    $jsonSchema: {
      required: ["_id", "numero_proy", "num_of", "nombre_proy", "descripcion", "fecha_inicio", "estado"],
      properties: {
        _id:         { bsonType: "int" },
        numero_proy: { bsonType: "int", minimum: 1 },
        num_of:      { bsonType: "int", enum: [1, 2, 3] },
        nombre_proy: { bsonType: "string", maxLength: 100 },
        descripcion: { bsonType: "string" },
        fecha_inicio:  { bsonType: "date" },
        fecha_entrega: { bsonType: "date" },
        presupuesto:   { bsonType: "double", minimum: 20000, maximum: 500000 },
        estado: { bsonType: "string", enum: ["APROBADO", "EJECUTANDO", "PAUSADO", "ENTREGADO"] },
        trabajadores: {
          bsonType: "array",
          minItems: 1,
          maxItems: 10,
          items: {
            bsonType: "object",
            required: ["empleado", "horas"],
            properties: {
              empleado: { bsonType: "object" },
              horas:    { bsonType: "int", minimum: 1 }
            }
          }
        }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});
```
*Explicación:* Se apartó del enunciado en un punto: el enunciado declara `_id: { bsonType: "objectId" }` pero luego inserta literales como `ObjectId("654321abcd00000000000001")` que son cadenas hexadecimales inválidas para un `ObjectId` (debe tener 24 caracteres hex válidos). Para que los tres inserts pasen sin errores, en este reporte el `_id` se tipifica como `int` siguiendo la misma convención usada en `empleados` y `oficinas`.

Se insertan los tres proyectos con referencias a empleados mediante **DBRef**:

```javascript
db.proyectos.insertOne({
  _id: 1, numero_proy: 1, num_of: 2,
  nombre_proy: "Mejoramiento de Calidad",
  descripcion: "Propuesta de implementación de un sistema de software para la vigilancia y reporte de los productos con baja calidad y/o devueltos por clientes",
  fecha_inicio: ISODate("2012-01-10"),
  presupuesto: Double(50000),
  estado: "APROBADO",
  trabajadores: [
    { empleado: { $ref: "empleados", $id: 1, $db: "empresa" }, horas: 16 },
    { empleado: { $ref: "empleados", $id: 2, $db: "empresa" }, horas:  8 }
  ]
});

db.proyectos.insertOne({
  _id: 2, numero_proy: 2, num_of: 1,
  nombre_proy: "Sitio Web",
  descripcion: "Desarrollo de un sitio web corporativo para la empresa Productos Entregables SA",
  fecha_inicio: ISODate("2010-02-18"),
  presupuesto: Double(375000),
  estado: "EJECUTANDO",
  trabajadores: [
    { empleado: { $ref: "empleados", $id: 3, $db: "empresa" }, horas: 10 },
    { empleado: { $ref: "empleados", $id: 4, $db: "empresa" }, horas:  2 },
    { empleado: { $ref: "empleados", $id: 5, $db: "empresa" }, horas:  8 }
  ]
});

db.proyectos.insertOne({
  _id: 3, numero_proy: 3, num_of: 3,
  nombre_proy: "Publicidad",
  descripcion: "Sistema de control de la ubicación de espectaculares publicitarios en diversas zonas de la CDMX",
  fecha_inicio:  ISODate("2011-09-06"),
  fecha_entrega: ISODate("2012-08-29"),
  presupuesto: Double(298000),
  estado: "ENTREGADO",
  trabajadores: [
    { empleado: { $ref: "empleados", $id: 6, $db: "empresa" }, horas: 8 }
  ]
});
```
*Explicación:* El tipo **DBRef** (`{ $ref, $id, $db }`) es una convención estándar de MongoDB para referenciar documentos de otra colección. Al imprimirse, `mongosh` lo renderiza como `DBRef('empleados', 1, 'empresa')`. No hay integridad referencial automática — Mongo no valida que el empleado con `_id: 1` exista; eso queda como responsabilidad del programa.

Consultas finales sobre `proyectos`:

```javascript
db.proyectos.find();
```
```text
[
  {
    _id: 1, numero_proy: 1, num_of: 2,
    nombre_proy: 'Mejoramiento de Calidad',
    ...
    fecha_inicio: ISODate('2012-01-10T00:00:00.000Z'),
    presupuesto: 50000,
    estado: 'APROBADO',
    trabajadores: [
      { empleado: DBRef('empleados', 1, 'empresa'), horas: 16 },
      { empleado: DBRef('empleados', 2, 'empresa'), horas: 8  }
    ]
  },
  { _id: 2, ..., estado: 'EJECUTANDO', trabajadores: [ ...3 DBRef ] },
  { _id: 3, ..., estado: 'ENTREGADO', fecha_entrega: ISODate('2012-08-29T00:00:00.000Z'), trabajadores: [ ...1 DBRef ] }
]
```

```javascript
db.proyectos.countDocuments({ genero: "M" });
db.proyectos.countDocuments({ genero: { $nin: ["F", "M"] } });
```
```text
0   // punto 35 - el campo "genero" no existe en proyectos
3   // punto 36 - todos los documentos (ninguno tiene el campo, $nin incluye ausentes)
```
*Explicación:* El campo `genero` no está definido en el esquema de `proyectos`, por lo que la consulta del punto 35 devuelve 0. En cambio, la consulta del punto 36 con `$nin` devuelve los 3 proyectos porque `$nin` matchea también cuando el campo **no existe** (MongoDB considera que un campo ausente no está "in" el array, por lo que sí está "nin").

---

## 3. Sección 5: Dataset Real - Statewide Accountability Ratings 2021-2022

El enunciado enlaza al dataset de data.gov que actualmente redirige (404) al portal del **Texas Education Agency**. Se descargó directamente el archivo oficial:

```bash
curl -sSLo dataset.xlsx \
  "https://tea.texas.gov/texas-schools/accountability/academic-accountability/performance-reporting/statewideoverallaccountabilityratings2022.xlsx"
```

### 3.1 Conversión XLSX → CSV limpio

El archivo viene en formato Excel con algunas peculiaridades que dificultan un `mongoimport` directo:

- Los encabezados contienen saltos de línea (`School\nType`, `Number of\nStudents`, etc.).
- Los números llevan comas de miles (`"1,194"`) y celdas vacías representadas como punto (`"."`).
- Los porcentajes están guardados como fracciones (`0.408` = 40.8%).

Se escribió un script Python con `openpyxl` para normalizar estos problemas **antes** de la importación, lo que evita depender de un paso de limpieza post-import:

```python
#!/usr/bin/env python3
import csv
import openpyxl

NUMERIC_COLS = {
    "Number of Students", "Overall Score",
    "Student Achievement Score", "School Progress Score",
    "Academic Growth Score", "Relative Performance Score",
    "Closing the Gaps Score",
    "% Economically Disadvantaged", "% EB/EL Students",
}
PERCENT_COLS = {"% Economically Disadvantaged", "% EB/EL Students"}

def parse_numeric(value):
    if value is None:
        return ""
    s = str(value).strip().replace(",", "").replace("%", "")
    if s in ("", "."):
        return ""
    try:
        return float(s) if "." in s else int(s)
    except ValueError:
        return s

wb = openpyxl.load_workbook("dataset.xlsx", read_only=True, data_only=True)
ws = wb[wb.sheetnames[0]]
it = ws.iter_rows(values_only=True)
raw_headers = next(it)
headers = [h.replace("\n", " ").strip() if h else "" for h in raw_headers]

with open("escuelas.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(headers)
    for row in it:
        cleaned = []
        for header, cell in zip(headers, row):
            if header in NUMERIC_COLS:
                value = parse_numeric(cell)
                if header in PERCENT_COLS and isinstance(value, (int, float)):
                    value = round(value * 100, 2)
                cleaned.append(value)
            else:
                cleaned.append("" if cell is None else str(cell).strip())
        w.writerow(cleaned)
```
*Explicación:* Los porcentajes se multiplican por 100 para quedar en escala 0-100, consistente con la fórmula que pide la Actividad 15 (`% EB/EL Students × Number of Students / 100`). Limpiar en Python es más robusto que usar un `forEach` de `mongosh` post-import porque `mongoimport` puede inferir correctamente `int` y `double` desde un CSV ya homogéneo.

### 3.2 Importación del CSV

Se copia el CSV al contenedor y se importa con `mongoimport`:

```bash
podman cp escuelas.csv mongo-p3:/tmp/escuelas.csv
podman exec mongo-p3 mongoimport \
  --db empresa --collection escuelas \
  --type csv --headerline --drop \
  --file /tmp/escuelas.csv
```
```text
connected to: mongodb://localhost/
dropping: `empresa.escuelas`
10173 document(s) imported successfully. 0 document(s) failed to import.
```

Verificación de tipos detectados automáticamente:

```javascript
db.escuelas.findOne()
// { "Number of Students": number (246), "Overall Score": number (91),
//   "% Economically Disadvantaged": number (45.9), "Overall Rating": "A", ... }
```

### 3.3 Actividades 1 a 15

**Actividad 1: Mostrar todos los distritos/condados con calificación general (Overall Rating) igual a "A", ordenados por Overall Score descendente.**
```javascript
db.escuelas.find(
  { "Overall Rating": "A" },
  { _id: 0, County: 1, District: 1, Campus: 1, "Overall Rating": 1, "Overall Score": 1 }
).sort({ "Overall Score": -1 });
```
```text
{ District: 'POR VIDA ACADEMY', Campus: 'POR VIDA ACADEMY CORPUS CHRISTI', County: 'BEXAR',    'Overall Rating': 'A', 'Overall Score': 100 }
{ District: 'HERITAGE ACADEMY',  Campus: '',                                County: 'BEXAR',    'Overall Rating': 'A', 'Overall Score': 100 }
{ District: 'ALVIN ISD',         Campus: 'RISE',                             County: 'BRAZORIA', 'Overall Rating': 'A', 'Overall Score': 100 }
{ District: 'DENTON ISD',        Campus: 'FRED MOORE H S',                   County: 'DENTON',   'Overall Rating': 'A', 'Overall Score': 100 }
... (2749 más, total 2753)
```
*Explicación:* `find()` acepta un filtro y una proyección. La proyección `{ _id: 0, ... }` desactiva el `_id` (que por defecto se incluye) y activa los demás campos. `.sort({ "Overall Score": -1 })` ordena de mayor a menor.

**Actividad 2: Listar los 20 campus con el mayor porcentaje de estudiantes económicamente desfavorecidos.**
```javascript
db.escuelas.find(
  { Campus: { $ne: "" } },
  { _id: 0, Campus: 1, County: 1, "% Economically Disadvantaged": 1 }
).sort({ "% Economically Disadvantaged": -1 }).limit(20);
```
```text
{ Campus: 'JUVENILE DETENT CTR',                County: 'ANGELINA', '% Economically Disadvantaged': 100 }
{ Campus: 'JHW INSPIRE ACADEMY - HAYS COUNTY',  County: 'BEXAR',    '% Economically Disadvantaged': 100 }
{ Campus: 'NELSON EARLY CHILDHOOD CAMPUS',      County: 'BEXAR',    '% Economically Disadvantaged': 100 }
{ Campus: 'NEW HORIZONS',                       County: 'BELL',     '% Economically Disadvantaged': 100 }
{ Campus: 'POR VIDA ACADEMY CHARTER H S',       County: 'BEXAR',    '% Economically Disadvantaged': 100 }
... (15 más, los 20 tienen % = 100)
```
*Explicación:* El filtro `Campus: { $ne: "" }` excluye las filas que representan distritos completos (el campo `Campus` está vacío en ese caso). Muchos campus empatan al 100%, por lo que aparece un subconjunto arbitrario.

**Actividad 3: Listar los campus que tienen la palabra "High" en su tipo de escuela (School Type) y proyectar únicamente el nombre del condado, el tipo de escuela y su calificación general.**
```javascript
db.escuelas.find(
  { "School Type": /High/i },
  { _id: 0, County: 1, "School Type": 1, "Overall Rating": 1 }
);
```
```text
{ County: 'ANDERSON', 'School Type': 'High School', 'Overall Rating': 'A' }
{ County: 'ANDERSON', 'School Type': 'High School', 'Overall Rating': 'B' }
{ County: 'ANGELINA', 'School Type': 'High School', 'Overall Rating': 'Not Rated' }
... (1798 más, total 1801)
```
*Explicación:* Se usa una **expresión regular** `/High/i` para matchear cualquier valor que contenga la subcadena "High" (mayúsculas ignoradas con el flag `i`). En este dataset todas las coincidencias son literalmente `"High School"` pero el regex es más robusto ante variantes.

**Actividad 4: Buscar todas las escuelas que son del programa "Charter" (Charter = "Yes").**
```javascript
db.escuelas.find(
  { Charter: "Yes" },
  { _id: 0, District: 1, Campus: 1, County: 1, Charter: 1 }
);
```
```text
{ District: 'PINEYWOODS COMMUNITY ACADEMY',           Campus: 'PINEYWOODS COMMUNITY ACADEMY H S',  County: 'ANGELINA', Charter: 'Yes' }
{ District: 'PINEYWOODS COMMUNITY ACADEMY',           Campus: '',                                   County: 'ANGELINA', Charter: 'Yes' }
{ District: "ST MARY'S ACADEMY CHARTER SCHOOL",       Campus: "ST MARY'S ACADEMY CHARTER SCHOOL",   County: 'BEE',      Charter: 'Yes' }
{ District: 'RICHARD MILBURN ALTER HIGH SCHOOL - KILLEEN', Campus: 'RICHARD MILBURN ALTER H S (KILLEEN)', County: 'BELL', Charter: 'Yes' }
... (1053 más, total 1057)
```

**Actividad 5: Encontrar los campus que tienen menos de 500 estudiantes y un puntaje general menor a 80.**
```javascript
db.escuelas.find(
  {
    "Number of Students": { $lt: 500 },
    "Overall Score": { $lt: 80 }
  },
  { _id: 0, Campus: 1, County: 1, "Number of Students": 1, "Overall Score": 1 }
);
```
```text
{ Campus: 'FRANKSTON MIDDLE',               County: 'ANDERSON', 'Number of Students': 203, 'Overall Score': 79 }
{ Campus: 'WASHINGTON EARLY CHILDHOOD CENTER', County: 'ANDERSON', 'Number of Students': 227, 'Overall Score': 78 }
{ Campus: 'HUNTINGTON INT',                 County: 'ANGELINA', 'Number of Students': 240, 'Overall Score': 74 }
... (1050 más, total 1053)
```
*Explicación:* Cuando un objeto de filtro tiene múltiples claves, MongoDB las combina con `AND` lógico. `$lt` significa "less than".

**Actividad 6: Contar cuántos campus hay por cada tipo de escuela (School Type).**
```javascript
db.escuelas.aggregate([
  { $match: { Campus: { $ne: "" } } },
  { $group: { _id: "$School Type", total: { $sum: 1 } } },
  { $sort: { total: -1 } }
]);
```
```text
{ _id: 'Elementary',    total: 4887 }
{ _id: 'High School',   total: 1801 }
{ _id: 'Middle School', total: 1720 }
{ _id: 'Elem/Secondary', total: 558  }
```
*Explicación:* Primer uso del *pipeline de agregación*. `$group` colapsa todos los documentos con el mismo `School Type` y suma 1 por cada uno (`$sum: 1`). El `$match` previo elimina las filas de distrito.

**Actividad 7: Obtener el promedio de estudiantes matriculados por cada condado.**
```javascript
db.escuelas.aggregate([
  { $match: { "Number of Students": { $type: "number" } } },
  { $group: { _id: "$County", promedio_estudiantes: { $avg: "$Number of Students" } } },
  { $sort: { promedio_estudiantes: -1 } }
]);
```
```text
{ _id: 'MONTGOMERY', promedio_estudiantes: 1773.93 }
{ _id: 'FORT BEND',  promedio_estudiantes: 1759.84 }
{ _id: 'HARRISON',   promedio_estudiantes: 1719.81 }
{ _id: 'WALKER',     promedio_estudiantes: 1591.90 }
{ _id: 'HARRIS',     promedio_estudiantes: 1577.13 }
... (248 más, total 253)
```
*Explicación:* `$avg` ignora documentos donde el campo no es un número, pero el `$match` con `$type: "number"` lo hace explícito y filtra celdas vacías (importadas como `""`).

**Actividad 8: Mostrar los condados que tienen más de 3 campus registrados.**
```javascript
db.escuelas.aggregate([
  { $match: { Campus: { $ne: "" } } },
  { $group: { _id: "$County", total_campus: { $sum: 1 } } },
  { $match: { total_campus: { $gt: 3 } } },
  { $sort: { total_campus: -1 } }
]);
```
```text
{ _id: 'HARRIS',     total_campus: 1060 }
{ _id: 'DALLAS',     total_campus: 767  }
{ _id: 'BEXAR',      total_campus: 562  }
{ _id: 'TARRANT',    total_campus: 521  }
{ _id: 'HIDALGO',    total_campus: 415  }
... (209 más, total 214)
```
*Explicación:* Aquí aparecen **dos `$match`**: el primero antes de agrupar (para excluir filas de distrito), el segundo después de agrupar (para filtrar sobre el conteo calculado). Esta es la clave para post-filtrar resultados agregados.

**Actividad 9: Listar las escuelas que lograron obtener la distinción "Earned" tanto en Matemáticas como en Ciencias.**
```javascript
db.escuelas.find(
  {
    "Distinction Mathematics": "Earned",
    "Distinction Science": "Earned"
  },
  { _id: 0, Campus: 1, County: 1, "Distinction Mathematics": 1, "Distinction Science": 1 }
);
```
```text
{ Campus: 'CAYUGA EL',     County: 'ANDERSON', 'Distinction Mathematics': 'Earned', 'Distinction Science': 'Earned' }
{ Campus: 'CAYUGA H S',    County: 'ANDERSON', 'Distinction Mathematics': 'Earned', 'Distinction Science': 'Earned' }
{ Campus: 'PALESTINE H S', County: 'ANDERSON', 'Distinction Mathematics': 'Earned', 'Distinction Science': 'Earned' }
{ Campus: 'FRANKSTON EL',  County: 'ANDERSON', 'Distinction Mathematics': 'Earned', 'Distinction Science': 'Earned' }
... (1031 más, total 1035)
```
*Explicación:* La conjunción se implementa simplemente listando ambas condiciones en el objeto de filtro (se combinan con AND).

**Actividad 10: Calcular el puntaje general (Overall Score) máximo y mínimo, agrupado por Tipo de Escuela.**
```javascript
db.escuelas.aggregate([
  { $match: { "Overall Score": { $type: "number" } } },
  { $group: {
      _id: "$School Type",
      score_max: { $max: "$Overall Score" },
      score_min: { $min: "$Overall Score" }
  } },
  { $sort: { _id: 1 } }
]);
```
```text
{ _id: 'District',       score_max: 100, score_min: 41 }
{ _id: 'Elem/Secondary', score_max: 99,  score_min: 55 }
{ _id: 'Elementary',     score_max: 100, score_min: 41 }
{ _id: 'High School',    score_max: 100, score_min: 47 }
{ _id: 'Middle School',  score_max: 98,  score_min: 45 }
```
*Explicación:* `$max` y `$min` son acumuladores paralelos en el mismo `$group`, lo que permite calcular varias métricas agregadas en una sola pasada.

**Actividad 11: Por cada región educativa (County), mostrar en un solo reporte: total de campus, promedio de Overall Score y total acumulado de estudiantes matriculados.**
```javascript
db.escuelas.aggregate([
  { $match: { Campus: { $ne: "" } } },
  { $group: {
      _id: "$County",
      total_campus: { $sum: 1 },
      promedio_score: { $avg: "$Overall Score" },
      total_estudiantes: { $sum: "$Number of Students" }
  } },
  { $sort: { total_campus: -1 } }
]);
```
```text
{ _id: 'HARRIS',  total_campus: 1060, promedio_score: 85.48, total_estudiantes: 880036 }
{ _id: 'DALLAS',  total_campus: 767,  promedio_score: 82.01, total_estudiantes: 492831 }
{ _id: 'BEXAR',   total_campus: 562,  promedio_score: 81.93, total_estudiantes: 341761 }
{ _id: 'TARRANT', total_campus: 521,  promedio_score: 83.73, total_estudiantes: 344096 }
{ _id: 'HIDALGO', total_campus: 415,  promedio_score: 89.19, total_estudiantes: 251101 }
... (248 más, total 253)
```
*Explicación:* Un `$group` puede combinar cualquier cantidad de acumuladores heterogéneos (`$sum`, `$avg`, `$max`, etc.). El condado HARRIS agrupa el área metropolitana de Houston, lo que explica su magnitud.

**Actividad 12: Identificar el Top 5 de condados con mayor cantidad total de estudiantes, excluyendo previamente las escuelas que son "Charter".**
```javascript
db.escuelas.aggregate([
  { $match: { Charter: "No", "Number of Students": { $type: "number" } } },
  { $group: { _id: "$County", total_estudiantes: { $sum: "$Number of Students" } } },
  { $sort: { total_estudiantes: -1 } },
  { $limit: 5 }
]);
```
```text
{ _id: 'HARRIS',  total_estudiantes: 1664826 }
{ _id: 'DALLAS',  total_estudiantes: 823640  }
{ _id: 'TARRANT', total_estudiantes: 670166  }
{ _id: 'BEXAR',   total_estudiantes: 599846  }
{ _id: 'COLLIN',  total_estudiantes: 458856  }
```
*Explicación:* El `$match` se aplica **antes** del `$group` para que el filtrado aproveche cualquier índice disponible (mejor desempeño). `$limit` corta al top-5 después del ordenamiento.

**Actividad 13: Agrupar las escuelas por su calificación general (Overall Rating) y crear un arreglo sin duplicados (`$addToSet`) de los condados que obtuvieron dicha calificación.**
```javascript
db.escuelas.aggregate([
  { $match: { "Overall Rating": { $nin: ["", null] } } },
  { $group: {
      _id: "$Overall Rating",
      condados: { $addToSet: "$County" },
      total_condados: { $sum: 1 }
  } },
  { $project: {
      _id: 1,
      muestra_condados: { $slice: ["$condados", 10] },
      num_condados_unicos: { $size: "$condados" }
  } },
  { $sort: { _id: 1 } }
]);
```
```text
{ _id: 'A', num_condados_unicos: 206, muestra_condados: ['GLASSCOCK','LAMPASAS','FISHER','HOWARD','MCMULLEN','PARMER','RED RIVER','ATASCOSA','DENTON','HARTLEY'] }
{ _id: 'B', num_condados_unicos: 237, muestra_condados: ['DELTA','POTTER','CONCHO','FANNIN','CASS','GONZALES','COLLINGSWORTH','FORT BEND','WEBB','FALLS'] }
{ _id: 'C', num_condados_unicos: 189, muestra_condados: ['RED RIVER','HOWARD','ATASCOSA','DENTON','DIMMIT','GUADALUPE','LA SALLE','COLEMAN','SAN JACINTO','GREGG'] }
{ _id: 'Not Rated', num_condados_unicos: 92 }
{ _id: 'Not Rated: Data Integrity Issues', num_condados_unicos: 1, muestra_condados: ['ERATH'] }
{ _id: 'Not Rated: Data Under Review',     num_condados_unicos: 2, muestra_condados: ['HARRISON','LUBBOCK'] }
{ _id: 'Not Rated: Senate Bill 1365',      num_condados_unicos: 116 }
```
*Explicación:* `$addToSet` acumula valores **únicos**, a diferencia de `$push` que acumula todos (incluyendo duplicados). Para no saturar el reporte con arreglos de 200+ elementos, se usa `$slice` para mostrar solo los primeros 10 y `$size` para reportar el total.

**Actividad 14: Obtener el promedio del puntaje de crecimiento académico (Academic Growth Score) por tipo de escuela, filtrando para ignorar aquellos documentos que no tengan este dato o esté vacío.**
```javascript
db.escuelas.aggregate([
  { $match: { "Academic Growth Score": { $type: "number" } } },
  { $group: {
      _id: "$School Type",
      promedio_growth: { $avg: "$Academic Growth Score" },
      muestras: { $sum: 1 }
  } },
  { $sort: { promedio_growth: -1 } }
]);
```
```text
{ _id: 'Elementary',     promedio_growth: 84.68, muestras: 4354 }
{ _id: 'District',       promedio_growth: 82.34, muestras: 1185 }
{ _id: 'Elem/Secondary', promedio_growth: 81.94, muestras: 426  }
{ _id: 'Middle School',  promedio_growth: 79.26, muestras: 1687 }
{ _id: 'High School',    promedio_growth: 76.10, muestras: 1348 }
```
*Explicación:* El filtro `$type: "number"` es más estricto que `$ne: null`, porque `mongoimport` representa celdas vacías como cadena vacía `""`, no como `null`. Sin este filtro, los promedios serían incorrectos.

**Actividad 15: Calcular la suma total de estudiantes del programa EB/EL (`% EB/EL Students × Number of Students / 100`) para todo el estado, agrupado por calificación general (Overall Rating).**
```javascript
db.escuelas.aggregate([
  { $match: {
      "Overall Rating": { $nin: ["", null] },
      "% EB/EL Students":   { $type: "number" },
      "Number of Students": { $type: "number" }
  } },
  { $group: {
      _id: "$Overall Rating",
      total_eb_el: {
        $sum: {
          $divide: [
            { $multiply: ["$% EB/EL Students", "$Number of Students"] },
            100
          ]
        }
      }
  } },
  { $project: { _id: 1, total_eb_el: { $round: ["$total_eb_el", 2] } } },
  { $sort: { _id: 1 } }
]);
```
```text
{ _id: 'A',                                total_eb_el:  499830.48 }
{ _id: 'B',                                total_eb_el: 1396549.14 }
{ _id: 'C',                                total_eb_el:  345034.98 }
{ _id: 'Not Rated',                        total_eb_el:    4069    }
{ _id: 'Not Rated: Data Integrity Issues', total_eb_el:     682.2  }
{ _id: 'Not Rated: Data Under Review',     total_eb_el:    1453.92 }
{ _id: 'Not Rated: Senate Bill 1365',      total_eb_el:   95459.26 }
```
*Explicación:* Dentro de un acumulador `$sum` se puede anidar una expresión aritmética completa con `$multiply`, `$divide`, etc. El `$round` final limpia la presentación a 2 decimales. La categoría con más estudiantes EB/EL (aprendices de inglés) es la **B**, con ~1.4 millones.

---

## 4. Conclusiones

La práctica recorre el ciclo completo de MongoDB: modelado (oficinas, empleados, proyectos), inserción, validación con **JSON Schema**, consultas con operadores lógicos (`$nor`, `$in`, `$nin`) y finalmente **agregación compuesta** sobre un dataset real de más de 10 mil documentos.

Hay dos decisiones prácticas que vale la pena destacar:

1. **Limpieza previa vs limpieza posterior.** Al normalizar el CSV en Python antes de importar, se evita escribir un script de `forEach` en `mongosh` para reparar tipos. Esto también permite que `mongoimport` infiera los tipos correctamente sin `--columnsHaveTypes`.

2. **JSON Schema con `collMod` vs al crear.** Cuando ya existen documentos, `collMod` con `validationLevel: "moderate"` es la forma segura de agregar reglas sin romper la colección. Cuando la colección es nueva, meter el validador directamente en `createCollection` es más limpio.

La riqueza del *aggregation framework* (en especial `$group` con múltiples acumuladores y expresiones aritméticas anidadas) permite resolver consultas complejas sin salirse del servidor, algo que en un modelo relacional normalmente requeriría subconsultas o vistas materializadas.
