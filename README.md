# Portafolio de BDNR y Big Data

![Build Status](https://img.shields.io/github/actions/workflow/status/eddndev-studio/bdnr/deploy.yml?branch=main&label=build)
![Astro](https://img.shields.io/badge/framework-Astro-orange)
![TailwindCSS](https://img.shields.io/badge/styling-Tailwind_CSS-38B2AC)
![Oracle](https://img.shields.io/badge/database-Oracle_11g_XE-F80000)
![License](https://img.shields.io/github/license/eddndev-studio/bdnr)

## Overview

Portafolio de prácticas de **Bases de Datos No Relacionales (BDNR)** y
**Big Data (C703)** de Eduardo Alonso Sánchez. El índice separa ambas materias
y conserva su numeración propia.

## Reportes de Big Data

Grupo 7CV4 · Docente: Tania Rodríguez Sarabia.

| Práctica | Reporte | Página fuente |
| --- | --- | --- |
| 1 | Limpieza de datos en Online Retail | `src/pages/big-data/practica1.md` |
| 2 | Introducción a Apache Spark | `src/pages/big-data/practica2.md` |

Las páginas se publican en `/big-data/practica1/` y `/big-data/practica2/`.
Incluyen procedimiento, fragmentos de código, resultados, limitaciones y
descargas de los reportes PDF con la plantilla ESCOM. Las evidencias están en
`public/big-data/`: notebook ejecutado, gráficas, script de Spark, dependencias,
resúmenes y CSV pequeños. Los datasets originales se obtienen de las fuentes
citadas en cada reporte.

En el espacio ESCOM, los documentos LaTeX independientes y las entradas originales
permanecen en `BD/01-limpieza-datos-retail/` y
`BD/02-introduccion-apache-spark/`. Los reportes web adaptan su contenido y sus
resultados guardados. La pieza `part-*.csv` de Spark se copia como
`ocupaciones.csv` sin modificar sus datos.

## Desarrollo y publicación

```bash
npm ci
npm run dev
npm run build
```

La publicación se realiza mediante `.github/workflows/deploy.yml` al publicar
cambios en `main` o `master`. El workflow instala dependencias, compila Astro y
despliega el directorio `dist/` en Cloudflare Pages. Los despliegues deben pasar
por GitHub Actions y comprobarse en el resultado del workflow.

## Purpose and Engineering Goals

The primary objective of this project is to maintain a clean, high-performance platform for technical documentation and query execution analysis. Unlike standard academic submissions, this system prioritizes:

*   **Static Site Excellence:** Utilizing Astro to achieve near-zero client-side JavaScript for content delivery, leveraging SSG (Static Site Generation) for optimal edge distribution via Cloudflare Pages.
*   **Database Operation Transparency:** Strict separation of concerns between heavy database operations (stored locally on Dockerized environments) and the presentation layer, ensuring the repository remains lightweight and agile.
*   **Algorithmic and Query Optimization:** Documenting real-world database constraints, memory management (OOM prevention), and the mathematical optimization of complex XPath/XQuery extractions into `XMLTable` structures.
*   **Structured Content Engineering:** Maintaining rigorous Markdown documentation that mirrors the exact execution states, query syntaxes, and standard outputs of the AlmaLinux VPS.

## Tech Stack

*   **Framework:** Astro (SSG)
*   **Styling:** Tailwind CSS v4 (Vite-integrated)
*   **Content:** Markdown with Shiki-based syntax highlighting
*   **Database Context:** Oracle 11g XE (Docker) with Native XML DB (XDB) features
*   **CI/CD:** GitHub Actions -> Cloudflare Pages

## License

GPLv3
