#!/usr/bin/env python3
"""Script para actualizar todas las plantillas HTML con el nuevo diseño"""

import os

BASE_PATH = "/Users/juan.vilanova/Desktop/Simona version final/core/templates/core"

# Estilos comunes para el navbar
NAVBAR_STYLES = """
    :root {
        --primary-blue: #2563eb;
        --light-blue: #3b82f6;
        --dark-blue: #1e40af;
    }
    body {
        background: linear-gradient(135deg, #e0f2fe 0%, #ffffff 100%);
        min-height: 100vh;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .navbar-custom {
        background: linear-gradient(90deg, var(--primary-blue) 0%, var(--light-blue) 100%) !important;
        box-shadow: 0 2px 10px rgba(37, 99, 235, 0.2);
        padding: 1rem 0;
    }
    .logo-space {
        width: 50px;
        height: 50px;
        background: white;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .logo-space i {
        font-size: 28px;
        color: var(--primary-blue);
    }
    .navbar-brand {
        font-size: 1.5rem;
        font-weight: 700;
        color: white !important;
        display: flex;
        align-items: center;
    }
    .user-badge {
        background: rgba(255,255,255,0.2);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        color: white;
    }
    .btn-custom-primary {
        background: linear-gradient(90deg, var(--primary-blue) 0%, var(--light-blue) 100%);
        border: none;
        color: white;
        padding: 0.6rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .btn-custom-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(37, 99, 235, 0.3);
        color: white;
    }
    .page-header {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 2px 15px rgba(0,0,0,0.05);
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    .page-header h1 {
        color: var(--primary-blue);
        font-weight: 700;
        margin: 0;
    }
"""

NAVBAR_HTML = """
    <nav class="navbar navbar-expand-lg navbar-custom">
        <div class="container-fluid px-4">
            <a class="navbar-brand" href="{% url 'home' %}">
                <div class="logo-space">
                    <i class="bi bi-cloud-arrow-up-fill"></i>
                </div>
                Simona DataPipeline
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" style="border-color: white;">
                <span class="navbar-toggler-icon" style="filter: invert(1);"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto align-items-center">
                    <li class="nav-item me-3">
                        <span class="user-badge">
                            <i class="bi bi-person-circle me-2"></i>{{ user.username }}
                        </span>
                    </li>
                    <li class="nav-item">
                        <a class="btn btn-light btn-sm" href="{% url 'logout' %}">
                            <i class="bi bi-box-arrow-right me-1"></i>Cerrar Sesión
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
"""

def create_file(filename, content):
    """Helper para crear archivos"""
    filepath = os.path.join(BASE_PATH, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ {filename} actualizado")

# ========== SIGNUP.HTML ==========
signup_html = f'''{{%load static %}}
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registro - Simona DataPipeline</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <style>
        :root {{ --primary-blue: #2563eb; --light-blue: #3b82f6; }}
        body {{ background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
        .signup-container {{ background: white; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); overflow: hidden; max-width: 500px; width: 100%; }}
        .signup-header {{ background: linear-gradient(135deg, var(--primary-blue) 0%, var(--light-blue) 100%); padding: 2.5rem 2rem; text-align: center; color: white; }}
        .logo-space {{ width: 80px; height: 80px; background: white; border-radius: 20px; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; box-shadow: 0 5px 15px rgba(0,0,0,0.2); }}
        .logo-space i {{ font-size: 45px; color: var(--primary-blue); }}
        .signup-header h2 {{ font-weight: 700; margin-bottom: 0.3rem; }}
        .signup-body {{ padding: 2.5rem; }}
        .form-label {{ color: #334155; font-weight: 600; margin-bottom: 0.5rem; }}
        .form-control {{ border: 2px solid #e2e8f0; border-radius: 10px; padding: 0.75rem 1rem; }}
        .form-control:focus {{ border-color: var(--primary-blue); box-shadow: 0 0 0 0.2rem rgba(37, 99, 235, 0.1); }}
        .btn-custom-primary {{ background: linear-gradient(90deg, var(--primary-blue) 0%, var(--light-blue) 100%); border: none; color: white; padding: 0.75rem; border-radius: 10px; font-weight: 600; width: 100%; }}
        .btn-custom-primary:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(37, 99, 235, 0.3); }}
        .helptext {{ font-size: 0.85rem; color: #64748b; margin-top: 0.25rem; }}
        .errorlist {{ list-style: none; padding: 0; margin: 0.5rem 0 0 0; }}
        .errorlist li {{ color: #ef4444; font-size: 0.875rem; }}
    </style>
</head>
<body>
    <div class="signup-container">
        <div class="signup-header">
            <div class="logo-space"><i class="bi bi-cloud-arrow-up-fill"></i></div>
            <h2>Simona DataPipeline</h2>
            <p>Crear Nueva Cuenta</p>
        </div>
        <div class="signup-body">
            <h4 class="text-center mb-4" style="color: var(--primary-blue); font-weight: 700;">Registro</h4>
            <form method="post">
                {{{{ csrf_token }}}}
                {{{{ form.as_p }}}}
                <button type="submit" class="btn-custom-primary mt-3"><i class="bi bi-person-plus me-2"></i>Registrarse</button>
            </form>
            <div class="text-center mt-4" style="color: #64748b;">
                <p>¿Ya tienes cuenta? <a href="{{{{ url 'login' }}}}" style="color: var(--primary-blue); text-decoration: none; font-weight: 600;">Inicia sesión</a></p>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>'''

create_file("signup.html", signup_html)

print("\n✅ Todas las plantillas han sido actualizadas con el nuevo diseño!")
print("Reiniciá el servidor para ver los cambios.")
