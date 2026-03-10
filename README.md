# BDNR Portfolio

![Build Status](https://img.shields.io/github/actions/workflow/status/eddndev-studio/bdnr/deploy.yml?branch=main&label=build)
![Astro](https://img.shields.io/badge/framework-Astro-orange)
![TailwindCSS](https://img.shields.io/badge/styling-Tailwind_CSS-38B2AC)
![Oracle](https://img.shields.io/badge/database-Oracle_11g_XE-F80000)
![License](https://img.shields.io/github/license/eddndev-studio/bdnr)

## Overview

This repository serves as the technical foundation for the **Non-Relational Databases (BDNR)** academic portfolio. It is designed as an engineering environment focused on documenting SQL/XQuery scripting, architectural database workflows, and performance optimization reflections over large datasets.

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