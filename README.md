# FashionHub Project

This project is a Django-based fashion e-commerce application.

## How to Transfer to Another Laptop

To move this project to a new computer while keeping all your products, users, and data, follow these steps:

### 1. On your CURRENT Laptop:
1.  **Export the Data**: Open PowerShell in the project folder and run:
    ```powershell
    .\export_data.ps1
    ```
    This creates a file called `data.json` with all your database information.
2.  **Zip the Project**: Compress the project folder. **Make sure `data.json` is included in the zip**. (You can exclude the `.venv` folder to save space).
3.  **Move the Zip**: Transfer the zip file to your new laptop (USB, Cloud, etc.).

### 2. On your NEW Laptop:
1.  **Extract**: Unzip the folder.
2.  **Run Setup**: Open PowerShell in the project folder and run:
    ```powershell
    .\setup.ps1
    ```
    The setup script will automatically:
    - Create a virtual environment and install packages.
    - Create your configuration (`.env`).
    - Run database migrations.
    - **Automatically import your data from `data.json`**.
    - Collect static files.

## Running the Project

Once setup is complete, you can start the development server:

1.  **Activate Environment**:
    - Windows: `.\.venv\Scripts\activate`
    - Linux/macOS: `source .venv/bin/activate`
2.  **Start Server**:
    ```bash
    python manage.py runserver
    ```

## Prerequisites

- **Python 3.11+**: Ensure Python is installed on the new laptop.
- **PostgreSQL**: This project is configured to use PostgreSQL. Make sure you have PostgreSQL installed and a database named `fashionhub` created before running the setup script.
