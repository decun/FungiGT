# Guía de Implementación del Sistema de Temas - FungiGT

## Descripción General
El sistema de temas de FungiGT permite cambiar entre modo claro y oscuro con persistencia en el usuario. Utiliza variables CSS y clases utilitarias para facilitar la implementación.

## Configuración Base

### 1. Incluir en el `<head>` de cada vista:
```html
<link rel="stylesheet" href="/css/styles.css">
<script src="/js/theme-manager.js"></script>
```

### 2. Clase base del `<body>`:
```html
<body class="theme-bg-primary theme-text-primary">
```

## Clases de Tema Disponibles

### Backgrounds
- `theme-bg-primary`: Fondo principal
- `theme-bg-secondary`: Fondo secundario
- `theme-bg-tertiary`: Fondo terciario
- `theme-card`: Fondo para tarjetas
- `theme-navbar`: Fondo del navbar
- `theme-glass-effect`: Efecto de vidrio

### Textos
- `theme-text-primary`: Texto principal
- `theme-text-secondary`: Texto secundario
- `theme-text-muted`: Texto atenuado

### Elementos Interactivos
- `theme-input`: Campos de entrada
- `theme-border`: Bordes
- `theme-shadow-light`: Sombra ligera
- `theme-shadow-medium`: Sombra media
- `theme-shadow-dark`: Sombra oscura

### Elementos de Navegación
- `theme-nav-hover`: Hover de navegación

## Control de Tema

### Toggle de Tema
```html
<div class="theme-toggle" title="Cambiar tema">
    <i class="fas fa-sun theme-icon sun"></i>
    <i class="fas fa-moon theme-icon moon"></i>
</div>
```

## Ejemplo de Implementación

### Estructura básica de vista:
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><%= title %></title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/css/styles.css">
    <script src="/js/theme-manager.js"></script>
</head>
<body class="theme-bg-primary theme-text-primary">
    <%- include('partials/header') %>
    
    <main class="theme-bg-primary min-h-screen">
        <div class="theme-card p-6">
            <h1 class="theme-text-primary">Título</h1>
            <p class="theme-text-secondary">Descripción</p>
        </div>
    </main>
    
    <%- include('partials/footer') %>
</body>
</html>
```

## Formularios

### Campos de entrada:
```html
<input type="text" class="theme-input border rounded-lg focus:ring-2 focus:ring-green-500">
```

### Labels:
```html
<label class="theme-text-secondary">Etiqueta</label>
```

## Tarjetas

### Tarjeta básica:
```html
<div class="theme-card rounded-lg shadow-lg p-6">
    <h3 class="theme-text-primary">Título</h3>
    <p class="theme-text-secondary">Contenido</p>
</div>
```

## Navegación

### Enlaces de navegación:
```html
<a href="/ruta" class="theme-glass-effect theme-nav-hover px-4 py-2 rounded-lg">
    <i class="fas fa-icon"></i>
    <span>Texto</span>
</a>
```

## JavaScript

### Event Listeners para cambios de tema:
```javascript
document.addEventListener('DOMContentLoaded', function() {
    window.addEventListener('themeChanged', function(e) {
        console.log('Tema cambiado a:', e.detail.theme);
        // Lógica adicional aquí
    });
});
```

### Acceso al gestor de temas:
```javascript
// Obtener tema actual
const currentTheme = window.themeManager.getCurrentTheme();

// Verificar si es modo oscuro
const isDarkMode = window.themeManager.isDarkMode();

// Cambiar tema programáticamente
window.themeManager.toggleTheme();
```

## Variables CSS Personalizadas

Si necesitas colores específicos, puedes usar las variables CSS:

```css
.custom-element {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    border-color: var(--border-color);
}
```

## Migración de Vistas Existentes

### Pasos para migrar una vista:

1. **Actualizar head:**
   - Agregar `<script src="/js/theme-manager.js"></script>`

2. **Actualizar body:**
   - Cambiar clase a `theme-bg-primary theme-text-primary`

3. **Reemplazar clases de fondo:**
   - `bg-white` → `theme-bg-primary`
   - `bg-gray-50` → `theme-bg-secondary`
   - `bg-gray-100` → `theme-bg-tertiary`

4. **Reemplazar clases de texto:**
   - `text-gray-900` → `theme-text-primary`
   - `text-gray-600` → `theme-text-secondary`
   - `text-gray-500` → `theme-text-muted`

5. **Actualizar inputs:**
   - Agregar clase `theme-input`

6. **Actualizar tarjetas:**
   - Usar `theme-card` en lugar de `bg-white shadow`

## Mejores Prácticas

1. **Consistencia:** Usa siempre las clases de tema en lugar de colores hardcodeados
2. **Contraste:** Asegúrate de que el contraste sea adecuado en ambos temas
3. **Transiciones:** Las transiciones están incluidas automáticamente
4. **Accesibilidad:** El toggle incluye soporte para teclado
5. **Fallbacks:** El sistema funciona sin JavaScript usando localStorage

## Soporte de Navegadores

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 16+

## Troubleshooting

### Problemas comunes:
1. **Tema no se aplica:** Verificar que el script esté cargado
2. **Colores no cambian:** Usar clases de tema en lugar de Tailwind
3. **Persistencia no funciona:** Verificar cookies y autenticación

### Debug:
```javascript
console.log('Tema actual:', window.themeManager.getCurrentTheme());
console.log('Token disponible:', !!window.themeManager.getAuthToken());
``` 