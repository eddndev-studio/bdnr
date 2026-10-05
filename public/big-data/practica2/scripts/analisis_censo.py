"""Práctica 2: análisis exploratorio de adult.csv con Apache Spark.

Ejecutar desde cualquier directorio con:
    python scripts/analisis_censo.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "datos" / "raw" / "adult.csv"
RESULTS = ROOT / "resultados"
OCCUPATIONS_DIR = RESULTS / "Reporte_Ocupaciones_Eduardo_Alonso_Sanchez"


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Falta el conjunto de datos: {SOURCE}")

    spark = (
        SparkSession.builder.appName("Análisis Censo")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    try:
        census = spark.read.csv(str(SOURCE), header=True, inferSchema=True)
        required = {"occupation", "gender", "hours-per-week", "native-country"}
        missing = required.difference(census.columns)
        if missing:
            raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")

        print("\n=== Esquema inferido ===")
        census.printSchema()
        total = census.count()
        print(f"Total de registros: {total}")

        top_occupations = (
            census.groupBy("occupation")
            .count()
            .orderBy(F.desc("count"), F.asc("occupation"))
            .limit(10)
        )
        print("\n=== Diez ocupaciones más frecuentes ===")
        top_occupations.show(10, truncate=False)

        hours_by_gender = (
            census.groupBy("gender")
            .agg(
                F.count("hours-per-week").alias("registros_con_horas"),
                F.avg("hours-per-week").alias("horas_promedio"),
            )
            .orderBy("gender")
        )
        print("\n=== Promedio de horas semanales por género ===")
        hours_by_gender.show(truncate=False)

        mexico = census.filter(F.col("native-country") == "Mexico")
        mexico_total = mexico.count()
        print(f"\n=== Personas con native-country = Mexico: {mexico_total} ===")
        mexico.select(
            "age", "workclass", "education", "occupation", "gender",
            "hours-per-week", "native-country", "income"
        ).show(20, truncate=False)

        RESULTS.mkdir(parents=True, exist_ok=True)
        (
            top_occupations.coalesce(1)
            .write.mode("overwrite")
            .option("header", True)
            .csv(str(OCCUPATIONS_DIR))
        )

        summary = {
            "fuente": "https://github.com/saravrajavelu/Adult-Income-Analysis/blob/master/adult.csv",
            "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "spark_version": spark.version,
            "registros": total,
            "columnas": census.columns,
            "esquema": [
                {"columna": field.name, "tipo": field.dataType.simpleString()}
                for field in census.schema.fields
            ],
            "ocupaciones_top10": [row.asDict() for row in top_occupations.collect()],
            "horas_por_genero": [row.asDict() for row in hours_by_gender.collect()],
            "registros_mexico": mexico_total,
        }
        (RESULTS / "resumen.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\nCSV de ocupaciones: {OCCUPATIONS_DIR}")
        print(f"Resumen verificable: {RESULTS / 'resumen.json'}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
