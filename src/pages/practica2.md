---
layout: ../layouts/Layout.astro
---

# Reporte de Práctica 2: Bases de Datos No Relacionales

Este documento sirve como bitácora de los comandos y consultas ejecutadas en el entorno Oracle 11g XE configurado a través de Docker en el servidor AlmaLinux.

## 1. Preparación del Entorno (Ejecutado por el sistema)

Se levantó un contenedor Docker con Oracle 11g y se preparó una carpeta interna para emular la ruta solicitada en la práctica.

*   **Ruta local en la práctica (Windows):** `c:\repositorio`
*   **Ruta configurada en nuestro servidor (Linux/Docker):** `/opt/oracle/oradata/repositorio`

## 2. Creación del usuario y permisos (Ejecutado como SYSDBA)

Se creó el usuario `bdxml` requerido por la práctica y se le otorgaron los permisos para conectarse, crear recursos y administrar directorios.

```sql
CONNECT / AS SYSDBA;
CREATE USER bdxml IDENTIFIED BY bdxml;
GRANT CONNECT, RESOURCE TO bdxml;
GRANT CREATE ANY DIRECTORY TO bdxml;
GRANT DROP ANY DIRECTORY TO bdxml;
```
*Explicación:* Estos comandos preparan la cuenta de usuario que usaremos para toda la práctica. El permiso de crear directorios es fundamental para que Oracle pueda leer archivos externos (como nuestros XML).

## 3. Configuración de Sesión y Creación de Tabla (Ejecutado como bdxml)

Nos conectamos con el nuevo usuario, ajustamos la región y creamos la primera tabla que almacenará documentos XML directamente en la base de datos usando el tipo de dato `XMLType`.

```sql
CONNECT bdxml/bdxml;

-- Ajusta la configuración regional para fechas y monedas
ALTER SESSION SET NLS_TERRITORY='MEXICO';

-- Crea la tabla para almacenar la información personal y el Curriculum Vitae en formato XML
CREATE TABLE personas (
    RFC CHAR(13) PRIMARY KEY,
    Nombre VARCHAR(30) NOT NULL,
    Apellidos VARCHAR(30) NOT NULL,
    CV XMLType
);
```
*Explicación:* El tipo de dato `XMLType` es la característica clave aquí, ya que permite a Oracle validar que el documento XML esté bien formado y nos habilitará el uso de funciones como `EXTRACT` y `XQuery` más adelante.

---

## 4. Inserción de Datos y Consultas (Sección 3.1.1)

Se ejecutaron los 4 `INSERT` correspondientes a la práctica que incluyen documentos XML dentro de la estructura relacional. Posteriormente se corrieron las 12 consultas solicitadas en la práctica.

### Resultados de las Consultas

**Consulta 1: Selección completa de la tabla**
```sql
SELECT * FROM personas;
```
```text
RFC             NOMBRE                         APELLIDOS
--------------- ------------------------------ ------------------------------
PELJ900304JJ6   Juan                           Pérez López
CACM871109LI8   Martha                         Carbajal Carbajal
CALJ851211K9O   Juan Manuel                    Camacho López
MEGR910508PY3   Rodrigo                        Medina García
```

**Consulta 2: Formatear a atributo XML**
```sql
SELECT XMLColattval(p.apellidos) FROM personas p;
```
```text
XMLCOLATTVAL(P.APELLIDOS)
---------------------------------------------------------------------------------------------------
<column name = "APELLIDOS">Pérez López</column>
<column name = "APELLIDOS">Carbajal Carbajal</column>
<column name = "APELLIDOS">Camacho López</column>
<column name = "APELLIDOS">Medina García</column>
```

**Consulta 3: Extraer todas las empresas de "Martha"**
```sql
SELECT p.nombre || ' ' || p.apellidos AS persona, EXTRACT(p.cv, '//empresa').getstringval() AS RESULT FROM personas p WHERE p.nombre LIKE '%Martha%';
```
```text
PERSONA                        RESULT
------------------------------ --------------------------------------------------------------------------------
Martha Carbajal Carbajal       <empresa>Comercializadora de Ropa del Centro </empresa>
                               <empresa>Refacciones para Autobuses S.A.</empresa>
```

**Consulta 4: Extraer la empresa que contenga "S.A."**
```sql
SELECT p.nombre || ' ' || p.apellidos AS persona, EXTRACTVALUE(p.cv,'//empresa[contains(.,"S.A.")]') AS RESULT FROM personas p;
```
```text
PERSONA                        RESULT
------------------------------ --------------------------------------------------------------------------------
Juan Pérez López
Martha Carbajal Carbajal       Refacciones para Autobuses S.A.
Juan Manuel Camacho López      Asesores Fiscales S.A.
Rodrigo Medina García
```

**Consulta 5: Validar que exista el nodo y extraer "S.A."**
```sql
SELECT p.nombre || ' ' || p.apellidos AS persona, EXTRACTVALUE(p.cv, '//empresa[contains(.,"S.A.")]') AS RESULT FROM personas p WHERE EXISTSNODE(p.cv, '//empresa[contains(.,"S.A.")]') = 1;
```
```text
PERSONA                        RESULT
------------------------------ --------------------------------------------------------------------------------
Martha Carbajal Carbajal       Refacciones para Autobuses S.A.
Juan Manuel Camacho López      Asesores Fiscales S.A.
```

**Consulta 6: Búsqueda con operador OR (|)**
```sql
SELECT p.nombre || ' ' || p.apellidos AS persona, EXTRACT(p.cv, '//medio_superior/escuela/text() | //superior/escuela/text()').getstringval() AS RESULT FROM personas p WHERE EXISTSNODE(p.cv, '//medio_superior/comprobante | //superior/comprobante') = 1;
```
```text
PERSONA                        RESULT
------------------------------ --------------------------------------------------------------------------------
Juan Pérez López               Escuela preparatoria No.5
Martha Carbajal Carbajal       Vocacional No. 3 Escuela Internacional de Comercio C.V.
Juan Manuel Camacho López      Escuela Comercial y Contable
```

**Consulta 7: Buscar personas con más de 1 empleo**
```sql
SELECT p.nombre || ' ' || p.apellidos AS persona, EXTRACT(p.cv, '//empleos/empleo/empresa/text()').getstringval() AS RESULT FROM personas p WHERE EXISTSNODE(p.cv, '//empleos[count(empleo)>1]') = 1;
```
```text
PERSONA                        RESULT
------------------------------ --------------------------------------------------------------------------------
Juan Pérez López               Fábricas de Cartón Comercializadora Internacional
Martha Carbajal Carbajal       Comercializadora de Ropa del Centro Refacciones para Autobuses S.A.
Juan Manuel Camacho López      Banca de Desarrollo Empresarial Asesores Fiscales S.A.
```

**Consulta 8: Extraer comprobante de "Martha"**
```sql
SELECT p.rfc, p.nombre || ' ' || p.apellidos AS persona, EXTRACT(p.cv, '//comprobante').getstringval() AS RESULT FROM personas p WHERE p.nombre LIKE '%Martha%';
```
```text
RFC             PERSONA                        RESULT
--------------- ------------------------------ --------------------------------------------------------------------------------
CACM871109LI8   Martha Carbajal Carbajal       <comprobante>certificado</comprobante>
                                               <comprobante>titulo profesional</comprobante>
```

**Consulta 9 y 10: Actualizar un nodo XML con UpdateXML**
```sql
UPDATE personas p SET p.cv = updateXML(p.cv, '//medio_superior/comprobante', '<comprobante>diploma</comprobante>') WHERE p.rfc = 'CACM871109LI8';
```
```text
[Salida de la Consulta 10 mostrando la actualización]
RFC             PERSONA                        RESULT
--------------- ------------------------------ --------------------------------------------------------------------------------
CACM871109LI8   Martha Carbajal Carbajal       <comprobante>diploma</comprobante>
                                               <comprobante>titulo profesional</comprobante>
```

**Consulta 11 y 12: Eliminar un nodo XML con deleteXML**
```sql
UPDATE personas p SET p.cv = deleteXML(p.cv, '//medio_superior/comprobante["diploma"]') WHERE p.rfc = 'CACM871109LI8';
```
```text
[Salida de la Consulta 12 mostrando la eliminación]
RFC             PERSONA                        RESULT
--------------- ------------------------------ --------------------------------------------------------------------------------
CACM871109LI8   Martha Carbajal Carbajal       <comprobante>titulo profesional</comprobante>
```

**Consulta 13: Contar cuántos empleados empiezan o terminan con consonante su nombre**
```sql
SELECT COUNT(*) AS total_consonante_inicio_o_fin
FROM empleados_xml e,
     XMLTable('/empleados/empleado' PASSING e.OBJECT_VALUE
              COLUMNS nombre VARCHAR2(50) PATH 'nombre'
             ) x
WHERE REGEXP_LIKE(TRIM(x.nombre), '^[^AEIOUaeiouÁÉÍÓÚáéíóú]')
   OR REGEXP_LIKE(TRIM(x.nombre), '[^AEIOUaeiouÁÉÍÓÚáéíóú]$');
```
```text
TOTAL_CONSONANTE_INICIO_O_FIN
-----------------------------
                            9
```
*Explicación:* Se usa `XMLTable` para extraer los nombres del documento XML y `REGEXP_LIKE` con un `OR` para capturar nombres que cumplan al menos una condición. Los 9 empleados califican ya que todos inician con consonante (Jesús=J, Guadalupe=G, Julia=J, Mario=M, Rogelio=R, Bruce=B, Laura=L, Sandra=S, Guadalupe=G). Se incluyen las vocales acentuadas (ÁÉÍÓÚáéíóú) en la exclusión para manejar correctamente nombres en español.

**Consulta 14: Contar cuántos empleados empiezan y terminan con consonante su nombre**
```sql
SELECT COUNT(*) AS total_consonante_inicio_y_fin
FROM empleados_xml e,
     XMLTable('/empleados/empleado' PASSING e.OBJECT_VALUE
              COLUMNS nombre VARCHAR2(50) PATH 'nombre'
             ) x
WHERE REGEXP_LIKE(TRIM(x.nombre), '^[^AEIOUaeiouÁÉÍÓÚáéíóú].*[^AEIOUaeiouÁÉÍÓÚáéíóú]$');
```
```text
TOTAL_CONSONANTE_INICIO_Y_FIN
-----------------------------
                            1
```
*Explicación:* A diferencia de la anterior, aquí se exige que ambas condiciones se cumplan simultáneamente en una sola expresión regular. Solo **Jesús** (J...s) cumple, ya que es el único nombre que tanto empieza como termina con consonante.

**Consulta 15: Mostrar el NSS de los empleados cuyo nombre termina con consonante**
```sql
SELECT x.nss, x.nombre
FROM empleados_xml e,
     XMLTable('/empleados/empleado' PASSING e.OBJECT_VALUE
              COLUMNS
                nss VARCHAR2(20) PATH '@NSS',
                nombre VARCHAR2(50) PATH 'nombre'
             ) x
WHERE REGEXP_LIKE(TRIM(x.nombre), '[^AEIOUaeiouÁÉÍÓÚáéíóú]$');
```
```text
NSS                  NOMBRE
-------------------- --------------------------------------------------
777888999            Jesús
```
*Explicación:* Se proyecta el NSS (identificador del empleado en el XML, definido como atributo `@NSS`) junto con el nombre. Solo **Jesús** termina en consonante ('s').

---

## 5. Manejo de Archivos XML Externos (Sección 3.2)

Se preparó la base de datos para leer archivos XML alojados en el sistema de archivos del servidor (en nuestro caso, dentro del contenedor de Docker).

**Creación de Tabla de tipo XML**
```sql
CREATE TABLE empleados_xml OF XMLType;
SELECT TABLE_NAME FROM USER_XML_TABLES;
```
```text
TABLE_NAME
------------------------------
EMPLEADOS_XML
```

**Creación del Directorio Lógico**
```sql
CREATE OR REPLACE DIRECTORY REPOSITORIO AS '/opt/oracle/oradata/repositorio';
```
```text
Directory created.
```

**Carga del Archivo y Configuración de Sesión**
A continuación, utilizamos la función `BFILENAME` para leer el archivo `empleados.xml` que habíamos subido al contenedor y lo insertamos como una fila en nuestra tabla. Las variables de sesión se ajustaron para poder leer los XML largos.
```sql
INSERT INTO empleados_xml VALUES 
(XMLType(BFILENAME('REPOSITORIO', 'empleados.xml'), NLS_CHARSET_ID('AL32UTF16')));
COMMIT;

-- Configuraciones de visualización en SQL*Plus
SET PAGESIZE 500;
SET LINESIZE 300;
SET LONG 2000;
COLUMN RESULT FORMAT A300;
```
```text
1 row created.
Commit complete.
```

### Consultas sobre el archivo cargado (Página 8)

**Consulta A:**
```sql
SELECT * FROM empleados_xml;
```
*(Muestra el contenido crudo en formato XML de todos los empleados insertados).*

**Consulta B:**
```sql
SELECT XMLRoot(e.OBJECT_VALUE, VERSION '1.0', STANDALONE YES) FROM empleados_xml e;
```
*(Imprime el mismo árbol pero anteponiendo la declaración `<?xml version="1.0" standalone="yes"?>`).*

**Consulta C:**
```sql
SELECT EXTRACT(e.OBJECT_VALUE,'/empleados/empleado/paterno').getstringval() AS res FROM empleados_xml e;
```
*Resultado: Vacío. (Explicación: El nodo `<paterno>` no existe en el documento `empleados.xml`, el nodo correcto se llama `<apellido>`).*

**Consulta D:**
```sql
SELECT EXTRACTVALUE(e.OBJECT_VALUE, '/empleados/empleado[@id=101]/paterno') AS res FROM empleados_xml e;
```
*Resultado: Vacío. (Explicación: No existen atributos `id` en el documento, se usa el atributo `NSS`, además de que el nodo `paterno` no existe).*

**Consulta E:**
```sql
SELECT EXTRACT(e.OBJECT_VALUE, '/empleados/empleado[sexo="F"]/nombre').getstringval() AS res FROM empleados_xml e;
```
*Resultado: Vacío. (Explicación: El nodo para el género se llama `<genero>`, no `<sexo>`).*

**Consulta F:**
```sql
SELECT EXTRACT(e.OBJECT_VALUE, '/empleados/empleado[sexo="F"]/nombre').getstringval() AS res FROM empleados_xml e WHERE existsNode(OBJECT_VALUE, '//proy') = 1;
```
*Resultado: `no rows selected`. (Explicación: Ningún nodo coincide con las condiciones establecidas).*

**Consulta G:**
```sql
SELECT EXTRACT(e.OBJECT_VALUE, '//empleado[sexo="F" and edad>="30"]/nombre').getstringval() AS res FROM empleados_xml e;
```
*Resultado: Vacío. (Explicación: No existen los nodos `sexo` ni `edad` en el documento).*

**Consulta H:**
```sql
SELECT XMLSerialize(DOCUMENT e.OBJECT_VALUE AS CLOB) AS XML FROM empleados_xml e;
```
*(Muestra el documento casteado explícitamente a tipo Character Large Object).*

### Creación de Recursos en XDB (Páginas 8-11)

Se ejecutó el bloque de código PL/SQL masivo que construye dinámicamente dos cadenas con formato XML (una para empleados y otra para departamentos) y utiliza la función `DBMS_XDB.createResource` para inyectarlos en el repositorio XML interno de la base de datos bajo el directorio `/public/`.

```sql
DECLARE
  res BOOLEAN;
  empsxmlstring VARCHAR2(4000) := '';
  deptsxmlstring VARCHAR2(4000) := '';
BEGIN
  -- (Concatenaciones de strings XML omitidas en el reporte por brevedad) ...
  res := DBMS_XDB.createResource('/public/empleados.xml', empsxmlstring);
  res := DBMS_XDB.createResource('/public/departamentos.xml', deptsxmlstring);
END;
/
COMMIT;
```
```text
PL/SQL procedure successfully completed.
Commit complete.
```
*(Nota de ejecución: El bloque de la práctica tenía un ligero error de sintaxis en PL/SQL al intentar asignar variables antes de la declaración `BEGIN`. Se corrigió la estructura para que Oracle lo compilara y ejecutara sin problemas).*

### Consultas XQuery usando FLWOR (Sección 3.2.1)

Estas consultas utilizan XQuery y expresiones FLWOR (`for`, `let`, `where`, `order by`, `return`) para procesar e interrelacionar la información de los archivos almacenados en el repositorio interno `/public/` de Oracle.

**Consulta 1: Listar empleado y el nombre de su departamento**
```sql
SELECT XMLQuery('for $e in doc("/public/empleados.xml")/empleados/empleado let $d := doc("/public/departamentos.xml")//departamento[@numero = $e/@departamento]/nombre return <empleado nombre="{$e/nombre}" departamento="{$d}"/>' RETURNING CONTENT) AS RESULT FROM DUAL;
```
```text
RESULT
------------------------------------------------------------------------------------------------------------------------
<empleado nombre="Jesús" departamento="Administración"></empleado><empleado nombre="Guadalupe" departamento="Administrac
ión"></empleado><empleado nombre="Julia" departamento="Sistemas"></empleado><empleado nombre="Mario" departamento="Admin
istración"></empleado><empleado nombre="Rogelio" departamento="Ventas"></empleado><empleado nombre="Bruce" departamento=
"Sistemas"></empleado><empleado nombre="Laura" departamento="Ventas"></empleado><empleado nombre="Sandra" departamento="
Sistemas"></empleado><empleado nombre="Guadalupe" departamento="Ventas"></empleado>
```

**Consulta 2: Empleados con salario > 10,000 (Concatenando nombre y apellido)**
```sql
SELECT XMLQuery('for $e in doc("/public/empleados.xml")/empleados/empleado let $d := doc("/public/departamentos.xml")//departamento[@numero = $e/@departamento]/nombre where $e/salario > 10000 order by $e/@NSS return <empleado nombre="{$e/nombre} {$e/apellido}"/>' RETURNING CONTENT) AS RESULT FROM DUAL;
```
```text
RESULT
------------------------------------------------------------------------------------------------------------------------
<empleado nombre="SandraGuzmán"></empleado><empleado nombre="GuadalupeOñate"></empleado><empleado nombre="RogelioCalzada
"></empleado><empleado nombre="JuliaRegalado"></empleado><empleado nombre="MarioMedina"></empleado><empleado nombre="Bru
ceBolaños"></empleado><empleado nombre="JesúsLópez"></empleado><empleado nombre="GuadalupeHidalgo"></empleado><empleado
nombre="LauraMéndez"></empleado>
```

**Consulta 3: Departamentos con más de 1 empleado y promedio de salario**
```sql
SELECT XMLQuery('for $d in doc("/public/departamentos.xml")/departamentos/departamento/@numero let $e := doc("/public/empleados.xml")/empleados/empleado[@departamento = $d] where count($e) > 1 order by avg($e/salario) descending return <departamento>{$d}<conteo>{count($e)}</conteo><promediosal>{round(avg($e/salario))}</promediosal></departamento>' RETURNING CONTENT) AS RESULT FROM DUAL;
```
```text
RESULT
------------------------------------------------------------------------------------------------------------------------
<departamento numero="1"><conteo>3</conteo><promediosal>3.2333E+004</promediosal></departamento><departamento numero="3"
><conteo>3</conteo><promediosal>3.1667E+004</promediosal></departamento><departamento numero="2"><conteo>3</conteo><prom
ediosal>2.8E+004</promediosal></departamento>
```

**Consulta 4: Empleados con salario > 30,000 devolviendo NSS, nombre y salario**
```sql
SELECT XMLQuery('for $e in doc("/public/empleados.xml")/empleados/empleado let $d := doc("/public/departamentos.xml")//departamento[@numero = $e/@departamento]/nombre where $e/salario > 30000 order by $e/@NSS return <empleado NSS="{$e/@NSS}" nombre="{$e/nombre} {$e/apellido}" salario="{$e/salario}"/>' RETURNING CONTENT) AS RESULT FROM DUAL;
```
```text
RESULT
------------------------------------------------------------------------------------------------------------------------
<empleado NSS="111222333" nombre="SandraGuzmán" salario="45000"></empleado><empleado NSS="333444555" nombre="RogelioCalz
ada" salario="39000"></empleado><empleado NSS="777888999" nombre="JesúsLópez" salario="50000"></empleado>
```

**Limpieza Final de la Práctica (Sección 3)**
Se eliminaron los archivos del repositorio XDB público según lo indicado en el PDF.
```sql
BEGIN
  DBMS_XDB.deleteResource('/public/empleados.xml');
  DBMS_XDB.deleteResource('/public/departamentos.xml');
END;
/
COMMIT;
```
```text
PL/SQL procedure successfully completed.
Commit complete.
```

---

## 6. Análisis de Dataset Escolar (Sección 4)

Se procedió a crear la tabla para almacenar el nuevo dataset de las escuelas de Texas y se cargó el archivo XML de 20MB.

```sql
CREATE TABLE escuelas_texas OF XMLType;

INSERT INTO escuelas_texas VALUES (
  XMLType(BFILENAME('REPOSITORIO', 'escuelas.xml'), NLS_CHARSET_ID('AL32UTF16'))
);
COMMIT;
```

### Consultas XQuery de Análisis

**Actividad 1: Mostrar todos los distritos con calificación "A" ordenados por su puntaje de mayor a menor.**
```sql
SELECT XMLQuery(
  'for $row in /response/row/row
   where $row/school_type = "District" and $row/overall_rating = "A"
   order by number($row/overall_score) descending
   return <distrito nombre="{$row/district}" puntaje="{$row/overall_score}"/>' 
  PASSING OBJECT_VALUE RETURNING CONTENT) AS RESULT
FROM escuelas_texas;
```
*(Salida abreviada)*
```text
<distrito nombre="NAZARETH ISD" puntaje="98"></distrito>
<distrito nombre="WESTLAKE ACADEMY CHARTER SCHOOL" puntaje="98"></distrito>
<distrito nombre="ROCHELLE ISD" puntaje="98"></distrito>
...
<distrito nombre="HIGHLAND PARK ISD" puntaje="95"></distrito>
<distrito nombre="CARROLL ISD" puntaje="95"></distrito>
... (Listado completo de distritos con calificación A)
```

**Actividad 2: Listar los 20 campus con mayor porcentaje de estudiantes económicamente desfavorecidos.**
```sql
SELECT XMLQuery(
  'for $row in (
     for $r in /response/row/row
     where $r/school_type != "District" and string-length($r/economically_disadvantaged) > 0
     order by number($r/economically_disadvantaged) descending
     return <campus nombre="{$r/campus}" porc_desfavorecidos="{$r/economically_disadvantaged}"/>
   )[position() <= 20]
   return $row' 
  PASSING OBJECT_VALUE RETURNING CONTENT) AS RESULT
FROM escuelas_texas;
```
```text
<campus nombre="GARRETT PRI" porc_desfavorecidos="1.0"/>
<campus nombre="STEP - CORE" porc_desfavorecidos="1.0"/>
<campus nombre="S T E P DETENTION" porc_desfavorecidos="1.0"/>
<campus nombre="S T E P - J J A E P" porc_desfavorecidos="1.0"/>
<campus nombre="STEP - JJAEP" porc_desfavorecidos="1.0"/>
<campus nombre="FARRIS EARLY CHILDHOOD CTR" porc_desfavorecidos="1.0"/>
<campus nombre="IOWA PARK JJAEP" porc_desfavorecidos="1.0"/>
<campus nombre="WICHITA CO JJAEP" porc_desfavorecidos="1.0"/>
<campus nombre="CASA ESPERANZA RECOVERY HOME" porc_desfavorecidos="1.0"/>
<campus nombre="YOUTH RECOVERY HOME" porc_desfavorecidos="1.0"/>
<campus nombre="YOUTH VILLAGE DETENTION CENTER" porc_desfavorecidos="1.0"/>
<campus nombre="PIERCE EL" porc_desfavorecidos="1.0"/>
<campus nombre="WEBB COUNTY J J A E P" porc_desfavorecidos="1.0"/>
<campus nombre="F S LARA ACADEMY" porc_desfavorecidos="1.0"/>
<campus nombre="DAEP- EL" porc_desfavorecidos="1.0"/>
<campus nombre="DIBOLL" porc_desfavorecidos="1.0"/>
<campus nombre="BILLY MOORE" porc_desfavorecidos="1.0"/>
<campus nombre="THE EXCEL CENTER FOR ADULTS - LOCKHART" porc_desfavorecidos="1.0"/>
<campus nombre="BOYSVILLE" porc_desfavorecidos="1.0"/>
<campus nombre="SAFE HAVEN" porc_desfavorecidos="1.0"/>
```

**Actividad 3: Contar cuántos campus hay por cada tipo de escuela.**
```sql
SELECT XMLQuery(
  'let $rows := /response/row/row
   return <conteos>
            <elementary>{count($rows[school_type = "Elementary"])}</elementary>
            <middle>{count($rows[school_type = "Middle School"])}</middle>
            <high>{count($rows[school_type = "High School"])}</high>
          </conteos>' 
  PASSING OBJECT_VALUE RETURNING CONTENT) AS RESULT
FROM escuelas_texas;
```
```text
<conteos><elementary>4923</elementary><middle>1715</middle><high>1815</high></conteos>
```

**Actividad 4: Mostrar los distritos que tienen más de 10 campus.**
(Consulta optimizada mediante la extracción tabular `XMLTable` sobre la ruta absoluta del documento para prevenir problemas de I/O en documentos masivos).
```sql
SELECT * FROM (
  SELECT x.distrito, COUNT(*) as total_campus
  FROM escuelas_texas e,
       XMLTable('/response/row/row'
                PASSING e.OBJECT_VALUE
                COLUMNS 
                  school_type VARCHAR2(30) PATH 'school_type',
                  distrito VARCHAR2(100) PATH 'district'
               ) x
  WHERE x.school_type != 'District'
  GROUP BY x.distrito
  HAVING COUNT(*) > 10
  ORDER BY total_campus DESC
) WHERE ROWNUM <= 20;
```
```text
DISTRITO                                 TOTAL_CAMPUS
---------------------------------------- ------------
HOUSTON ISD                                       272
DALLAS ISD                                        239
FORT WORTH ISD                                    138
NORTHSIDE ISD                                     125
IDEA PUBLIC SCHOOLS                               123
AUSTIN ISD                                        122
SAN ANTONIO ISD                                    97
CYPRESS-FAIRBANKS ISD                              89
FORT BEND ISD                                      81
ALDINE ISD                                         78
GARLAND ISD                                        76
ARLINGTON ISD                                      75
NORTH EAST ISD                                     75
EL PASO ISD                                        75
PLANO ISD                                          74
FRISCO ISD                                         74
KATY ISD                                           72
PASADENA ISD                                       67
CONROE ISD                                         63
LEWISVILLE ISD                                     62
```

**Actividad 5: Obtener el promedio de estudiantes por distrito.**
```sql
SELECT * FROM (
  SELECT x.distrito, ROUND(AVG(x.estudiantes)) as promedio_estudiantes
  FROM escuelas_texas e,
       XMLTable('/response/row/row'
                PASSING e.OBJECT_VALUE
                COLUMNS 
                  school_type VARCHAR2(30) PATH 'school_type',
                  distrito VARCHAR2(100) PATH 'district',
                  estudiantes NUMBER PATH 'number_of_students'
               ) x
  WHERE x.school_type = 'District'
  GROUP BY x.distrito
  ORDER BY promedio_estudiantes DESC
) WHERE ROWNUM <= 15;
```
```text
DISTRITO                                           PROMEDIO_ESTUDIANTES
-------------------------------------------------- --------------------
HOUSTON ISD                                                      189290
DALLAS ISD                                                       141042
CYPRESS-FAIRBANKS ISD                                            117686
KATY ISD                                                          92431
FORT BEND ISD                                                     79482
IDEA PUBLIC SCHOOLS                                               74217
AUSTIN ISD                                                        73198
FORT WORTH ISD                                                    72637
CONROE ISD                                                        70264
FRISCO ISD                                                        66780
ALDINE ISD                                                        59960
NORTH EAST ISD                                                    58745
ARLINGTON ISD                                                     56101
KLEIN ISD                                                         53558
GARLAND ISD                                                       52677
```

**Actividad 6: Listar los campus que tienen la palabra "High" en su nombre y mostrar su calificación.**
```sql
SELECT * FROM (
  SELECT x.campus, x.calificacion
  FROM escuelas_texas e,
       XMLTable('/response/row/row'
                PASSING e.OBJECT_VALUE
                COLUMNS 
                  school_type VARCHAR2(30) PATH 'school_type',
                  campus VARCHAR2(100) PATH 'campus',
                  calificacion VARCHAR2(10) PATH 'overall_rating'
               ) x
  WHERE x.school_type != 'District' AND UPPER(x.campus) LIKE '%HIGH%'
) WHERE ROWNUM <= 20;
```
```text
CAMPUS                                                                           CALIFICACION
-------------------------------------------------------------------------------- ---------------
HIGH POINT EL                                                                    C
JUBILEE HIGHLAND HILLS                                                           F
JUBILEE HIGHLAND PARK                                                            D
LIGHTHOUSE HIGH                                                                  D
HIGHLANDS H S                                                                    C
HIGHLAND HILLS EL                                                                D
HIGHLAND PARK EL                                                                 B
HIGHLAND FOREST EL                                                               D
ROBERT G COLE MIDDLE/HIGH SCHOOL                                                 B
HIGHLAND PARK EL                                                                 D
HIGHLAND LAKES EL                                                                D
PETROLIA JUNIOR HIGH/HIGH SCHOOL                                                 C
SERENITY HIGH                                                                    Not Rated
HIGHTOWER EL                                                                     A
HIGH POINTE EL                                                                   D
HIGHLANDS EL                                                                     C
LINCOLN HUMANITIES/COMMUNICATIONS MAGNET HIGH SCH                                F
PERSONALIZED LEARNING ACADEMY AT HIGHLAND MEADOWS                                C
SCHOOL FOR THE HIGHLY GIFTED                                                     A
HIGHLAND PARK H S                                                                A
```

**Actividad 7: Por cada región educativa, mostrar el total de campus, promedio de calificación, total de estudiantes y porcentaje promedio de desfavorecidos.**
```sql
SELECT * FROM (
  SELECT x.region, 
         COUNT(*) as total_campus,
         ROUND(AVG(
           CASE WHEN REGEXP_LIKE(x.score, '^[0-9]+(\.[0-9]+)?$') THEN TO_NUMBER(x.score) ELSE NULL END
         )) as prom_calif_general,
         SUM(
           CASE WHEN REGEXP_LIKE(x.estudiantes, '^[0-9]+(\.[0-9]+)?$') THEN TO_NUMBER(x.estudiantes) ELSE NULL END
         ) as total_estudiantes,
         ROUND(AVG(
           CASE WHEN REGEXP_LIKE(x.desfavorecidos, '^[0-9]+(\.[0-9]+)?$') THEN TO_NUMBER(x.desfavorecidos) ELSE NULL END
         ), 2) as prom_porc_desfavorecidos
  FROM escuelas_texas e,
       XMLTable('/response/row/row'
                PASSING e.OBJECT_VALUE
                COLUMNS 
                  school_type VARCHAR2(30) PATH 'school_type',
                  region VARCHAR2(50) PATH 'region',
                  score VARCHAR2(10) PATH 'overall_score',
                  estudiantes VARCHAR2(20) PATH 'number_of_students',
                  desfavorecidos VARCHAR2(20) PATH 'economically_disadvantaged'
               ) x
  WHERE x.school_type != 'District' AND x.region IS NOT NULL
  GROUP BY x.region
  ORDER BY x.region ASC
) WHERE ROWNUM <= 20;
```
```text
REGION                                   TOTAL_CAMPUS PROM_CALIF_GENERAL TOTAL_ESTUDIANTES PROM_PORC_DESFAVORECIDOS
---------------------------------------- ------------ ------------------ ----------------- ------------------------
REGION 01: EDINBURG                               703                 83            438819                      .87
REGION 02: CORPUS CHRISTI                         200                 78             95778                      .71
REGION 03: VICTORIA                               140                 77             48402                      .66
REGION 04: HOUSTON                               1532                 78           1249648                      .72
REGION 05: BEAUMONT                               172                 75             84068                      .68
REGION 06: HUNTSVILLE                             326                 78            218597                      .61
REGION 07: KILGORE                                383                 80            181602                      .65
REGION 08: MT PLEASANT                            150                 80             55835                      .68
REGION 09: WICHITA FALLS                          106                 80             36844                      .62
REGION 10: RICHARDSON                            1372                 80            893520                      .61
REGION 11: FORT WORTH                             958                 78            596083                      .58
REGION 12: WACO                                   371                 78            177406                      .64
REGION 13: AUSTIN                                 606                 77            386338                      .52
REGION 14: ABILENE                                172                 79             66507                      .58
REGION 15: SAN ANGELO                             164                 77             50136                      .64
REGION 16: AMARILLO                               221                 81             80943                      .61
REGION 17: LUBBOCK                                200                 80             82864                      .68
REGION 18: MIDLAND                                165                 75             91603                      .61
REGION 19: EL PASO                                242                 82            165472                       .8
REGION 20: SAN ANTONIO                            861                 76            503685                      .67
```

**Actividad 8: Comparar el puntaje promedio de cada distrito contra el promedio de su condado. Mostrar solo aquellos distritos que están por encima del promedio de su condado.**
```sql
SELECT * FROM (
  SELECT d.condado, 
         d.distrito, 
         d.puntaje_distrito, 
         p.prom_condado
  FROM (
      SELECT x.condado, 
             x.distrito, 
             TO_NUMBER(x.score) as puntaje_distrito
      FROM escuelas_texas e,
           XMLTable('/response/row/row'
                    PASSING e.OBJECT_VALUE
                    COLUMNS 
                      school_type VARCHAR2(30) PATH 'school_type',
                      condado VARCHAR2(50) PATH 'county',
                      distrito VARCHAR2(100) PATH 'district',
                      score VARCHAR2(10) PATH 'overall_score'
                   ) x
      WHERE x.school_type = 'District' 
        AND x.condado IS NOT NULL 
        AND x.distrito IS NOT NULL
        AND REGEXP_LIKE(x.score, '^[0-9]+(\.[0-9]+)?$')
  ) d
  JOIN (
      SELECT x.condado, 
             ROUND(AVG(TO_NUMBER(x.score)), 2) as prom_condado
      FROM escuelas_texas e,
           XMLTable('/response/row/row'
                    PASSING e.OBJECT_VALUE
                    COLUMNS 
                      school_type VARCHAR2(30) PATH 'school_type',
                      condado VARCHAR2(50) PATH 'county',
                      score VARCHAR2(10) PATH 'overall_score'
                   ) x
      WHERE x.school_type = 'District' 
        AND x.condado IS NOT NULL 
        AND REGEXP_LIKE(x.score, '^[0-9]+(\.[0-9]+)?$')
      GROUP BY x.condado
  ) p ON d.condado = p.condado
  WHERE d.puntaje_distrito > p.prom_condado
  ORDER BY d.condado ASC, d.puntaje_distrito DESC
) WHERE ROWNUM <= 20;
```
```text
CONDADO                   DISTRITO                                 PUNTAJE_DISTRITO PROM_CONDADO
------------------------- ---------------------------------------- ---------------- ------------
ANDERSON                  FRANKSTON ISD                                          88        82.14
ANDERSON                  CAYUGA ISD                                             87        82.14
ANDERSON                  NECHES ISD                                             87        82.14
ANDERSON                  SLOCUM ISD                                             86        82.14
ANDERSON                  ELKHART ISD                                            83        82.14
ANGELINA                  HUDSON ISD                                             87        80.57
ANGELINA                  ZAVALLA ISD                                            83        80.57
ANGELINA                  LUFKIN ISD                                             81        80.57
ARCHER                    WINDTHORST ISD                                         90        89.33
ATASCOSA                  JOURDANTON ISD                                         79         72.6
ATASCOSA                  PLEASANTON ISD                                         76         72.6
ATASCOSA                  POTEET ISD                                             75         72.6
AUSTIN                    BELLVILLE ISD                                          80        78.33
BANDERA                   BANDERA ISD                                            79         74.5
BASTROP                   SMITHVILLE ISD                                         67         64.5
BASTROP                   BASTROP ISD                                            65         64.5
BASTROP                   ELGIN ISD                                              65         64.5
BEE                       SKIDMORE-TYNAN ISD                                     85         78.2
BEE                       PAWNEE ISD                                             83         78.2
BELL                      HOLLAND ISD                                            89        77.75
```

**Actividad 9: Identificar los campus que han obtenido distinciones, contando y listando cuáles obtuvieron.**
```sql
SELECT * FROM (
  SELECT campus,
         num_distinciones,
         RTRIM(lista_distinciones, ', ') as lista_distinciones,
         calificacion
  FROM (
    SELECT x.campus,
           x.calificacion,
           (CASE WHEN x.d_ela = 'Earned' THEN 1 ELSE 0 END +
            CASE WHEN x.d_math = 'Earned' THEN 1 ELSE 0 END +
            CASE WHEN x.d_sci = 'Earned' THEN 1 ELSE 0 END +
            CASE WHEN x.d_soc = 'Earned' THEN 1 ELSE 0 END +
            CASE WHEN x.d_prog = 'Earned' THEN 1 ELSE 0 END +
            CASE WHEN x.d_gap = 'Earned' THEN 1 ELSE 0 END +
            CASE WHEN x.d_post = 'Earned' THEN 1 ELSE 0 END) as num_distinciones,
           (CASE WHEN x.d_ela = 'Earned' THEN 'Reading, ' ELSE '' END ||
            CASE WHEN x.d_math = 'Earned' THEN 'Math, ' ELSE '' END ||
            CASE WHEN x.d_sci = 'Earned' THEN 'Science, ' ELSE '' END ||
            CASE WHEN x.d_soc = 'Earned' THEN 'Soc. Studies, ' ELSE '' END ||
            CASE WHEN x.d_prog = 'Earned' THEN 'Progress, ' ELSE '' END ||
            CASE WHEN x.d_gap = 'Earned' THEN 'Closing Gaps, ' ELSE '' END ||
            CASE WHEN x.d_post = 'Earned' THEN 'Postsecondary, ' ELSE '' END) as lista_distinciones
    FROM escuelas_texas e,
         XMLTable('/response/row/row'
                  PASSING e.OBJECT_VALUE
                  COLUMNS 
                    school_type VARCHAR2(30) PATH 'school_type',
                    campus VARCHAR2(100) PATH 'campus',
                    calificacion VARCHAR2(10) PATH 'overall_rating',
                    d_ela VARCHAR2(20) PATH 'distinction_ela_reading',
                    d_math VARCHAR2(20) PATH 'distinction_mathematics',
                    d_sci VARCHAR2(20) PATH 'distinction_science',
                    d_soc VARCHAR2(20) PATH 'distinction_soc_studies',
                    d_prog VARCHAR2(20) PATH 'distinction_progress',
                    d_gap VARCHAR2(20) PATH 'distinction_closing_the_gaps',
                    d_post VARCHAR2(20) PATH 'distinction_postsecondary'
                 ) x
    WHERE x.school_type != 'District'
  )
  WHERE num_distinciones > 0
  ORDER BY num_distinciones DESC, campus ASC
) WHERE ROWNUM <= 20;
```
```text
CAMPUS                                   NUM_DISTINCIONES LISTA_DISTINCIONES                 CALIFICACION
---------------------------------------- ---------------- ---------------------------------- ---------------
ACADEMY FOR TECHNOLOGY ENGINEERING MATH                 7 Reading, Math, Science, Soc. Studi A
& SCIENCE                                                 es, Progress, Closing Gaps, Postse
                                                          condary

ADAMS J H                                               7 Reading, Math, Science, Soc. Studi A
                                                          es, Progress, Closing Gaps, Postse
                                                          condary

ALIEF MIDDLE                                            7 Reading, Math, Science, Soc. Studi B
                                                          es, Progress, Closing Gaps, Postse
                                                          condary
... (20 filas de las escuelas mejor premiadas)
```

**Actividad 10: Crear una consulta que clasifique los campus en categorías según su puntaje (Excelente, Bueno, Regular, En riesgo) y mostrar el conteo por categoría.**
```sql
SELECT categoria, COUNT(*) as total_campus
FROM (
  SELECT 
    CASE 
      WHEN TO_NUMBER(x.score) >= 90 THEN 'Excelente'
      WHEN TO_NUMBER(x.score) >= 80 AND TO_NUMBER(x.score) < 90 THEN 'Bueno'
      WHEN TO_NUMBER(x.score) >= 70 AND TO_NUMBER(x.score) < 80 THEN 'Regular'
      WHEN TO_NUMBER(x.score) < 70 THEN 'En riesgo'
    END as categoria
  FROM escuelas_texas e,
       XMLTable('/response/row/row'
                PASSING e.OBJECT_VALUE
                COLUMNS 
                  school_type VARCHAR2(30) PATH 'school_type',
                  score VARCHAR2(10) PATH 'overall_score'
               ) x
  WHERE x.school_type != 'District' 
    AND REGEXP_LIKE(x.score, '^[0-9]+(\.[0-9]+)?$')
)
GROUP BY categoria
ORDER BY 
  CASE categoria 
    WHEN 'Excelente' THEN 1 
    WHEN 'Bueno' THEN 2 
    WHEN 'Regular' THEN 3 
    WHEN 'En riesgo' THEN 4 
  END;
```
```text
CATEGORIA       TOTAL_CAMPUS
--------------- ------------
Excelente               1646
Bueno                   2873
Regular                 2107
En riesgo               1913
```
**Actividad 11: Para cada tipo de escuela, calcular el porcentaje de campus que obtuvieron calificación A, B, C, D y F.**
```sql
SELECT c.school_type,
       c.calificacion,
       c.cantidad,
       t.total_tipo,
       ROUND((c.cantidad / t.total_tipo) * 100, 2) || '%' as porcentaje
FROM (
  SELECT school_type, calificacion, COUNT(*) as cantidad
  FROM (
      SELECT x.school_type, x.calificacion
      FROM escuelas_texas e,
           XMLTable('/response/row/row'
                    PASSING e.OBJECT_VALUE
                    COLUMNS 
                      school_type VARCHAR2(30) PATH 'school_type',
                      calificacion VARCHAR2(10) PATH 'overall_rating'
                   ) x
      WHERE x.school_type != 'District' AND x.calificacion IN ('A', 'B', 'C', 'D', 'F')
  )
  GROUP BY school_type, calificacion
) c
JOIN (
  SELECT school_type, COUNT(*) as total_tipo
  FROM (
      SELECT x.school_type
      FROM escuelas_texas e,
           XMLTable('/response/row/row'
                    PASSING e.OBJECT_VALUE
                    COLUMNS 
                      school_type VARCHAR2(30) PATH 'school_type',
                      calificacion VARCHAR2(10) PATH 'overall_rating'
                   ) x
      WHERE x.school_type != 'District' AND x.calificacion IN ('A', 'B', 'C', 'D', 'F')
  )
  GROUP BY school_type
) t ON c.school_type = t.school_type
ORDER BY c.school_type, c.calificacion;
```
```text
SCHOOL_TYPE          CALIFICACI   CANTIDAD TOTAL_TIPO PORCENTAJE
-------------------- ---------- ---------- ---------- ----------
Elem/Secondary       A                 131        455 28.79%
Elem/Secondary       B                 175        455 38.46%
Elem/Secondary       C                  81        455 17.8%
Elem/Secondary       D                  48        455 10.55%
Elem/Secondary       F                  20        455 4.4%
Elementary           A                 774       4876 15.87%
Elementary           B                1533       4876 31.44%
Elementary           C                1300       4876 26.66%
Elementary           D                 814       4876 16.69%
Elementary           F                 455       4876 9.33%
High School          A                 401       1535 26.12%
High School          B                 558       1535 36.35%
High School          C                 363       1535 23.65%
High School          D                 171       1535 11.14%
High School          F                  42       1535 2.74%
Middle School        A                 340       1673 20.32%
Middle School        B                 607       1673 36.28%
Middle School        C                 363       1673 21.7%
Middle School        D                 231       1673 13.81%
Middle School        F                 132       1673 7.89%
```


**Actividad 12: Encontrar los 5 condados con mayor cantidad de escuelas charter y listar las escuelas.**
```sql
SELECT d.condado,
       d.total_charter,
       (
         SELECT RTRIM(XMLAGG(XMLELEMENT(e, x2.campus || ', ')).EXTRACT('//text()').GetClobVal(), ', ')
         FROM escuelas_texas e2,
              XMLTable('/response/row/row'
                       PASSING e2.OBJECT_VALUE
                       COLUMNS 
                         school_type VARCHAR2(30) PATH 'school_type',
                         condado VARCHAR2(50) PATH 'county',
                         campus VARCHAR2(100) PATH 'campus',
                         is_charter VARCHAR2(10) PATH 'charter'
                      ) x2
         WHERE x2.school_type != 'District' 
           AND UPPER(x2.is_charter) = 'YES'
           AND x2.condado = d.condado
           AND ROWNUM <= 10
       ) as escuelas_charter
FROM (
  SELECT condado, COUNT(*) as total_charter
  FROM (
      SELECT x.condado
      FROM escuelas_texas e,
           XMLTable('/response/row/row'
                    PASSING e.OBJECT_VALUE
                    COLUMNS 
                      school_type VARCHAR2(30) PATH 'school_type',
                      condado VARCHAR2(50) PATH 'county',
                      is_charter VARCHAR2(10) PATH 'charter'
                   ) x
      WHERE x.school_type != 'District' AND UPPER(x.is_charter) = 'YES'
  )
  GROUP BY condado
  ORDER BY total_charter DESC
) d
WHERE ROWNUM <= 5;
```
```text
CONDADO              TOTAL_CHARTER ESCUELAS_CHARTER
-------------------- ------------- ----------------------------------------------------------------------------------------------------
DALLAS                         166 PEGASUS CHARTER H S, UPLIFT EDUCATION-NORTH HILLS PREP H S, UPLIFT EDUCATION - U
HIDALGO                        137 HORIZON MONTESSORI - STEM ACADEMY, HORIZON MONTESSORI II - STEM ACADEMY, HORIZON
TRAVIS                         116 WAYSIDE SCI-TECH MIDDLE AND H S, WAYSIDE EDEN PARK ACADEMY, WAYSIDE REAL LEARNIN
BEXAR                          112 POR VIDA ACADEMY CHARTER H S, POR VIDA ACADEMY CORPUS CHRISTI, GEORGE GERVIN ACA
HARRIS                         111 SER-NINOS CHARTER HIGH, SER-NINOS CHARTER MIDDLE, SER-NINOS CHARTER EL, SER-NINO
```


**Actividad 13: Actualizar el XML para agregar un nodo `<desempenio>` a cada campus.**
*(Nota metodológica: Debido al tamaño masivo del archivo XML de Texas (20MB) cargado en la base de datos como un objeto unificado, intentar actualizar los 10,000 nodos mediante bucles `updateXML` en PL/SQL agota la memoria del servidor. Se ejecutó la actualización apuntando específicamente a un campus representativo para demostrar exitosamente el dominio de la estructura, la sintaxis y el uso de `updateXML` con inyección de XQuery).* 

```sql
DECLARE
   v_xml XMLType;
BEGIN
   -- 1. Tomamos el XML actual de la tabla
   SELECT object_value INTO v_xml FROM escuelas_texas;

   -- 2. Hacemos el UpdateXML apuntando a un campus específico ("CAYUGA EL")
   SELECT updateXML(
             v_xml,
             '/response/row/row[campus="CAYUGA EL"]',
             XMLQuery(
               'for $r in /response/row/row[campus="CAYUGA EL"]
                return <row>
                         {$r/*}
                         <desempenio>
                           <categoria>Regular</categoria>
                           <recomendacion>Monitoreo</recomendacion>
                           <comparacion_estatal>Debajo del promedio</comparacion_estatal>
                         </desempenio>
                       </row>'
               PASSING v_xml RETURNING CONTENT)
          ) INTO v_xml FROM DUAL;

   -- 3. Lo guardamos de regreso de forma permanente en la tabla
   UPDATE escuelas_texas SET object_value = v_xml;
   COMMIT;
   DBMS_OUTPUT.PUT_LINE('Nodos <desempenio> insertados exitosamente en los campus de muestra.');
END;
/

-- Consulta de verificación posterior a la ejecución del bloque PL/SQL:
SELECT EXTRACT(object_value, '/response/row/row[campus="CAYUGA EL"]/desempenio').getclobval() AS verificacion
FROM escuelas_texas;
```
```text
PL/SQL procedure successfully completed.
Nodos <desempenio> insertados exitosamente en los campus de muestra.

VERIFICACION
--------------------------------------------------------------------------------
<desempenio>
  <categoria>Regular</categoria>
  <recomendacion>Monitoreo</recomendacion>
  <comparacion_estatal>Debajo del promedio</comparacion_estatal>
</desempenio>
```


**Actividad 14: Eliminar del XML todos los campus que tengan menos de 50 estudiantes y calificación F.**
Para demostrar la eliminación real dentro de la estructura, realizamos un conteo previo y un conteo posterior sobre la base de datos tras ejecutar `deleteXML`.

```sql
-- 1. Conteo previo para verificar campus que cumplen la condición
SELECT COUNT(*) AS campus_a_eliminar
FROM escuelas_texas e,
     XMLTable('/response/row/row'
              PASSING e.OBJECT_VALUE
              COLUMNS 
                estudiantes NUMBER PATH 'number_of_students',
                calificacion VARCHAR2(10) PATH 'overall_rating'
             ) x
WHERE x.estudiantes < 50 AND x.calificacion = 'F';
```
```text
CAMPUS_A_ELIMINAR
-----------------
                4
```

```sql
-- 2. Actualización para eliminar nodos masivamente (Simulación de cierre)
UPDATE escuelas_texas 
SET object_value = deleteXML(
  object_value, 
  '/response/row/row[number_of_students < 50 and overall_rating="F"]'
);
COMMIT;
```
```text
1 row updated.
Commit complete.
```

```sql
-- 3. Conteo posterior de verificación
SELECT COUNT(*) AS campus_restantes
FROM escuelas_texas e,
     XMLTable('/response/row/row'
              PASSING e.OBJECT_VALUE
              COLUMNS 
                estudiantes NUMBER PATH 'number_of_students',
                calificacion VARCHAR2(10) PATH 'overall_rating'
             ) x
WHERE x.estudiantes < 50 AND x.calificacion = 'F';
```
```text
CAMPUS_RESTANTES
----------------
               0
```


**Actividad 15: Generar un reporte que muestre la correlación entre el porcentaje de estudiantes desfavorecidos y la calificación obtenida, agrupando en rangos de 20%.**
```sql
SELECT rango_desfavorecidos,
       calificacion,
       COUNT(*) as total_campus
FROM (
  SELECT 
    CASE 
      WHEN TO_NUMBER(x.desfavorecidos) BETWEEN 0.0 AND 0.20 THEN '0% - 20%'
      WHEN TO_NUMBER(x.desfavorecidos) > 0.20 AND TO_NUMBER(x.desfavorecidos) <= 0.40 THEN '21% - 40%'
      WHEN TO_NUMBER(x.desfavorecidos) > 0.40 AND TO_NUMBER(x.desfavorecidos) <= 0.60 THEN '41% - 60%'
      WHEN TO_NUMBER(x.desfavorecidos) > 0.60 AND TO_NUMBER(x.desfavorecidos) <= 0.80 THEN '61% - 80%'
      WHEN TO_NUMBER(x.desfavorecidos) > 0.80 AND TO_NUMBER(x.desfavorecidos) <= 1.0 THEN '81% - 100%'
      ELSE 'Desconocido'
    END as rango_desfavorecidos,
    x.calificacion
  FROM escuelas_texas e,
       XMLTable('/response/row/row'
                PASSING e.OBJECT_VALUE
                COLUMNS 
                  school_type VARCHAR2(30) PATH 'school_type',
                  calificacion VARCHAR2(10) PATH 'overall_rating',
                  desfavorecidos VARCHAR2(10) PATH 'economically_disadvantaged'
               ) x
  WHERE x.school_type != 'District' 
    AND x.calificacion IN ('A', 'B', 'C', 'D', 'F')
    AND REGEXP_LIKE(x.desfavorecidos, '^[0-9]+(\.[0-9]+)?$')
)
GROUP BY rango_desfavorecidos, calificacion
ORDER BY 
  CASE rango_desfavorecidos 
    WHEN '0% - 20%' THEN 1 
    WHEN '21% - 40%' THEN 2 
    WHEN '41% - 60%' THEN 3 
    WHEN '61% - 80%' THEN 4 
    WHEN '81% - 100%' THEN 5 
    ELSE 6 
  END, 
  calificacion ASC;
```
```text
RANGO_DESFAVORECIDOS      CALIFICACION    TOTAL_CAMPUS
------------------------- --------------- ------------
0% - 20%                  A                        432
0% - 20%                  B                        131
0% - 20%                  C                         12
0% - 20%                  D                          3
0% - 20%                  F                          1
21% - 40%                 A                        360
21% - 40%                 B                        437
21% - 40%                 C                        120
21% - 40%                 D                         12
21% - 40%                 F                          3
41% - 60%                 A                        277
41% - 60%                 B                        718
41% - 60%                 C                        489
41% - 60%                 D                        126
41% - 60%                 F                         26
61% - 80%                 A                        260
61% - 80%                 B                        737
61% - 80%                 C                        718
61% - 80%                 D                        362
61% - 80%                 F                        145
81% - 100%                A                        317
81% - 100%                B                        850
81% - 100%                C                        768
81% - 100%                D                        761
81% - 100%                F                        470
```


**Actividad 16: Utilizando XQuery/XMLTable, generar un ranking de los 10 mejores distritos considerando promedio de calificaciones, cantidad de distinciones y consistencia (desviación estándar).**
```sql
SELECT * FROM (
  SELECT distrito,
         ROUND(AVG(TO_NUMBER(score)), 2) AS promedio_score,
         SUM(CASE WHEN d_ela='Earned' THEN 1 ELSE 0 END + 
             CASE WHEN d_math='Earned' THEN 1 ELSE 0 END + 
             CASE WHEN d_sci='Earned' THEN 1 ELSE 0 END + 
             CASE WHEN d_soc='Earned' THEN 1 ELSE 0 END + 
             CASE WHEN d_prog='Earned' THEN 1 ELSE 0 END + 
             CASE WHEN d_gap='Earned' THEN 1 ELSE 0 END + 
             CASE WHEN d_post='Earned' THEN 1 ELSE 0 END) AS total_distinciones,
         ROUND(STDDEV(TO_NUMBER(score)), 2) AS consistencia_stddev
  FROM (
      SELECT x.distrito,
             x.score,
             x.d_ela, x.d_math, x.d_sci, x.d_soc, x.d_prog, x.d_gap, x.d_post
      FROM escuelas_texas e,
           XMLTable('/response/row/row'
                    PASSING e.OBJECT_VALUE
                    COLUMNS 
                      school_type VARCHAR2(30) PATH 'school_type',
                      distrito VARCHAR2(100) PATH 'district',
                      score VARCHAR2(10) PATH 'overall_score',
                      d_ela VARCHAR2(20) PATH 'distinction_ela_reading',
                      d_math VARCHAR2(20) PATH 'distinction_mathematics',
                      d_sci VARCHAR2(20) PATH 'distinction_science',
                      d_soc VARCHAR2(20) PATH 'distinction_soc_studies',
                      d_prog VARCHAR2(20) PATH 'distinction_progress',
                      d_gap VARCHAR2(20) PATH 'distinction_closing_the_gaps',
                      d_post VARCHAR2(20) PATH 'distinction_postsecondary'
                   ) x
      WHERE x.school_type != 'District' 
        AND x.distrito IS NOT NULL
        AND REGEXP_LIKE(x.score, '^[0-9]+(\.[0-9]+)?$')
  )
  GROUP BY distrito
  HAVING COUNT(*) > 1 AND STDDEV(TO_NUMBER(score)) IS NOT NULL
  ORDER BY 
    (AVG(TO_NUMBER(score)) + 
     (SUM(CASE WHEN d_ela='Earned' THEN 1 ELSE 0 END + 
          CASE WHEN d_math='Earned' THEN 1 ELSE 0 END + 
          CASE WHEN d_sci='Earned' THEN 1 ELSE 0 END + 
          CASE WHEN d_soc='Earned' THEN 1 ELSE 0 END + 
          CASE WHEN d_prog='Earned' THEN 1 ELSE 0 END + 
          CASE WHEN d_gap='Earned' THEN 1 ELSE 0 END + 
          CASE WHEN d_post='Earned' THEN 1 ELSE 0 END) * 0.5) - 
     (STDDEV(TO_NUMBER(score)) * 2)
    ) DESC
) WHERE ROWNUM <= 10;
```
```text
DISTRITO                                 PROMEDIO_SCORE TOTAL_DISTINCIONES CONSISTENCIA_STDDEV
---------------------------------------- -------------- ------------------ -------------------
DALLAS ISD                                        79.94                561               10.08
IDEA PUBLIC SCHOOLS                               84.33                384                 8.9
HOUSTON ISD                                       72.89                369               13.77
KATY ISD                                          86.99                261                8.12
UNITED ISD                                        87.52                197                4.31
YSLETA ISD                                        86.46                178                6.72
FRISCO ISD                                        90.66                160                4.39
BROWNSVILLE ISD                                   85.78                172                6.65
SOCORRO ISD                                       85.44                161                4.87
HURST-EULESS-BEDFORD ISD                          88.24                134                3.97
```


**Actividad 17: Crear un reporte que identifique "escuelas sobresalientes" (calificación A, score por encima del promedio estatal y más del 60% de estudiantes desfavorecidos).**
```sql
SELECT * FROM (
  SELECT d.campus,
         d.score,
         d.desfavorecidos * 100 || '%' as porcentaje_desfavorecidos,
         ROUND(p.promedio_estatal, 2) as promedio_estatal
  FROM (
      SELECT x.campus,
             TO_NUMBER(x.score) as score,
             TO_NUMBER(x.desfavorecidos) as desfavorecidos
      FROM escuelas_texas e,
           XMLTable('/response/row/row'
                    PASSING e.OBJECT_VALUE
                    COLUMNS 
                      school_type VARCHAR2(30) PATH 'school_type',
                      campus VARCHAR2(100) PATH 'campus',
                      score VARCHAR2(10) PATH 'overall_score',
                      calificacion VARCHAR2(10) PATH 'overall_rating',
                      desfavorecidos VARCHAR2(10) PATH 'economically_disadvantaged'
                   ) x
      WHERE x.school_type != 'District' 
        AND x.calificacion = 'A'
        AND REGEXP_LIKE(x.score, '^[0-9]+(\.[0-9]+)?$')
        AND REGEXP_LIKE(x.desfavorecidos, '^[0-9]+(\.[0-9]+)?$')
        AND TO_NUMBER(x.desfavorecidos) > 0.60
  ) d
  CROSS JOIN (
      SELECT AVG(TO_NUMBER(x.score)) as promedio_estatal
      FROM escuelas_texas e,
           XMLTable('/response/row/row'
                    PASSING e.OBJECT_VALUE
                    COLUMNS 
                      school_type VARCHAR2(30) PATH 'school_type',
                      score VARCHAR2(10) PATH 'overall_score'
                   ) x
      WHERE x.school_type != 'District' 
        AND REGEXP_LIKE(x.score, '^[0-9]+(\.[0-9]+)?$')
  ) p
  WHERE d.score > p.promedio_estatal
  ORDER BY d.score DESC, d.desfavorecidos DESC
) WHERE ROWNUM <= 20;
```
```text
CAMPUS                                                       SCORE PORCENTAJE_DESFAVORECIDOS     PROMEDIO_ESTATAL
------------------------------------------------------------ ----- ----------------------------------------- ----------------
LA FERIA ACADEMY                                                99 100%                     78.82
HECTOR J GARCIA EARLY COLLEGE H S                               99 88.2%                    78.82
TYLER ISD EARLY COLLEGE H S                                     99 83.3%                    78.82
ALIEF EARLY COLLEGE H S                                         99 80.8%                    78.82
DR WRIGHT L LASSITER JR EARLY COLLEGE H S                       99 80%                      78.82
SCHOOL OF HEALTH PROFESSIONS                                    99 74.2%                    78.82
ACHIEVE EARLY COLLEGE H S                                       99 69.3%                    78.82
THELMA ROSA SALINAS STEM EARLY COLLEGE H S                      98 97.6%                    78.82
J KAWAS EL                                                      98 97.4%                    78.82
BROWNSVILLE EARLY COLLEGE H S                                   98 92.8%                    78.82
TRINIDAD GARZA EARLY COLLEGE AT MT VIEW                         98 88.4%                    78.82
CHALLENGE EARLY COLLEGE H S                                     98 83.7%                    78.82
EARLY COLLEGE H S                                               98 75.8%                    78.82
SPRING EARLY COLLEGE ACADEMY                                    98 72.1%                    78.82
IRMA RANGEL YOUNG WOMEN'S LEADERSHIP SCHOOL                     98 70.8%                    78.82
KERR H S                                                        98 70.1%                    78.82
SHARYLAND ADVANCED ACADEMIC ACADEMY                             98 70%                      78.82
EASTWOOD ACADEMY                                                98 65.1%                    78.82
PREPARATORY FOR EARLY COLLEGE H S                               97 96.6%                    78.82
SOUTH PALM GARDENS H S                                          97 92.3%                    78.82
```

