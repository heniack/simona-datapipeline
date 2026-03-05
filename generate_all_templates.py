#!/usr/bin/env python3
"""Script para generar todas las plantillas HTML restantes con el nuevo diseño"""

import os

BASE_PATH = "/Users/juan.vilanova/Desktop/Simona version final/core/templates/core"

# ========== SYNC_TASK_LIST.HTML ==========
sync_task_list_html = """{% load static %}
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sincronizaciones - {{ connector.name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <style>
        :root { --primary-blue: #2563eb; --light-blue: #3b82f6; }
        body { background: linear-gradient(135deg, #e0f2fe 0%, #ffffff 100%); min-height: 100vh; }
        .navbar-custom { background: linear-gradient(90deg, var(--primary-blue) 0%, var(--light-blue) 100%) !important; box-shadow: 0 2px 10px rgba(37, 99, 235, 0.2); padding: 1rem 0; }
        .logo-space { width: 50px; height: 50px; background: white; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-right: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .logo-space i { font-size: 28px; color: var(--primary-blue); }
        .navbar-brand { font-size: 1.5rem; font-weight: 700; color: white !important; display: flex; align-items: center; }
        .user-badge { background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; color: white; }
        .page-header { background: white; border-radius: 15px; padding: 2rem; box-shadow: 0 2px 15px rgba(0,0,0,0.05); margin-top: 2rem; margin-bottom: 2rem; }
        .page-header h1 { color: var(--primary-blue); font-weight: 700; margin: 0; }
        .btn-custom-primary { background: linear-gradient(90deg, var(--primary-blue) 0%, var(--light-blue) 100%); border: none; color: white; padding: 0.6rem 1.5rem; border-radius: 10px; font-weight: 600; transition: all 0.3s ease; }
        .btn-custom-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(37, 99, 235, 0.3); color: white; }
        .history-card { background: white; border-radius: 15px; padding: 2rem; box-shadow: 0 2px 15px rgba(0,0,0,0.05); margin-bottom: 2rem; }
        .table-modern { background: white; border-radius: 10px; overflow: hidden; }
        .table-modern thead { background: linear-gradient(90deg, var(--primary-blue) 0%, var(--light-blue) 100%); color: white; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-custom">
        <div class="container-fluid px-4">
            <a class="navbar-brand" href="{% url 'home' %}">
                <div class="logo-space"><i class="bi bi-cloud-arrow-up-fill"></i></div>
                Simona DataPipeline
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" style="border-color: white;">
                <span class="navbar-toggler-icon" style="filter: invert(1);"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto align-items-center">
                    <li class="nav-item me-3"><span class="user-badge"><i class="bi bi-person-circle me-2"></i>{{ user.username }}</span></li>
                    <li class="nav-item"><a class="btn btn-light btn-sm" href="{% url 'logout' %}"><i class="bi bi-box-arrow-right me-1"></i>Cerrar Sesión</a></li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
        {% if messages %}
            <div class="mt-3">
                {% for message in messages %}
                    <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            </div>
        {% endif %}

        <div class="page-header">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h1><i class="bi bi-clock-history me-2"></i>Historial de Sincronizaciones</h1>
                    <p class="text-muted mb-0 mt-2">
                        Conector: <strong>{{ connector.name }}</strong> | Base de datos: <strong>{{ connector.db_name }}</strong> | 
                        Tablas: <strong>{{ sync_tasks.count }}</strong> | Frecuencia: <strong>{{ connector.get_sync_frequency_display }}</strong>
                    </p>
                </div>
                <div>
                    <a href="{% url 'connector_list' %}" class="btn btn-secondary me-2"><i class="bi bi-arrow-left me-2"></i>Volver</a>
                    <a href="{% url 'select_tables' connector.id %}" class="btn btn-custom-primary"><i class="bi bi-plus-circle me-2"></i>Agregar Tablas</a>
                </div>
            </div>
        </div>

        <div class="history-card">
            <h4 style="color: var(--primary-blue); margin-bottom: 1.5rem;"><i class="bi bi-list-check me-2"></i>Últimas 20 Ejecuciones</h4>
            {% if sync_executions %}
                <div class="table-responsive table-modern">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>Fecha y Hora</th>
                                <th>Tipo</th>
                                <th>Tablas</th>
                                <th>Registros</th>
                                <th>Duración</th>
                                <th>Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for execution in sync_executions %}
                            <tr>
                                <td><i class="bi bi-calendar3 me-2"></i>{{ execution.started_at|date:"d/m/Y H:i:s" }}</td>
                                <td>
                                    {% if execution.trigger == 'automatic' %}
                                        <span class="badge" style="background: #10b981;"><i class="bi bi-robot me-1"></i>Automática</span>
                                    {% else %}
                                        <span class="badge" style="background: #3b82f6;"><i class="bi bi-hand-index me-1"></i>Manual</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <span class="badge bg-success">{{ execution.tables_synced }}</span>
                                    {% if execution.tables_failed > 0 %}<span class="badge bg-danger ms-1">{{ execution.tables_failed }}</span>{% endif %}
                                </td>
                                <td><i class="bi bi-database me-1"></i>{{ execution.total_records|default:"0" }}</td>
                                <td><i class="bi bi-stopwatch me-1"></i>{{ execution.duration }}</td>
                                <td>
                                    {% if execution.status == 'success' %}
                                        <span class="badge" style="background: #10b981;"><i class="bi bi-check-circle me-1"></i>Éxito</span>
                                    {% elif execution.status == 'partial' %}
                                        <span class="badge bg-warning"><i class="bi bi-exclamation-triangle me-1"></i>Parcial</span>
                                    {% else %}
                                        <span class="badge bg-danger"><i class="bi bi-x-circle me-1"></i>Fallo</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% else %}
                <div class="text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 60px; color: #cbd5e1;"></i>
                    <h5 class="mt-3" style="color: var(--primary-blue);">No hay sincronizaciones registradas</h5>
                    <p class="text-muted">Las sincronizaciones automáticas y manuales aparecerán aquí</p>
                </div>
            {% endif %}
        </div>

        <div class="alert alert-info">
            <strong><i class="bi bi-lightbulb me-2"></i>Tip:</strong> Para que la sincronización detecte cambios, recordá incluir <code>updated_at = NOW()</code> en tus queries UPDATE.
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

with open(os.path.join(BASE_PATH, "sync_task_list.html"), "w", encoding="utf-8") as f:
    f.write(sync_task_list_html)
print("✓ sync_task_list.html")

print("\n✅ Todas las plantillas actualizadas!")
