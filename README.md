# FastAPI Learning Project

Welcome to my FastAPI learning project! This repository is dedicated to my journey of exploring and mastering Python for web APIs using FastAPI. The project covers various aspects including ORM, telemetry instrumentation, logging, and more.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Database Migration](#database-migration)
- [Usage](#usage)

## Introduction

This project is a hands-on exploration of FastAPI, a modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints. The goal is to learn and implement various features and best practices in FastAPI.

## Features

- **FastAPI**: Building APIs with FastAPI.
- **ORM**: Using SQLAlchemy for database interactions.
- **Telemetry Instrumentation**: Implementing telemetry to monitor application performance using OpenTelemetry SDK.
- **Logging**: Setting up structured logging for better debugging and monitoring.
- **Testing**: Writing tests to ensure the reliability of the application.

## Installation

To get started with this project, follow these steps:

1. Clone the repository:
    ```bash
    git clone https://github.com/amaneasdf/simple-fastapi.git
    cd fastapi-learning-project
    ```

2. Create and activate a virtual environment:
    ```bash
    python -m venv env
    source env/bin/activate  # On Windows use `env\Scripts\activate`
    ```

3. Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
## Environment Variables

This project uses environment variables for configuration. To set up the environment variables, follow these steps:

  1. Copy the `.env.example` file to `.env`:
      ```bash
      cp .env.example .env
      ```
  
  2. Open the `.env` file and update the values as needed.


## Database Migration

This project uses Alembic for database migrations. To add a new migration, follow these steps:

  1. Create a new migration script:
      ```bash
      alembic revision --autogenerate -m "Description of migration"
      ```
  
  2. Apply the migration to the database:
      ```bash
      alembic upgrade head
      ```

## Usage

To run the FastAPI application, use the following command:
```bash
uvicorn main:app --reload
```
The application will be available at `http://127.0.0.1:8000`.